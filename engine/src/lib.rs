use actix_web::{get, post, web, HttpRequest, HttpResponse, Responder};

pub mod aggregator;
pub mod evaluator;
pub mod models;
pub mod rules;

pub use models::{
    Artifact, EngineResult, RuleEvaluation, RuleStatus, Verdict, VerificationPayload,
    VerificationRule,
};

pub struct AppState {
    pub api_key: String,
}

pub fn check_api_key(req: &HttpRequest, state: &web::Data<AppState>) -> bool {
    if state.api_key.is_empty() {
        return true;
    }
    match req.headers().get("X-Engine-Api-Key") {
        Some(val) => val.to_str().unwrap_or("") == state.api_key,
        None => false,
    }
}

#[get("/health")]
pub async fn health_handler(_state: web::Data<AppState>) -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "svaes-engine",
        "version": env!("CARGO_PKG_VERSION")
    }))
}

#[post("/api/v1/verify")]
pub async fn verify_handler(
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
