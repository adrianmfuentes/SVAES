use actix_web::{web, HttpServer};
use std::env;
use svaes_engine::{AppState, health_handler, verify_handler};

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
        actix_web::App::new()
            .app_data(state.clone())
            .service(health_handler)
            .service(verify_handler)
    })
    .bind((host, port))?
    .run()
    .await
}
