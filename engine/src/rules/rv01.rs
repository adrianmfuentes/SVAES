use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-01: Valida que la lista de artefactos no esté vacía.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla que contiene el ID.
///
/// # Lógica
/// 1. Verifica si la longitud del slice de artefactos es mayor a cero.
/// 2. Si está vacía, retorna `RuleStatus::Error` con mensaje descriptivo.
/// 3. Si contiene elementos, retorna `RuleStatus::Ok`.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y mensaje de error si aplica.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    if artifacts.is_empty() {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Error,
            message: Some("La lista de artefactos está vacía. Se requiere al menos un artefacto para proceder.".to_string()),
        }
    } else {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Ok,
            message: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_artifact(id: &str, artifact_type: &str) -> Artifact {
        Artifact {
            id: id.to_string(),
            artifact_type: artifact_type.to_string(),
            metadata: json!({}),
        }
    }

    fn make_rule(id: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        }
    }

    #[test]
    fn rv01_empty_artifacts_returns_error() {
        let artifacts: Vec<Artifact> = vec![];
        let rule = make_rule("RV-01");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("vacía"));
    }

    #[test]
    fn rv01_non_empty_artifacts_returns_ok() {
        let artifacts = vec![make_artifact("A1", "TAREA")];
        let rule = make_rule("RV-01");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    #[test]
    fn rv01_single_artifact_returns_ok() {
        let artifacts = vec![make_artifact("A1", "CÓDIGO")];
        let rule = make_rule("RV-01");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }
}