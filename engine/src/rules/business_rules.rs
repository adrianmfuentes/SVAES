// Reglas de negocio RV-01..RV-10 del catalogo SVAES, consolidadas en un
// unico fichero (cada una vivia antes en su propio rvXX.rs) para no tener
// diez ficheros casi identicos en el directorio. Cada submodulo mantiene su
// propio `evaluate` y sus propios tests, exactamente igual que antes -
// `rules::rv01::evaluate(...)` etc. siguen funcionando sin cambios via el
// re-export en mod.rs.


pub mod rv01 {
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
                message: Some("rule_evidence.error.RV-01".to_string()),
                message_params: None,
            }
        } else {
            RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Ok,
                message: None,
                message_params: None,
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

        /// TC-UNI-MOT-01: RV-01 caso base — artefactos presentes, connector ACTIVO implícito.
        /// Each Choice: cubre el resultado OK para el catálogo de reglas.
        #[test]
        fn tc_uni_mot_01_rv01_artifacts_present_returns_ok() {
            let artifacts = vec![make_artifact("A1", "TAREA")];
            let rule = make_rule("RV-01");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
            assert!(result.message.is_none());
        }

        /// TC-UNI-MOT-11: RV-01 — lista vacía produce ERROR (NOT_FOUND path).
        /// Each Choice: cubre el resultado ERROR para RV-01.
        #[test]
        fn tc_uni_mot_11_rv01_empty_artifacts_returns_error() {
            let artifacts: Vec<Artifact> = vec![];
            let rule = make_rule("RV-01");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            assert_eq!(result.message.unwrap(), "rule_evidence.error.RV-01");
        }
    }
}

pub mod rv02 {
    use serde_json::json;
    use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

