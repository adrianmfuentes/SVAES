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
    let config = parse_params(rule_config);
    let invalid_refs = collect_invalid_refs(artifacts, &config);

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

// ── helpers ──────────────────────────────────────────────────────────────────

struct Rv09Params<'a> {
    artifact_type: &'a str,
    reference_fields: Vec<&'a str>,
    accessible_field: &'a str,
}

fn parse_params<'a>(rule_config: &'a VerificationRule) -> Rv09Params<'a> {
    let artifact_type = rule_config
        .params
        .get("artifact_type")
        .and_then(|v| v.as_str())
        .unwrap_or("CÓDIGO");

    let reference_fields: Vec<&str> = rule_config
        .params
        .get("reference_fields")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
        .unwrap_or_else(|| vec!["link", "branch"]);

    let accessible_field = rule_config
        .params
        .get("accessible_field")
        .and_then(|v| v.as_str())
        .unwrap_or("accessible");

    Rv09Params {
        artifact_type,
        reference_fields,
        accessible_field,
    }
}

fn is_valid_url(s: &str) -> bool {
    s.starts_with("http://") || s.starts_with("https://")
}

fn is_valid_branch(s: &str) -> bool {
    !s.is_empty() && s.chars().all(|c| c.is_alphanumeric() || c == '-' || c == '_' || c == '/')
}

/// Determina si una referencia dada es un link (por campo o contenido) y
/// valida su formato en consecuencia.
fn validate_reference_format(field: &str, reference_str: &str) -> bool {
    let is_url = field.contains("link") || reference_str.starts_with("http");
    if is_url {
        is_valid_url(reference_str)
    } else {
        is_valid_branch(reference_str)
    }
}

/// Inspecciona los campos de referencia de un artefacto y devuelve una lista
/// con los mensajes de error para cada referencia con formato inválido.
fn check_reference_fields(artifact: &Artifact, config: &Rv09Params) -> Vec<String> {
    let mut errors: Vec<String> = Vec::new();

    for field in &config.reference_fields {
        if let Some(reference_str) = artifact
            .metadata
            .get(field)
            .and_then(|v| v.as_str())
        {
            if !validate_reference_format(field, reference_str) {
                errors.push(format!("{}/{}: '{}'", artifact.id, field, reference_str));
            }
        }
    }

    errors
}

/// Verifica el campo de accesibilidad del artefacto.
fn check_accessibility(artifact: &Artifact, accessible_field: &str) -> Option<String> {
    match artifact.metadata.get(accessible_field) {
        Some(val) if val.as_bool() == Some(false) => {
            Some(format!("{}/{}: no accesible", artifact.id, accessible_field))
        }
        _ => None,
    }
}

/// Recorre los artefactos del tipo configurado y acumula todos los errores
/// de formato de referencia y accesibilidad.
fn collect_invalid_refs(artifacts: &[Artifact], config: &Rv09Params) -> Vec<String> {
    artifacts
        .iter()
        .filter(|a| a.artifact_type == config.artifact_type)
        .flat_map(|artifact| {
            let mut errors = check_reference_fields(artifact, config);
            if let Some(acc_err) = check_accessibility(artifact, config.accessible_field) {
                errors.push(acc_err);
            }
            errors
        })
        .collect()
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

    /// TC-UNI-MOT-09: RV-09 caso base — referencias de código válidas y accesibles.
    /// Each Choice: cubre el resultado OK para validación de referencias.
    #[test]
    fn tc_uni_mot_09_rv09_valid_references_returns_ok() {
        let artifacts = vec![make_artifact(
            "C-001",
            "CÓDIGO",
            json!({
                "link": "https://github.com/repo/commit/abc123",
                "branch": "feature/new-feature",
                "accessible": true
            }),
        )];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    /// Branch: invalid link URL → Error
    #[test]
    fn invalid_link_returns_error() {
        let artifacts = vec![make_artifact(
            "C-002",
            "CÓDIGO",
            json!({
                "link": "ftp://bad-protocol.com",
                "accessible": true
            }),
        )];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("C-002/link"));
    }

    /// Branch: invalid branch name (empty) → Error
    #[test]
    fn invalid_branch_returns_error() {
        let artifacts = vec![make_artifact(
            "C-003",
            "CÓDIGO",
            json!({
                "branch": "",
                "accessible": true
            }),
        )];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("C-003/branch"));
    }

    /// Branch: accessible field is false → Error
    #[test]
    fn not_accessible_returns_error() {
        let artifacts = vec![make_artifact(
            "C-004",
            "CÓDIGO",
            json!({
                "link": "https://valid.com",
                "accessible": false
            }),
        )];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("no accesible"));
    }

    /// Branch: artifact does not match artifact_type → skipped (OK)
    #[test]
    fn different_artifact_type_skipped() {
        let artifacts = vec![make_artifact(
            "D-001",
            "DOCUMENTO",
            json!({
                "link": "invalid",
                "accessible": false
            }),
        )];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    /// Branch: accessible field missing → treated as accessible (OK)
    #[test]
    fn missing_accessible_field_treated_as_ok() {
        let artifacts = vec![make_artifact(
            "C-005",
            "CÓDIGO",
            json!({
                "link": "https://valid.com"
            }),
        )];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    /// Branch: reference field missing → no error for that field (OK)
    #[test]
    fn missing_reference_field_treated_as_ok() {
        let artifacts = vec![make_artifact(
            "C-006",
            "CÓDIGO",
            json!({
                "accessible": true
            }),
        )];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    /// Branch: reference starts with http → treated as URL validation
    #[test]
    fn reference_starts_with_http_validates_as_url() {
        let artifacts = vec![make_artifact(
            "C-007",
            "CÓDIGO",
            json!({
                "branch": "http://github.com/repo",
                "accessible": true
            }),
        )];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    /// Branch: multiple artifacts with mixed results → all invalid refs collected
    #[test]
    fn multiple_artifacts_collects_all_errors() {
        let artifacts = vec![
            make_artifact(
                "C-008",
                "CÓDIGO",
                json!({
                    "link": "invalid-link",
                    "accessible": true
                }),
            ),
            make_artifact(
                "C-009",
                "CÓDIGO",
                json!({
                    "link": "https://valid.com",
                    "accessible": false
                }),
            ),
        ];
        let rule = make_rule("RV-09");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("C-008/link"));
        assert!(msg.contains("C-009/accessible"));
    }
}
