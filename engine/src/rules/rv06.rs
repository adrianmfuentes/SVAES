use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-06: Compara un atributo específico (como la versión) presente en los metadatos
/// de los artefactos con un valor global proporcionado en los parámetros de la regla.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto a verificar (default: "DOCUMENTO").
///   - `attribute`: Nombre del campo en metadata a comparar (default: "version").
///   - `expected_value`: Valor esperado contra el cual comparar.
///
/// # Lógica
/// 1. Obtiene el tipo de artefacto, campo a verificar y valor esperado.
/// 2. Filtra artefactos por tipo.
/// 3. Por cada artefacto, obtiene el valor del campo en su metadata.
/// 4. Si el valor no coincide con el esperado, añade el ID a la lista de discrepancias.
/// 5. Retorna Error si hay discrepancias, Ok si todos coinciden.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y IDs con valores discrepantes.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type")
        .and_then(|v| v.as_str())
        .unwrap_or("DOCUMENTO");

    let attribute = rule_config.params
        .get("attribute")
        .and_then(|v| v.as_str())
        .unwrap_or("version");

    let expected_value = rule_config.params
        .get("expected_value")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let mismatched_artifacts: Vec<&str> = artifacts
        .iter()
        .filter(|a| a.artifact_type == artifact_type)
        .filter(|a| {
            match a.metadata.get(attribute) {
                Some(val) => val.as_str() != Some(expected_value),
                None => true,
            }
        })
        .map(|a| a.id.as_str())
        .collect();

    if mismatched_artifacts.is_empty() {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Ok,
            message: None,
        }
    } else {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Error,
            message: Some(format!(
                "Artefactos con valor de '{}' diferente a '{}' (atributo '{}'): {:?}",
                attribute,
                expected_value,
                attribute,
                mismatched_artifacts
            )),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_artifact(id: &str, artifact_type: &str, metadata: serde_json::Value) -> Artifact {
        Artifact {
            id: id.to_string(),
            artifact_type: artifact_type.to_string(),
            metadata,
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
    fn rv06_all_versions_match_returns_ok() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"})),
            make_artifact("D-002", "DOCUMENTO", json!({"version": "2.0"})),
        ];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    #[test]
    fn rv06_mismatched_version_returns_error() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"})),
            make_artifact("D-002", "DOCUMENTO", json!({"version": "1.5"})),
        ];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("D-002"));
    }

    #[test]
    fn rv06_missing_attribute_returns_error() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"})),
            make_artifact("D-002", "DOCUMENTO", json!({})),
        ];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("D-002"));
    }

    #[test]
    fn rv06_no_artifacts_of_type_returns_ok() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"version": "1.0"})),
        ];
        let rule = make_rule("RV-06");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn rv06_custom_attribute() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"revision": "A"})),
            make_artifact("D-002", "DOCUMENTO", json!({"revision": "B"})),
        ];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({
                "artifact_type": "DOCUMENTO",
                "attribute": "revision",
                "expected_value": "A"
            }),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("D-002"));
    }
}