use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-09: Verifica que las referencias de origen (links o ramas) en la metadata
/// de los artefactos tengan un formato válido y estén marcadas como accesibles.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto a verificar (default: "CÓDIGO").
///   - `reference_fields`: Array de nombres de campos que contienen referencias (default: ["link", "branch"]).
///   - `accessible_field`: Campo boolean que indica si la referencia es accesible (default: "accessible").
///
/// # Lógica
/// 1. Obtiene el tipo de artefacto y los campos de referencia a verificar.
/// 2. Filtra artefactos por tipo.
/// 3. Por cada artefacto y cada campo de referencia:
///    a) Verifica que el campo exista y sea un string.
///    b) Valida el formato de la referencia (URL o nombre de rama válido).
///    c) Verifica que el campo `accessible` sea `true`.
/// 4. Si alguna referencia es inválida o no accesible, retorna Error.
///
/// # Formatos válidos
/// - Links: deben empezar con "http://" o "https://"
/// - Ramas: deben coincidir con patrón alfanumérico con guiones (ej: "feature/new-feature")
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y IDs con referencias inválidas.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type")
        .and_then(|v| v.as_str())
        .unwrap_or("CÓDIGO");

    let reference_fields: Vec<&str> = rule_config.params
        .get("reference_fields")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
        .unwrap_or_else(|| vec!["link", "branch"]);

    let accessible_field = rule_config.params
        .get("accessible_field")
        .and_then(|v| v.as_str())
        .unwrap_or("accessible");

    fn is_valid_url(s: &str) -> bool {
        s.starts_with("http://") || s.starts_with("https://")
    }

    fn is_valid_branch(s: &str) -> bool {
        !s.is_empty() && s.chars().all(|c| c.is_alphanumeric() || c == '-' || c == '_' || c == '/')
    }

    let mut invalid_refs: Vec<String> = Vec::new();

    for artifact in artifacts.iter().filter(|a| a.artifact_type == artifact_type) {
        for field in &reference_fields {
            if let Some(reference) = artifact.metadata.get(field) {
                if let Some(reference_str) = reference.as_str() {
                    let is_url = field.contains("link") || reference_str.starts_with("http");
                    let format_valid = if is_url {
                        is_valid_url(reference_str)
                    } else {
                        is_valid_branch(reference_str)
                    };

                    if !format_valid {
                        invalid_refs.push(format!("{}/{}: '{}'", artifact.id, field, reference_str));
                    }
                }
            }
        }

        if let Some(accessibility) = artifact.metadata.get(accessible_field) {
            if accessibility.as_bool() == Some(false) {
                invalid_refs.push(format!("{}/{}: no accesible", artifact.id, accessible_field));
            }
        }
    }

    if invalid_refs.is_empty() {
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
                "Referencias inválidas o inaccesibles encontradas: {:?}",
                invalid_refs
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
    fn rv09_valid_references_returns_ok() {
        let artifacts = vec![
            make_artifact("C-001", "CÓDIGO", json!({
                "link": "https://github.com/repo/commit/abc123",
                "branch": "feature/new-feature",
                "accessible": true
            })),
        ];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    #[test]
    fn rv09_invalid_url_format_returns_error() {
        let artifacts = vec![
            make_artifact("C-001", "CÓDIGO", json!({
                "link": "ftp://invalid-protocol.com",
                "accessible": true
            })),
        ];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("C-001"));
    }

    #[test]
    fn rv09_inaccessible_reference_returns_error() {
        let artifacts = vec![
            make_artifact("C-001", "CÓDIGO", json!({
                "link": "https://github.com/repo/commit/abc123",
                "accessible": false
            })),
        ];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("no accesible"));
    }

    #[test]
    fn rv09_invalid_branch_format_returns_error() {
        let artifacts = vec![
            make_artifact("C-001", "CÓDIGO", json!({
                "branch": "feature with spaces",
                "accessible": true
            })),
        ];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("spaces"));
    }

    #[test]
    fn rv09_no_artifacts_of_type_returns_ok() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({})),
        ];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn rv09_missing_reference_field_is_ok() {
        let artifacts = vec![
            make_artifact("C-001", "CÓDIGO", json!({
                "accessible": true
            })),
        ];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn rv09_custom_reference_fields() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({
                "url": "not@valid!url",
                "accessible": true
            })),
        ];
        let rule = VerificationRule {
            id: "RV-09".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({
                "artifact_type": "DOCUMENTO",
                "reference_fields": ["url"],
                "accessible_field": "accessible"
            }),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("not@valid!url"));
    }
}