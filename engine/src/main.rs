use actix_web::{get, post, web, App, HttpServer, HttpRequest, Responder, HttpResponse};
use std::env;

mod models;
mod aggregator;
mod evaluator;
mod rules;

struct AppState {
    api_key: String,
}

fn check_api_key(req: &HttpRequest, state: &web::Data<AppState>) -> bool {
    if state.api_key.is_empty() {
        return true;
    }
    match req.headers().get("X-Engine-Api-Key") {
        Some(val) => val.to_str().unwrap_or("") == state.api_key,
        None => false,
    }
}

#[get("/health")]
async fn health_handler(req: HttpRequest, state: web::Data<AppState>) -> impl Responder {
    if !check_api_key(&req, &state) {
        return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"}));
    }
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "svaes-engine",
        "version": env!("CARGO_PKG_VERSION")
    }))
}

#[post("/api/v1/verify")]
async fn verify_handler(
    req: HttpRequest,
    state: web::Data<AppState>,
    payload: web::Json<models::VerificationPayload>,
) -> impl Responder {
    if !check_api_key(&req, &state) {
        return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"}));
    }
    let result = evaluator::evaluate(payload.into_inner());
    HttpResponse::Ok().json(result)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let host = env::var("ENGINE_HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
    let port = env::var("ENGINE_PORT").unwrap_or_else(|_| "8081".to_string())
        .parse::<u16>()
        .unwrap_or(8081);
    let api_key = env::var("ENGINE_API_KEY").unwrap_or_default();

    if api_key.is_empty() {
        eprintln!("WARNING: ENGINE_API_KEY is not set — engine is unauthenticated");
    }

    println!("SVAES Engine v{} starting on http://{}:{}", env!("CARGO_PKG_VERSION"), host, port);

    let state = web::Data::new(AppState { api_key });

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .service(health_handler)
            .service(verify_handler)
    })
    .bind((host, port))?
    .run()
    .await
}
