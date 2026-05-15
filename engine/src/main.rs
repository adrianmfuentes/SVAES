use actix_web::{get, post, web, App, HttpServer, Responder, HttpResponse};
use std::env;

mod models;
mod aggregator;
mod evaluator;
mod rules;

#[get("/health")]
async fn health_handler() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "svaes-engine",
        "version": env!("CARGO_PKG_VERSION")
    }))
}

#[post("/api/v1/verify")]
async fn verify_handler(payload: web::Json<models::VerificationPayload>) -> impl Responder {
    let result = evaluator::evaluate(payload.into_inner());
    HttpResponse::Ok().json(result)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let host = env::var("ENGINE_HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
    let port = env::var("ENGINE_PORT").unwrap_or_else(|_| "8081".to_string())
        .parse::<u16>()
        .unwrap_or(8081);

    println!("SVAES Engine v{} starting on http://{}:{}", env!("CARGO_PKG_VERSION"), host, port);

    HttpServer::new(|| {
        App::new()
            .service(health_handler)
            .service(verify_handler)
    })
    .bind((host, port))?
    .run()
    .await
}