    /// RV-02: Implementa una búsqueda cruzada para verificar trazabilidad.
    ///
    /// # Parámetros
    /// * `artifacts` - Slice de artefactos a verificar.
    /// * `rule_config` - Configuración de la regla con parámetros opcionales:
    ///   - `source_type`: Tipo de artefacto fuente que contiene referencias (default: "CODIGO").
    ///   - `target_type`: Tipo de artefacto destino que debe existir (default: "TAREA").
    ///   - `reference_field`: Campo de metadata que contiene el ID referenciado (default: "task_id").
    ///
    /// # Lógica
    /// 1. Filtra artefactos por tipo fuente (default: "CODIGO").
    /// 2. Por cada artefacto fuente, extrae el campo de referencia de su metadata.
    /// 3. Busca si existe algún artefacto del tipo destino (default: "TAREA") con ese ID.
    /// 4. Si no existe, retorna Error con los IDs huérfanos.
    /// 5. Si todos existen, retorna Ok.
    ///
    /// # Retorno
    /// `RuleEvaluation` con el estado correspondiente y mensaje detallado si hay referencias faltantes.
    pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
        if artifacts.is_empty() {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::NoEvaluada,
                message: Some("rule_evidence.no_evaluada.empty_artifacts".to_string()),
                message_params: None,
            };
        }

        let source_type = rule_config.params
            .get("source_type")
            .and_then(|v| v.as_str())
            .unwrap_or("CODIGO");

        let target_type = rule_config.params
            .get("target_type")
            .and_then(|v| v.as_str())
            .unwrap_or("TAREA");

        let reference_field = rule_config.params
            .get("reference_field")
            .and_then(|v| v.as_str())
            .unwrap_or("task_id");

        let source_ids: std::collections::HashSet<&str> = artifacts
            .iter()
            .filter(|a| a.artifact_type == target_type)
            .map(|a| a.id.as_str())
            .collect();

        let mut missing_references: Vec<&str> = Vec::new();

        for artifact in artifacts.iter().filter(|a| a.artifact_type == source_type) {
            if let Some(reference) = artifact.metadata.get(reference_field) {
                if let Some(reference_str) = reference.as_str() {
                    if !source_ids.contains(reference_str) {
                        missing_references.push(reference_str);
                    }
                }
            }
        }

        if missing_references.is_empty() {
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
                message: Some("rule_evidence.error.RV-02".to_string()),
                message_params: Some(json!({
                    "count": missing_references.len().to_string(),
                    "source_type": source_type,
                    "target_type": target_type,
                    "missing_refs": format!("{:?}", missing_references),
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

        fn make_rule(id: &str) -> VerificationRule {
            VerificationRule {
                id: id.to_string(),
                severity: "OBLIGATORIA".to_string(),
                params: json!({}),
            }
        }

        /// TC-UNI-MOT-02: RV-02 caso base — todas las referencias existen.
        /// Each Choice: cubre el resultado OK para trazabilidad entre artefactos.
        #[test]
        fn tc_uni_mot_02_rv02_all_references_exist_returns_ok() {
            let artifacts = vec![
                make_artifact("T-001", "TAREA", json!({})),
                make_artifact("T-002", "TAREA", json!({})),
                make_artifact("C-001", "CODIGO", json!({"task_id": "T-001"})),
                make_artifact("C-002", "CODIGO", json!({"task_id": "T-002"})),
            ];
            let rule = make_rule("RV-02");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
            assert!(result.message.is_none());
        }

        /// TC-UNI-MOT-12: RV-02 — referencia huérfana produce ERROR.
        /// Each Choice: cubre el resultado ERROR para el catálogo de trazabilidad.
        #[test]
        fn tc_uni_mot_12_rv02_orphan_reference_returns_error() {
            let artifacts = vec![
                make_artifact("T-001", "TAREA", json!({})),
                make_artifact("C-001", "CODIGO", json!({"task_id": "T-001"})),
                make_artifact("C-002", "CODIGO", json!({"task_id": "T-999"})),
            ];
            let rule = make_rule("RV-02");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-02");
            let params = result.message_params.unwrap();
            assert!(params["missing_refs"].as_str().unwrap().contains("T-999"));
        }

        #[test]
        fn codigo_without_task_id_field_is_ok() {
            // CODIGO artifacts without the reference field are silently skipped (field is optional).
            let artifacts = vec![
                make_artifact("T-001", "TAREA", json!({})),
                make_artifact("C-001", "CODIGO", json!({})),
            ];
            let result = evaluate(&artifacts, &make_rule("RV-02"));
            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn no_codigo_artifacts_returns_ok() {
            let artifacts = vec![make_artifact("T-001", "TAREA", json!({}))];
            let result = evaluate(&artifacts, &make_rule("RV-02"));
            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn empty_artifacts_returns_no_evaluada() {
            let artifacts: Vec<Artifact> = vec![];
            let result = evaluate(&artifacts, &make_rule("RV-02"));
            assert_eq!(result.status, RuleStatus::NoEvaluada);
        }
    }
}

pub mod rv03 {
    use serde_json::json;
    use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

    /// RV-03: Comprueba que todos los artefactos de un tipo específico coincidan
    /// con un valor de "estado" permitido definido en los parámetros de la regla.
    ///
    /// # Parámetros
    /// * `artifacts` - Slice de artefactos a verificar.
    /// * `rule_config` - Configuración de la regla con parámetros:
    ///   - `artifact_type`: Tipo de artefacto a filtrar (default: "TAREA").
    ///   - `allowed_states`: Array de strings con los estados válidos (default: ["DONE", "CLOSED"]).
    ///   - `status_field`: Nombre del campo en metadata que contiene el estado (default: "status").
    ///
    /// # Lógica
    /// 1. Obtiene el tipo de artefacto a verificar (default: "TAREA").
    /// 2. Obtiene la lista de estados permitidos desde los parámetros (default: ["DONE", "CLOSED"]).
    /// 3. Filtra los artefactos por tipo y verifica que cada uno tenga un estado permitido.
    /// 4. Si algún artefacto tiene estado no permitido o campo ausente, retorna Error.
    /// 5. Si todos los estados son válidos, retorna Ok.
    ///
    /// # Retorno
    /// `RuleEvaluation` con el estado correspondiente y mensaje detallado si hay estados inválidos.
    pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
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
            .unwrap_or("TAREA");

        let allowed_states: Vec<&str> = rule_config.params
            .get("allowed_states")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
            .unwrap_or_else(|| vec!["DONE", "CLOSED"]);

        let status_field = rule_config.params
            .get("status_field")
            .and_then(|v| v.as_str())
            .unwrap_or("status");

        let invalid_artifacts: Vec<&str> = artifacts
            .iter()
            .filter(|a| a.artifact_type == artifact_type)
            .filter(|a| {
                match a.metadata.get(status_field) {
                    Some(val) => {
                        match val.as_str() {
                            Some(state) => !allowed_states.iter().any(|allowed| allowed.eq_ignore_ascii_case(state)),
                            None => true,
                        }
                    }
                    None => true,
                }
            })
            .map(|a| a.id.as_str())
            .collect();

        if invalid_artifacts.is_empty() {
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
                message: Some("rule_evidence.error.RV-03".to_string()),
                message_params: Some(json!({
                    "allowed_states": format!("{:?}", allowed_states),
                    "invalid_artifacts": format!("{:?}", invalid_artifacts),
                })),
            }
        }
    }

    #[cfg(test)]
    mod tests {
        use super::*;
        use serde_json::json;

        fn make_artifact(id: &str, artifact_type: &str, status: &str) -> Artifact {
            Artifact {
                id: id.to_string(),
                artifact_type: artifact_type.to_string(),
                metadata: json!({"status": status}),
            }
        }

        fn make_rule(id: &str, params: serde_json::Value) -> VerificationRule {
            VerificationRule {
                id: id.to_string(),
                severity: "OBLIGATORIA".to_string(),
                params,
            }
        }

        /// TC-UNI-MOT-03: RV-03 caso base — todos los estados son válidos.
        /// Each Choice: cubre el resultado OK para validación de estado de tareas.
        #[test]
        fn tc_uni_mot_03_rv03_all_states_valid_returns_ok() {
            let artifacts = vec![
                make_artifact("T-001", "TAREA", "DONE"),
                make_artifact("T-002", "TAREA", "CLOSED"),
            ];
            let rule = make_rule("RV-03", json!({"allowed_states": ["DONE", "CLOSED"]}));

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
            assert!(result.message.is_none());
        }

        #[test]
        fn invalid_state_returns_error() {
            let artifacts = vec![
                make_artifact("T-001", "TAREA", "DONE"),
                make_artifact("T-002", "TAREA", "IN_PROGRESS"),
            ];
            let rule = make_rule("RV-03", json!({}));

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-03");
            let params = result.message_params.unwrap();
            assert!(params["invalid_artifacts"].as_str().unwrap().contains("T-002"));
        }

        #[test]
        fn missing_status_field_returns_error() {
            let artifacts = vec![Artifact {
                id: "T-001".to_string(),
                artifact_type: "TAREA".to_string(),
                metadata: serde_json::json!({}),
            }];
            let rule = make_rule("RV-03", json!({}));

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
        }

        #[test]
        fn no_tarea_artifacts_returns_ok() {
            let artifacts = vec![Artifact {
                id: "C-001".to_string(),
                artifact_type: "CODIGO".to_string(),
                metadata: serde_json::json!({"status": "IN_PROGRESS"}),
            }];
            let rule = make_rule("RV-03", json!({}));

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn empty_artifacts_returns_no_evaluada() {
            let artifacts: Vec<Artifact> = vec![];
            let result = evaluate(&artifacts, &make_rule("RV-03", json!({})));
            assert_eq!(result.status, RuleStatus::NoEvaluada);
        }

        /// Conectores como Jira devuelven el nombre de estado con la capitalización
        /// original de su workflow (p. ej. "Done"), no en mayúsculas. La comparación
        /// contra `allowed_states` debe ser insensible a mayúsculas/minúsculas para
        /// que un estado como "Done" siga contando como válido frente al valor por
        /// defecto ["DONE", "CLOSED"].
        #[test]
        fn state_comparison_is_case_insensitive() {
            let artifacts = vec![make_artifact("T-001", "TAREA", "Done")];
            let rule = make_rule("RV-03", json!({}));

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
        }
    }
}

pub mod rv04 {
    use serde_json::json;
    use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

    /// RV-04: Asegura que campos numéricos o de esfuerzo en la metadata no sean nulos ni menores a cero.
    ///
    /// # Parámetros
    /// * `artifacts` - Slice de artefactos a verificar.
    /// * `rule_config` - Configuración de la regla con parámetros:
    ///   - `artifact_type`: Tipo de artefacto a verificar (default: "TAREA").
    ///   - `numeric_fields`: Array con los nombres de campos a validar (default: ["effort", "estimation"]).
    ///
    /// # Lógica
    /// 1. Obtiene el tipo de artefacto y lista de campos a verificar.
    /// 2. Por cada artefacto del tipo especificado, verifica que cada campo exista y sea numérico >= 0.
    /// 3. Si algún campo es nulo, no numérico, o menor a cero, añade el ID a la lista de errores.
    /// 4. Retorna Error con los IDs que tienen campos inválidos.
    ///
    /// # Retorno
    /// `RuleEvaluation` con el estado correspondiente y IDs de artefactos con campos inválidos.
    pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
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
            .unwrap_or("TAREA");

        let numeric_fields: Vec<&str> = rule_config.params
            .get("numeric_fields")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
            .unwrap_or_else(|| vec!["effort", "estimation"]);

        let invalid_artifacts: Vec<&str> = artifacts
            .iter()
            .filter(|a| a.artifact_type == artifact_type)
            .filter(|a| {
                // A field that is simply absent from the connector's data isn't an
                // invalid value - it means this artifact doesn't track that field at
                // all (e.g. a Jira issue with no story-point estimate configured).
                // Only a field that is *present* but null, non-numeric, or negative
                // indicates an actual data-quality problem worth flagging.
                numeric_fields.iter().any(|field| {
                    match a.metadata.get(*field) {
                        Some(val) => {
                            if val.is_null() {
                                return true;
                            }
                            match val.as_f64() {
                                Some(n) => n < 0.0,
                                None => true,
                            }
                        }
                        None => false,
                    }
                })
            })
            .map(|a| a.id.as_str())
            .collect();

        if invalid_artifacts.is_empty() {
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
                message: Some("rule_evidence.error.RV-04".to_string()),
                message_params: Some(json!({
                    "numeric_fields": format!("{:?}", numeric_fields),
                    "invalid_artifacts": format!("{:?}", invalid_artifacts),
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

        fn make_rule(id: &str) -> VerificationRule {
            VerificationRule {
                id: id.to_string(),
                severity: "OBLIGATORIA".to_string(),
                params: json!({}),
            }
        }

        /// TC-UNI-MOT-04: RV-04 caso base — campos numéricos válidos (>= 0).
        /// Each Choice: cubre el resultado OK para integridad de campos numéricos.
        #[test]
        fn tc_uni_mot_04_rv04_all_fields_valid_returns_ok() {
            let artifacts = vec![
                make_artifact("T-001", "TAREA", json!({"effort": 5, "estimation": 10})),
                make_artifact("T-002", "TAREA", json!({"effort": 0, "estimation": 0})),
            ];
            let rule = make_rule("RV-04");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn float_values_are_accepted() {
            let artifacts = vec![make_artifact("T-001", "TAREA", json!({"effort": 2.5, "estimation": 3.75}))];
            let result = evaluate(&artifacts, &make_rule("RV-04"));
            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn negative_value_returns_error() {
            let artifacts = vec![make_artifact("T-001", "TAREA", json!({"effort": -1, "estimation": 5}))];
            let result = evaluate(&artifacts, &make_rule("RV-04"));
            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-04");
            let params = result.message_params.unwrap();
            assert!(params["invalid_artifacts"].as_str().unwrap().contains("T-001"));
        }

        #[test]
        fn missing_field_is_not_flagged_only_present_invalid_values_are() {
            // A connector that simply doesn't track "estimation" for this artifact
            // shouldn't fail the rule - there's nothing invalid to report, just data
            // that was never collected. Only a *present* invalid value is an error.
            let artifacts = vec![make_artifact("T-001", "TAREA", json!({"effort": 3}))];
            let result = evaluate(&artifacts, &make_rule("RV-04"));
            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn null_field_returns_error() {
            let artifacts = vec![make_artifact("T-001", "TAREA", json!({"effort": null, "estimation": 5}))];
            let result = evaluate(&artifacts, &make_rule("RV-04"));
            assert_eq!(result.status, RuleStatus::Error);
        }

        #[test]
        fn no_tarea_artifacts_returns_ok() {
            let artifacts = vec![make_artifact("C-001", "CODIGO", json!({}))];
            let result = evaluate(&artifacts, &make_rule("RV-04"));
            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn empty_artifacts_returns_no_evaluada() {
            let artifacts: Vec<Artifact> = vec![];
            let result = evaluate(&artifacts, &make_rule("RV-04"));
            assert_eq!(result.status, RuleStatus::NoEvaluada);
        }
    }
}

pub mod rv05 {
    use serde_json::json;
    use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

    /// RV-05: Verifica que existan artefactos de tipo "DOCUMENTO" y que tengan
    /// un flag de accesibilidad en true dentro de su metadata.
    ///
    /// # Parámetros
    /// * `artifacts` - Slice de artefactos a verificar.
    /// * `rule_config` - Configuración de la regla con parámetros:
    ///   - `artifact_type`: Tipo de artefacto a verificar (default: "DOCUMENTO").
    ///   - `accessible_field`: Nombre del campo boolean en metadata (default: "accessible").
    ///
    /// # Lógica
    /// 1. Filtra artefactos por tipo (default: "DOCUMENTO").
    /// 2. Verifica que al menos uno exista.
    /// 3. Por cada documento, comprueba que el campo `accessible` exista y sea `true`.
    /// 4. Si no hay documentos o alguno no es accesible, retorna Error.
    ///
    /// # Retorno
    /// `RuleEvaluation` con el estado correspondiente y IDs de documentos inaccesibles.
    pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
        let artifact_type = rule_config.params
            .get("artifact_type")
            .and_then(|v| v.as_str())
            .unwrap_or("DOCUMENTO");

        let accessible_field = rule_config.params
            .get("accessible_field")
            .and_then(|v| v.as_str())
            .unwrap_or("accessible");

        let documents: Vec<&Artifact> = artifacts
            .iter()
            .filter(|a| a.artifact_type == artifact_type)
            .collect();

        if documents.is_empty() {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some("rule_evidence.error.RV-05.no_docs".to_string()),
                message_params: Some(json!({
                    "artifact_type": artifact_type,
                })),
            };
        }

        let inaccessible_docs: Vec<&str> = documents
            .iter()
            .filter(|doc| {
                match doc.metadata.get(accessible_field) {
                    Some(val) => val.as_bool() != Some(true),
                    None => true,
                }
            })
            .map(|doc| doc.id.as_str())
            .collect();

        if inaccessible_docs.is_empty() {
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
                message: Some("rule_evidence.error.RV-05.inaccessible".to_string()),
                message_params: Some(json!({
                    "accessible_field": accessible_field,
                    "inaccessible_docs": format!("{:?}", inaccessible_docs),
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

        fn make_rule(id: &str) -> VerificationRule {
            VerificationRule {
                id: id.to_string(),
                severity: "OBLIGATORIA".to_string(),
                params: json!({}),
            }
        }

        /// TC-UNI-MOT-05: RV-05 caso base — todos los documentos accesibles.
        /// Each Choice: cubre el resultado OK para disponibilidad de documentos.
        #[test]
        fn tc_uni_mot_05_rv05_all_accessible_returns_ok() {
            let artifacts = vec![
                make_artifact("D-001", "DOCUMENTO", json!({"accessible": true})),
                make_artifact("D-002", "DOCUMENTO", json!({"accessible": true})),
            ];
            let rule = make_rule("RV-05");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
            assert!(result.message.is_none());
        }

        #[test]
        fn no_documents_returns_error() {
            let artifacts = vec![make_artifact("T-001", "TAREA", json!({"accessible": true}))];
            let rule = make_rule("RV-05");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-05.no_docs");
            let params = result.message_params.unwrap();
            assert!(params["artifact_type"].as_str().unwrap().contains("DOCUMENTO"));
        }

        #[test]
        fn inaccessible_document_returns_error() {
            let artifacts = vec![
                make_artifact("D-001", "DOCUMENTO", json!({"accessible": true})),
                make_artifact("D-002", "DOCUMENTO", json!({"accessible": false})),
            ];
            let rule = make_rule("RV-05");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-05.inaccessible");
            let params = result.message_params.unwrap();
            assert!(params["inaccessible_docs"].as_str().unwrap().contains("D-002"));
        }

        #[test]
        fn document_missing_accessible_field_returns_error() {
            let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({}))];
            let rule = make_rule("RV-05");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
        }
    }
}

pub mod rv06 {
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
    /// Comprueba si `expected_value` aparece en `title` como token de versión
    /// completo (no como subcadena de un número mayor, p. ej. "2.0" no debe
    /// coincidir dentro de "12.0" ni de "2.0.1").
    fn title_contains_exact_version(title: &str, expected_value: &str) -> bool {
        if expected_value.is_empty() {
            return false;
        }
        let is_version_char = |c: char| c.is_ascii_digit() || c == '.';
        title.match_indices(expected_value).any(|(start, matched)| {
            let end = start + matched.len();
            let before_ok = title[..start].chars().next_back().map_or(true, |c| !is_version_char(c));
            let after_ok = title[end..].chars().next().map_or(true, |c| !is_version_char(c));
            before_ok && after_ok
        })
    }

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
                //
                // This must be an exact token match, not a raw substring search:
                // `str::contains` would let expected_value "1.0.0" match inside an
                // unrelated "21.0.0" or "1.0.0.1", silently marking a genuinely
                // mismatched artifact as OK.
                let title_contains_expected = a.metadata.get("title")
                    .and_then(|v| v.as_str())
                    .map(|title| title_contains_exact_version(title, expected_value))
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

        /// Bug regression: a plain `str::contains` fallback lets a mismatched
        /// version slip through validation whenever `expected_value` happens to
        /// occur as a substring of a larger, unrelated number in the title
        /// (e.g. "1.0.0" inside "21.0.0"). The rule must not report OK here.
        #[test]
        fn title_with_expected_version_as_substring_of_larger_number_still_flagged() {
            let artifacts = vec![make_artifact(
                "D-001", "DOCUMENTO",
                json!({"version": "1", "title": "Informe de pruebas v21.0.0"}),
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
}

pub mod rv07 {
    use serde_json::json;
    use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

    /// RV-07: Confirma la presencia de un artefacto que actúe como "marcador"
    /// de que la operación ha sido registrada en herramientas externas de gestión.
    ///
    /// # Parámetros
    /// * `artifacts` - Slice de artefactos a verificar.
    /// * `rule_config` - Configuración de la regla con parámetros:
    ///   - `artifact_type`: Tipo de artefacto marcador a buscar (obligatorio: "TAREA",
    ///     "CAMBIO" o "PLAN"). Sin conector alguno que exponga un marcador booleano
    ///     genérico, no hay una búsqueda "en cualquier tipo" con la que evaluar de
    ///     forma fiable.
    ///   - `marker_field`: Campo en metadata que indica registro externo (default: "external_registered").
    ///
    /// # Lógica
    /// 1. Si `artifact_type` no está configurado, la regla no es aplicable: NoEvaluada.
    /// 2. Si está configurado pero no es uno de los tipos permitidos, Error.
    /// 3. Si no encuentra ningún artefacto de ese tipo, devuelve Error.
    /// 4. Para "PLAN": su mera existencia ya es la prueba de registro externo (un
    ///    artefacto de plan viene, por definición, de una herramienta de
    ///    planificación externa) - Ok directo, sin exigir un campo marker adicional.
    /// 5. Para "TAREA"/"CAMBIO": además hace falta que su campo marker sea `true`,
    ///    porque la mera existencia de una tarea no prueba por sí sola un registro
    ///    externo específico.
    ///
    /// # Retorno
    /// `RuleEvaluation` con el estado correspondiente indicando si el marcador fue encontrado.
    const PERMITIDOS: &[&str] = &["TAREA", "CAMBIO", "PLAN"];
    const EXISTENCE_ONLY_TYPES: &[&str] = &["PLAN"];

    pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
        let artifact_type = rule_config.params
            .get("artifact_type")
            .and_then(|v| v.as_str());

        if artifact_type.is_none() {
            // Without a configured artifact_type there's no reliable signal to search
            // for: connectors don't natively expose a generic "external_registered"
            // marker, so searching across every artifact type would always fail
            // regardless of real data. That's a missing configuration, not a defect.
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::NoEvaluada,
                message: Some("rule_evidence.no_evaluada.RV-07".to_string()),
                message_params: None,
            };
        }

        let t = artifact_type.expect("checked above: artifact_type is Some at this point");
        if !PERMITIDOS.contains(&t) {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some("rule_evidence.error.RV-07.tipo_no_permitido".to_string()),
                message_params: Some(json!({
                    "artifact_type": t,
                    "tipos_permitidos": PERMITIDOS,
                })),
            };
        }

        let marker_field = rule_config.params
            .get("marker_field")
            .and_then(|v| v.as_str())
            .unwrap_or("external_registered");

        let marker_artifact = artifacts.iter().find(|a| a.artifact_type == t);

        match marker_artifact {
            Some(artifact) => {
                let found_type = t;
                if EXISTENCE_ONLY_TYPES.contains(&t) {
                    return RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::Ok,
                        message: Some("rule_evidence.ok.RV-07.found".to_string()),
                        message_params: Some(json!({
                            "artifact_type": found_type,
                            "artifact_id": artifact.id,
                        })),
                    };
                }
                match artifact.metadata.get(marker_field) {
                    Some(val) if val.as_bool() == Some(true) => {
                        RuleEvaluation {
                            rule_id: rule_config.id.clone(),
                            status: RuleStatus::Ok,
                            message: Some("rule_evidence.ok.RV-07.found".to_string()),
                            message_params: Some(json!({
                                "artifact_type": found_type,
                                "artifact_id": artifact.id,
                            })),
                        }
                    }
                    _ => {
                        RuleEvaluation {
                            rule_id: rule_config.id.clone(),
                            status: RuleStatus::Error,
                            message: Some("rule_evidence.error.RV-07.not_true".to_string()),
                            message_params: Some(json!({
                                "artifact_id": artifact.id,
                                "artifact_type": found_type,
                                "marker_field": marker_field,
                            })),
                        }
                    }
                }
            }
            None => {
                RuleEvaluation {
                    rule_id: rule_config.id.clone(),
                    status: RuleStatus::Error,
                    message: Some("rule_evidence.error.RV-07.not_found".to_string()),
                    message_params: Some(json!({
                        "artifact_type": t,
                    })),
                }
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

        fn make_rule_with_type(id: &str, artifact_type: &str) -> VerificationRule {
            VerificationRule {
                id: id.to_string(),
                severity: "OBLIGATORIA".to_string(),
                params: json!({"artifact_type": artifact_type}),
            }
        }

        fn make_rule_no_params(id: &str) -> VerificationRule {
            VerificationRule {
                id: id.to_string(),
                severity: "OBLIGATORIA".to_string(),
                params: json!({}),
            }
        }

        /// TC-UNI-MOT-07: RV-07 caso base — marcador de registro externo encontrado.
        /// Each Choice: cubre el resultado OK para registro externo.
        #[test]
        fn tc_uni_mot_07_rv07_marker_found_returns_ok() {
            let artifacts = vec![
                make_artifact("T-001", "TAREA", json!({"external_registered": true})),
            ];
            let rule = make_rule_with_type("RV-07", "TAREA");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
            assert!(result.message.is_some());
        }

        #[test]
        fn no_artifact_type_configured_returns_no_evaluada() {
            // No connector exposes a generic "external_registered" marker natively,
            // so searching across all types without a configured artifact_type can
            // never meaningfully pass or fail - it's a missing configuration.
            let artifacts = vec![
                make_artifact("T-001", "TAREA", json!({"external_registered": true})),
            ];
            let rule = make_rule_no_params("RV-07");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::NoEvaluada);
            assert_eq!(result.message.unwrap(), "rule_evidence.no_evaluada.RV-07");
        }

        #[test]
        fn plan_artifact_existence_is_sufficient_without_marker_field() {
            // A PLAN artifact comes from an external planning tool (e.g. ClickUp) by
            // definition - its mere presence in the release already proves external
            // registration, no synthetic boolean field required.
            let artifacts = vec![
                make_artifact("P-001", "PLAN", json!({})),
            ];
            let rule = make_rule_with_type("RV-07", "PLAN");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
            assert_eq!(result.message.unwrap(), "rule_evidence.ok.RV-07.found");
        }

        #[test]
        fn marker_artifact_not_found_returns_error() {
            let artifacts = vec![
                make_artifact("C-001", "CODIGO", json!({})),
            ];
            let rule = make_rule_with_type("RV-07", "TAREA");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-07.not_found");
            let params = result.message_params.unwrap();
            assert!(params["artifact_type"].as_str().unwrap().contains("TAREA"));
        }

        #[test]
        fn marker_field_false_returns_error() {
            let artifacts = vec![
                make_artifact("T-001", "TAREA", json!({"external_registered": false})),
            ];
            let rule = make_rule_with_type("RV-07", "TAREA");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-07.not_true");
            let params = result.message_params.unwrap();
            assert!(params["artifact_id"].as_str().unwrap().contains("T-001"));
        }

        #[test]
        fn marker_field_missing_returns_error() {
            let artifacts = vec![
                make_artifact("T-001", "TAREA", json!({"other_field": true})),
            ];
            let rule = make_rule_with_type("RV-07", "TAREA");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
        }

        #[test]
        fn tipo_no_permitido_devuelve_error() {
            let artifacts = vec![
                make_artifact("D-001", "DOCUMENTO", json!({"external_registered": true})),
            ];
            let rule = make_rule_with_type("RV-07", "DOCUMENTO");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-07.tipo_no_permitido");
        }
    }
}

pub mod rv08 {
    use serde_json::json;
    use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};
    use std::collections::HashSet;

    /// RV-08: Compara dos conjuntos de identificadores: los declarados en un artefacto
    /// maestro (mapeo) frente a los que realmente se han enviado en el payload.
    ///
    /// # Parámetros
    /// * `artifacts` - Slice de artefactos a verificar.
    /// * `rule_config` - Configuración de la regla con parámetros:
    ///   - `master_artifact_id` (opcional): ID (UUID interno de SVAES) del artefacto
    ///     maestro que contiene la lista de IDs declarados. Permite fijar explícitamente
    ///     cuál de los artefactos de esta entrega actúa como "maestro". Si se omite,
    ///     el maestro se autodetecta (ver `master_type`) para que la regla funcione
    ///     sin configuración adicional en el perfil por defecto del sistema, ya que el
    ///     UUID interno cambia en cada entrega/organización y no puede fijarse a nivel
    ///     de perfil compartido.
    ///   - `master_type`: Tipo de artefacto que se autodetecta como maestro cuando no
    ///     se especifica `master_artifact_id` (default: "PLAN"). Debe existir
    ///     exactamente un artefacto de este tipo en la entrega; si no hay ninguno la
    ///     regla queda No evaluada, y si hay más de uno se requiere `master_artifact_id`
    ///     para desambiguar.
    ///   - `master_field`: Campo en metadata del maestro que contiene la lista de
    ///     IDs declarados (default: "planned_tasks"). Acepta un array JSON o una
    ///     cadena separada por comas (para campos de texto simples en el conector,
    ///     p. ej. un campo personalizado de ClickUp).
    ///   - `target_type`: Tipo de artefactos a comparar con la lista del maestro (default: "TAREA").
    ///
    /// # Lógica
    /// 1. Determina el artefacto maestro: por `master_artifact_id` si se indica, o
    ///    autodetectando el único artefacto de tipo `master_type` en la entrega.
    /// 2. Extrae la lista de IDs declarados desde el campo especificado de su metadata.
    /// 3. Recopila la **referencia externa** (`_svaes_external_ref`, la que el usuario
    ///    introdujo al importar el artefacto, p. ej. "SVAES-1") de los artefactos del
    ///    tipo especificado - nunca su UUID interno, que ninguna herramienta externa
    ///    puede conocer ni declarar.
    /// 4. Compara ambos conjuntos y calcula la diferencia.
    /// 5. Si hay IDs faltantes (en payload pero no declarados) o sobrantes (declarados pero no en payload), retorna Error.
    /// 6. Si ambos conjuntos coinciden exactamente, retorna Ok.
    ///
    /// # Retorno
    /// `RuleEvaluation` con el estado correspondiente y lista de IDs faltantes/sobrantes.
    pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
        let master_type = rule_config.params
            .get("master_type")
            .and_then(|v| v.as_str())
            .unwrap_or("PLAN");

        let master = match rule_config.params.get("master_artifact_id").and_then(|v| v.as_str()) {
            Some(master_id) => match artifacts.iter().find(|a| a.id == master_id) {
                Some(a) => a,
                None => {
                    return RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::Error,
                        message: Some("rule_evidence.error.RV-08.master_not_found".to_string()),
                        message_params: Some(json!({
                            "master_id": master_id,
                        })),
                    };
                }
            },
            None => {
                let candidates: Vec<&Artifact> = artifacts.iter().filter(|a| a.artifact_type == master_type).collect();
                match candidates.as_slice() {
                    [] => {
                        return RuleEvaluation {
                            rule_id: rule_config.id.clone(),
                            status: RuleStatus::NoEvaluada,
                            message: Some("rule_evidence.no_evaluada.RV-08".to_string()),
                            message_params: Some(json!({
                                "master_type": master_type,
                            })),
                        };
                    }
                    [single] => *single,
                    multiple => {
                        return RuleEvaluation {
                            rule_id: rule_config.id.clone(),
                            status: RuleStatus::Error,
                            message: Some("rule_evidence.error.RV-08.multiple_masters_found".to_string()),
                            message_params: Some(json!({
                                "master_type": master_type,
                                "count": multiple.len(),
                            })),
                        };
                    }
                }
            }
        };

        let master_field = rule_config.params
            .get("master_field")
            .and_then(|v| v.as_str())
            .unwrap_or("planned_tasks");

        let target_type = rule_config.params
            .get("target_type")
            .and_then(|v| v.as_str())
            .unwrap_or("TAREA");

        let declared_ids: HashSet<&str> = match master.metadata.get(master_field) {
            Some(val) => {
                if let Some(arr) = val.as_array() {
                    arr.iter().filter_map(|v| v.as_str()).collect()
                } else if let Some(s) = val.as_str() {
                    // Plain text custom fields (e.g. a ClickUp text field with
                    // "SVAES-1, SVAES-2") are a realistic way to declare this list
                    // without needing a structured array type in the source tool.
                    s.split(',').map(|part| part.trim()).filter(|part| !part.is_empty()).collect()
                } else {
                    return RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::Error,
                        message: Some("rule_evidence.error.RV-08.field_not_array".to_string()),
                        message_params: Some(json!({
                            "master_field": master_field,
                            "master_id": master.id.as_str(),
                        })),
                    };
                }
            }
            None => {
                return RuleEvaluation {
                    rule_id: rule_config.id.clone(),
                    status: RuleStatus::Error,
                    message: Some("rule_evidence.error.RV-08.field_not_found".to_string()),
                    message_params: Some(json!({
                        "master_field": master_field,
                        "master_id": master.id.as_str(),
                    })),
                };
            }
        };

        // Compare against each artifact's *external* reference (the one the user
        // typed when importing it, e.g. "SVAES-1") - not its internal SVAES UUID,
        // which no external tool can ever know or declare in a "planned tasks" field.
        let actual_ids: HashSet<&str> = artifacts
            .iter()
            .filter(|a| a.artifact_type == target_type)
            .filter_map(|a| a.metadata.get("_svaes_external_ref").and_then(|v| v.as_str()))
            .collect();

        let missing_in_payload: Vec<&str> = declared_ids
            .difference(&actual_ids)
            .copied()
            .collect();

        if missing_in_payload.is_empty() && declared_ids.len() == actual_ids.len() {
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
                message: Some("rule_evidence.error.RV-08.discrepancy".to_string()),
                message_params: Some(json!({
                    "master_field": master_field,
                    "master_id": master.id.as_str(),
                    "target_type": target_type,
                    "missing_ids": format!("{:?}", missing_in_payload),
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

        /// A TAREA artifact as it actually arrives from the API: internal UUID
        /// (`id`) distinct from the external reference the user typed on import
        /// (e.g. "SVAES-1"), which is what a master artifact must declare.
        fn make_tarea(id: &str, external_ref: &str) -> Artifact {
            Artifact {
                id: id.to_string(),
                artifact_type: "TAREA".to_string(),
                metadata: json!({"_svaes_external_ref": external_ref}),
            }
        }

        fn make_rule(id: &str, master_id: &str) -> VerificationRule {
            VerificationRule {
                id: id.to_string(),
                severity: "OBLIGATORIA".to_string(),
                params: json!({"master_artifact_id": master_id}),
            }
        }

        /// TC-UNI-MOT-08: RV-08 caso base — coincidencia exacta entre lista declarada y payload.
        /// Each Choice: cubre el resultado OK para alineación de listas de planificación.
        #[test]
        fn tc_uni_mot_08_rv08_exact_match_returns_ok() {
            let artifacts = vec![
                make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": ["SVAES-1", "SVAES-2"]})),
                make_tarea("uuid-t1", "SVAES-1"),
                make_tarea("uuid-t2", "SVAES-2"),
            ];
            let rule = make_rule("RV-08", "uuid-plan");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
            assert!(result.message.is_none());
        }

        #[test]
        fn comma_separated_text_field_is_accepted() {
            // A plain ClickUp text custom field (not a structured array type) with
            // "SVAES-1, SVAES-2" must work just as well as a JSON array.
            let artifacts = vec![
                make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": "SVAES-1, SVAES-2"})),
                make_tarea("uuid-t1", "SVAES-1"),
                make_tarea("uuid-t2", "SVAES-2"),
            ];
            let rule = make_rule("RV-08", "uuid-plan");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn missing_master_artifact_id_param_returns_no_evaluada() {
            let rule = VerificationRule {
                id: "RV-08".to_string(),
                severity: "OBLIGATORIA".to_string(),
                params: serde_json::json!({}),
            };
            let result = evaluate(&[], &rule);
            assert_eq!(result.status, RuleStatus::NoEvaluada);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.no_evaluada.RV-08");
        }

        #[test]
        fn master_artifact_not_found_returns_error() {
            let artifacts = vec![
                make_tarea("uuid-t1", "SVAES-1"),
            ];
            let rule = make_rule("RV-08", "PLAN-999");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-08.master_not_found");
            let params = result.message_params.unwrap();
            assert!(params["master_id"].as_str().unwrap().contains("PLAN-999"));
        }

        #[test]
        fn declared_task_missing_from_payload_returns_error() {
            let artifacts = vec![
                make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": ["SVAES-1", "SVAES-2", "SVAES-3"]})),
                make_tarea("uuid-t1", "SVAES-1"),
                make_tarea("uuid-t2", "SVAES-2"),
            ];
            let rule = make_rule("RV-08", "uuid-plan");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-08.discrepancy");
            let params = result.message_params.unwrap();
            assert!(params["missing_ids"].as_str().unwrap().contains("SVAES-3"));
        }

        #[test]
        fn extra_task_not_declared_returns_error() {
            let artifacts = vec![
                make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": ["SVAES-1"]})),
                make_tarea("uuid-t1", "SVAES-1"),
                make_tarea("uuid-t2", "SVAES-2"),
            ];
            let rule = make_rule("RV-08", "uuid-plan");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
        }

        fn make_rule_without_master_id(id: &str) -> VerificationRule {
            VerificationRule {
                id: id.to_string(),
                severity: "OBLIGATORIA".to_string(),
                params: json!({}),
            }
        }

        /// The system default profile ships RV-08 with no `master_artifact_id` (that
        /// UUID is release/org-specific and can't be fixed at the shared-profile
        /// level) - the rule must still pass by auto-detecting the single PLAN
        /// artifact as master, e.g. the ClickUp "Release x.y.z" item.
        #[test]
        fn auto_detects_single_plan_artifact_as_master_when_id_not_given() {
            let artifacts = vec![
                make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": "SVAES-1,SVAES-2"})),
                make_tarea("uuid-t1", "SVAES-1"),
                make_tarea("uuid-t2", "SVAES-2"),
            ];
            let rule = make_rule_without_master_id("RV-08");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn no_plan_artifact_and_no_master_id_returns_no_evaluada_with_master_type() {
            let artifacts = vec![make_tarea("uuid-t1", "SVAES-1")];
            let rule = make_rule_without_master_id("RV-08");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::NoEvaluada);
            let params = result.message_params.unwrap();
            assert_eq!(params["master_type"].as_str().unwrap(), "PLAN");
        }

        #[test]
        fn multiple_plan_artifacts_without_master_id_returns_error() {
            let artifacts = vec![
                make_artifact("uuid-plan-1", "PLAN", json!({"planned_tasks": ["SVAES-1"]})),
                make_artifact("uuid-plan-2", "PLAN", json!({"planned_tasks": ["SVAES-1"]})),
                make_tarea("uuid-t1", "SVAES-1"),
            ];
            let rule = make_rule_without_master_id("RV-08");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-08.multiple_masters_found");
            let params = result.message_params.unwrap();
            assert_eq!(params["count"].as_u64().unwrap(), 2);
        }
    }
}

pub mod rv09 {
    use serde_json::json;
    use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

    /// RV-09: Verifica que las referencias de origen (links o ramas) en la metadata
    /// de los artefactos tengan un formato válido y estén marcadas como accesibles.
    ///
    /// # Parámetros
    /// * `artifacts` - Slice de artefactos a verificar.
    /// * `rule_config` - Configuración de la regla con parámetros:
    ///   - `artifact_type`: Tipo de artefacto a verificar (default: "CODIGO").
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
                message_params: None,
            }
        } else {
            RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some("rule_evidence.error.RV-09".to_string()),
                message_params: Some(json!({
                    "invalid_refs": format!("{:?}", invalid_refs),
                })),
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
            .unwrap_or("CODIGO");

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
                "CODIGO",
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
                "CODIGO",
                json!({
                    "link": "ftp://bad-protocol.com",
                    "accessible": true
                }),
            )];
            let rule = make_rule("RV-09");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-09");
            let params = result.message_params.unwrap();
            assert!(params["invalid_refs"].as_str().unwrap().contains("C-002/link"));
        }

        /// Branch: invalid branch name (empty) → Error
        #[test]
        fn invalid_branch_returns_error() {
            let artifacts = vec![make_artifact(
                "C-003",
                "CODIGO",
                json!({
                    "branch": "",
                    "accessible": true
                }),
            )];
            let rule = make_rule("RV-09");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-09");
            let params = result.message_params.unwrap();
            assert!(params["invalid_refs"].as_str().unwrap().contains("C-003/branch"));
        }

        /// Branch: accessible field is false → Error
        #[test]
        fn not_accessible_returns_error() {
            let artifacts = vec![make_artifact(
                "C-004",
                "CODIGO",
                json!({
                    "link": "https://valid.com",
                    "accessible": false
                }),
            )];
            let rule = make_rule("RV-09");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-09");
            let params = result.message_params.unwrap();
            assert!(params["invalid_refs"].as_str().unwrap().contains("no accesible"));
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
                "CODIGO",
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
                "CODIGO",
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
                "CODIGO",
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
                    "CODIGO",
                    json!({
                        "link": "invalid-link",
                        "accessible": true
                    }),
                ),
                make_artifact(
                    "C-009",
                    "CODIGO",
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
            assert_eq!(msg, "rule_evidence.error.RV-09");
            let params = result.message_params.unwrap();
            let refs = params["invalid_refs"].as_str().unwrap();
            assert!(refs.contains("C-008/link"));
            assert!(refs.contains("C-009/accessible"));
        }
    }
}

pub mod rv10 {
    use serde_json::json;
    use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

    /// RV-10: Busca un artefacto de un tipo concreto que posea un atributo de estado
    /// igual a "APROBADO" o "VALIDADO".
    ///
    /// # Parámetros
    /// * `artifacts` - Slice de artefactos a verificar.
    /// * `rule_config` - Configuración de la regla con parámetros:
    ///   - `artifact_type`: Tipo de artefacto a buscar (default: "DOCUMENTO").
    ///   - `status_field`: Campo en metadata que contiene el estado (default: "status").
    ///   - `approved_states`: Array de estados que se consideran aprobados (default: ["APROBADO", "VALIDADO"]).
    ///
    /// # Lógica
    /// 1. Obtiene el tipo de artefacto, campo de estado y valores considerados como aprobados.
    /// 2. Filtra los artefactos por tipo.
    /// 3. Busca un artefacto cuyo campo de estado sea alguno de los valores aprobados.
    /// 4. Si lo encuentra, retorna Ok; si no, retorna Error.
    ///
    /// # Retorno
    /// `RuleEvaluation` con el estado correspondiente indicando si se encontró el artefacto aprobado.
    pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
        let artifact_type = rule_config.params
            .get("artifact_type")
            .and_then(|v| v.as_str())
            .unwrap_or("DOCUMENTO");

        let status_field = rule_config.params
            .get("status_field")
            .and_then(|v| v.as_str())
            .unwrap_or("status");

        let approved_states: Vec<&str> = rule_config.params
            .get("approved_states")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
            // "current" is Confluence's own native status for a live/published page
            // (as opposed to "draft"/"trashed"), so a document connector that has no
            // custom approval field still counts as approved by default when live.
            .unwrap_or_else(|| vec!["APROBADO", "VALIDADO", "current"]);

        let approved_artifact = artifacts
            .iter()
            .filter(|a| a.artifact_type == artifact_type)
            .find(|a| {
                match a.metadata.get(status_field) {
                    Some(val) => val.as_str().map(|s| approved_states.contains(&s)).unwrap_or(false),
                    None => false,
                }
            });

        match approved_artifact {
            Some(artifact) => {
                RuleEvaluation {
                    rule_id: rule_config.id.clone(),
                    status: RuleStatus::Ok,
                    message: Some("rule_evidence.ok.RV-10.found".to_string()),
                    message_params: Some(json!({
                        "artifact_id": artifact.id,
                        "artifact_type": artifact_type,
                        "approved_status": artifact.metadata.get(status_field).and_then(|v| v.as_str()).unwrap_or("desconocido"),
                    })),
                }
            }
            None => {
                RuleEvaluation {
                    rule_id: rule_config.id.clone(),
                    status: RuleStatus::Error,
                    message: Some("rule_evidence.error.RV-10".to_string()),
                    message_params: Some(json!({
                        "artifact_type": artifact_type,
                        "approved_states": format!("{:?}", approved_states),
                    })),
                }
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

        /// TC-UNI-MOT-10: RV-10 caso base — artefacto con estado de aprobación encontrado.
        /// Each Choice: cubre el resultado OK para aprobación final.
        #[test]
        fn tc_uni_mot_10_rv10_approved_artifact_returns_ok() {
            let artifacts = vec![
                make_artifact("D-001", "DOCUMENTO", json!({"status": "APROBADO"})),
            ];
            let rule = make_rule("RV-10");

            let result = evaluate(&artifacts, &rule);

            assert_eq!(result.status, RuleStatus::Ok);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.ok.RV-10.found");
            let params = result.message_params.unwrap();
            assert!(params["artifact_id"].as_str().unwrap().contains("D-001"));
            assert!(params["approved_status"].as_str().unwrap().contains("APROBADO"));
        }

        #[test]
        fn validado_state_also_accepted() {
            let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"status": "VALIDADO"}))];
            let result = evaluate(&artifacts, &make_rule("RV-10"));
            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn no_documents_returns_error() {
            let artifacts = vec![make_artifact("T-001", "TAREA", json!({"status": "APROBADO"}))];
            let result = evaluate(&artifacts, &make_rule("RV-10"));
            assert_eq!(result.status, RuleStatus::Error);
            let msg = result.message.unwrap();
            assert_eq!(msg, "rule_evidence.error.RV-10");
            let params = result.message_params.unwrap();
            assert!(params["artifact_type"].as_str().unwrap().contains("DOCUMENTO"));
        }

        #[test]
        fn document_with_non_approved_status_returns_error() {
            let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"status": "BORRADOR"}))];
            let result = evaluate(&artifacts, &make_rule("RV-10"));
            assert_eq!(result.status, RuleStatus::Error);
        }

        #[test]
        fn document_with_missing_status_returns_error() {
            let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({}))];
            let result = evaluate(&artifacts, &make_rule("RV-10"));
            assert_eq!(result.status, RuleStatus::Error);
        }

        #[test]
        fn confluence_current_status_accepted_by_default() {
            // A published (non-draft) Confluence page has status "current" natively -
            // it should count as approved out of the box, without requiring a custom
            // approval field that Confluence doesn't have.
            let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"status": "current"}))];
            let result = evaluate(&artifacts, &make_rule("RV-10"));
            assert_eq!(result.status, RuleStatus::Ok);
        }

        #[test]
        fn custom_approved_states_respected() {
            let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"status": "REVIEWED"}))];
            let rule = VerificationRule {
                id: "RV-10".to_string(),
                severity: "OBLIGATORIA".to_string(),
                params: json!({"approved_states": ["REVIEWED", "SIGNED"]}),
            };
            let result = evaluate(&artifacts, &rule);
            assert_eq!(result.status, RuleStatus::Ok);
        }
    }
}
