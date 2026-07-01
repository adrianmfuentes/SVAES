use serde_json::json;
use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-06: Compara un atributo específico (como la versión) presente en los metadatos
/// de los artefactos con un valor global proporcionado en los parámetros de la regla.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto a verificar (default: "DOCUMENTO").
///   - `attribute`: Nombre del campo en metadata a comparar (default: "version").
///   - `expected_value`: Valor esperado contra el cual comparar. Si no se
///     configura, se usa `release_version` (la versión real de la entrega en
///     verificación) como valor por defecto - así el perfil de sistema (que no
///     puede fijar un valor válido para todas las entregas) sigue siendo útil
///     sin necesitar un perfil propio por cada entrega.
/// * `release_version` - Versión de la entrega actual, provista por el motor
///   (no por el perfil), usada como fallback cuando `expected_value` no está configurado.
///
/// # Lógica
/// 1. Obtiene el tipo de artefacto, campo a verificar y valor esperado
///    (explícito o, en su defecto, la versión de la entrega).
/// 2. Filtra artefactos por tipo.
/// 3. Por cada artefacto, obtiene el valor del campo en su metadata.
/// 4. Si el valor no coincide con el esperado, añade el ID a la lista de discrepancias.
/// 5. Retorna Error si hay discrepancias, Ok si todos coinciden.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y IDs con valores discrepantes.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule, release_version: Option<&str>) -> RuleEvaluation {
    if artifacts.is_empty() {
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::NoEvaluada,
            message: Some("rule_evidence.no_evaluada.empty_artifacts".to_string()),
            message_params: None,
        };
    }

    let artifact_type = rule_config.params
        .get("artifact_type")
        .and_then(|v| v.as_str())
        .unwrap_or("DOCUMENTO");

    let attribute = rule_config.params
        .get("attribute")
        .and_then(|v| v.as_str())
        .unwrap_or("version");

    let configured_value = rule_config.params
        .get("expected_value")
        .and_then(|v| v.as_str())
        .filter(|v| !v.is_empty());

    let expected_value = match configured_value.or(release_version) {
        Some(v) if !v.is_empty() => v,
        _ => {
            // Neither the profile nor the engine has any value to compare
            // against - there's nothing meaningful to check, not a data problem.
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::NoEvaluada,
                message: Some("rule_evidence.no_evaluada.RV-06.no_expected_value".to_string()),
                message_params: None,
            };
        }
    };

    let target_artifacts: Vec<&Artifact> = artifacts
        .iter()
        .filter(|a| a.artifact_type == artifact_type)
        .collect();

    if target_artifacts.is_empty() {
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::NoEvaluada,
            message: Some("rule_evidence.no_evaluada.RV-06".to_string()),
            message_params: Some(json!({
                "artifact_type": artifact_type,
            })),
        };
    }

    let mismatched_artifacts: Vec<&str> = target_artifacts
        .iter()
        .filter(|a| {
            let attribute_matches = a.metadata.get(attribute)
                .and_then(|v| v.as_str())
                .map(|s| s == expected_value)
                .unwrap_or(false);
            if attribute_matches {
                return false;
            }
            // Fallback: many documents are versioned by embedding the version
            // in their title (e.g. "Informe de pruebas v1.0.0") rather than
            // relying on a connector-native version counter - Confluence's
            // "version" field, for instance, is just an edit-revision count
            // (e.g. 1, 2, 9...), unrelated to the product's semantic release
            // version, so it will essentially never match by coincidence.
            let title_contains_expected = a.metadata.get("title")
                .and_then(|v| v.as_str())
                .map(|title| title.contains(expected_value))
                .unwrap_or(false);
            !title_contains_expected
        })
        .map(|a| a.id.as_str())
        .collect();

    if mismatched_artifacts.is_empty() {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Ok,
            message: None,
            message_params: None,
        }
    } else {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Error,
            message: Some("rule_evidence.error.RV-06".to_string()),
            message_params: Some(json!({
                "attribute": attribute,
                "expected_value": expected_value,
                "mismatched_artifacts": format!("{:?}", mismatched_artifacts),
            })),
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

    /// TC-UNI-MOT-06: RV-06 caso base — todos los atributos de versión coinciden.
    /// Each Choice: cubre el resultado OK para coherencia de atributos.
    #[test]
    fn tc_uni_mot_06_rv06_all_versions_match_returns_ok() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"})),
            make_artifact("D-002", "DOCUMENTO", json!({"version": "2.0"})),
        ];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule, None);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    #[test]
    fn no_expected_value_configured_returns_no_evaluada() {
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"}))];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        };

        let result = evaluate(&artifacts, &rule, None);

        assert_eq!(result.status, RuleStatus::NoEvaluada);
        assert_eq!(result.message.unwrap(), "rule_evidence.no_evaluada.RV-06.no_expected_value");
    }

    #[test]
    fn falls_back_to_release_version_when_expected_value_not_configured() {
        // The system's default profile can't hardcode a version that fits every
        // release, so when expected_value isn't set the release's own version
        // (passed in by the engine, not the profile) is used instead.
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"version": "1.0.0"}))];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        };

        let result = evaluate(&artifacts, &rule, Some("1.0.0"));

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn title_containing_expected_version_matches_even_if_version_field_differs() {
        // Confluence's native "version" is an edit-revision counter (e.g. "1"
        // for a never-edited page), unrelated to the product's semantic release
        // version - but many pages embed the real version in their title
        // instead (e.g. "Informe de pruebas v1.0.0"), which should count.
        let artifacts = vec![make_artifact(
            "D-001", "DOCUMENTO",
            json!({"version": "1", "title": "Informe de pruebas v1.0.0"}),
        )];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        };

        let result = evaluate(&artifacts, &rule, Some("1.0.0"));

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn title_not_containing_expected_version_still_flagged() {
        let artifacts = vec![make_artifact(
            "D-001", "DOCUMENTO",
            json!({"version": "1", "title": "Informe de pruebas v0.9.0"}),
        )];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        };

        let result = evaluate(&artifacts, &rule, Some("1.0.0"));

        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn release_version_fallback_still_flags_real_mismatch() {
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"version": "0.9.0"}))];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        };

        let result = evaluate(&artifacts, &rule, Some("1.0.0"));

        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn explicit_expected_value_takes_priority_over_release_version() {
        // A profile that deliberately configures expected_value (e.g. because a
        // document is meant to stay at a fixed version regardless of releases)
        // must not be silently overridden by the release version fallback.
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"}))];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule, Some("1.0.0"));

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn version_mismatch_returns_error() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"})),
            make_artifact("D-002", "DOCUMENTO", json!({"version": "1.5"})),
        ];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule, None);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.error.RV-06");
        let params = result.message_params.unwrap();
        assert!(params["mismatched_artifacts"].as_str().unwrap().contains("D-002"));
    }

    #[test]
    fn missing_attribute_returns_error() {
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({}))];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule, None);

        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn no_matching_artifacts_returns_no_evaluada() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"version": "wrong"}))];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule, None);

        assert_eq!(result.status, RuleStatus::NoEvaluada);
    }

    #[test]
    fn empty_artifacts_returns_no_evaluada() {
        let artifacts: Vec<Artifact> = vec![];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };
        let result = evaluate(&artifacts, &rule, None);
        assert_eq!(result.status, RuleStatus::NoEvaluada);
    }
}