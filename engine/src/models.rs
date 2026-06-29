/*
Este módulo define las estructuras de datos clave utilizadas para la comunicación entre el backend y el motor de verificación.
Estas estructuras permiten representar los artefactos recuperados, las reglas de verificación configuradas, los resultados de
la evaluación de cada regla y el veredicto global de la verificación. El diseño de estas estructuras facilita la integración
con diversos conectores y la adaptación a diferentes tipos de artefactos y reglas.
*/

use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Artifact {
    pub id: String,
    pub artifact_type: String,
    pub metadata: Value,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct VerificationRule {
    pub id: String,
    pub severity: String,
    pub params: Value,
}

#[derive(Debug, Deserialize)]
pub struct VerificationPayload {
    pub artifacts: Vec<Artifact>,
    pub rules: Vec<VerificationRule>,
}

#[derive(Debug, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum RuleStatus {
    Ok,
    Error,
    Warning,
    NoEvaluada,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RuleEvaluation {
    pub rule_id: String,
    pub status: RuleStatus,
    pub message: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message_params: Option<serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Verdict {
    Valida,
    ConAdvertencias,
    NoValida,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub struct SummaryData {
    pub total: usize,
    pub ok: usize,
    pub error: usize,
    pub warning: usize,
    pub not_evaluated: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EngineResult {
    pub verdict: Verdict,
    pub rule_results: Vec<RuleEvaluation>,
    pub summary: SummaryData,
}