use crate::models::{RuleEvaluation, RuleStatus, Verdict, VerificationRule}; // Importamos las estructuras y enums necesarios desde el módulo de modelos.

/*
Función de agregación que toma las evaluaciones de reglas y las reglas de verificación para determinar el veredicto global.

Parámetros:
    - `evaluations`: Un slice de `RuleEvaluation` que contiene el resultado de la evaluación de cada regla.
    - `rules`: Un slice de `VerificationRule` que contiene la configuración de cada regla, incluyendo su severidad (OBLIGATORIA u OPCIONAL).
    
Lógica de agregación:
    1. Si una regla OBLIGATORIA tiene un ERROR, el veredicto es NO_VÁLIDA.
    2. Si las obligatorias están OK pero una OPCIONAL tiene WARNING, el veredicto es CON_ADVERTENCIAS.
    3. Si todas las reglas obligatorias están OK y no hay advertencias en las opcionales, el veredicto es VÁLIDA.

Retorna:
    - Un `Verdict` que representa el resultado global de la evaluación de las reglas.
*/
pub fn aggregate(evaluations: &[RuleEvaluation], rules: &[VerificationRule]) -> Verdict {
    let mut has_mandatory_error = false;
    let mut has_optional_warning = false;

    for evaluation in evaluations {
        // Buscamos la configuración de la regla para conocer su severidad.
        if let Some(rule_config) = rules.iter().find(|r| r.id == evaluation.rule_id) {
            
            match evaluation.status {
                // Si una regla OBLIGATORIA tiene un ERROR, el veredicto es NO_VÁLIDA.
                RuleStatus::Error if rule_config.severity == "OBLIGATORIA" => {
                    has_mandatory_error = true;
                }
                // Si las obligatorias están OK pero una OPCIONAL tiene WARNING, el veredicto es CON_ADVERTENCIAS.
                RuleStatus::Warning if rule_config.severity == "OPCIONAL" => {
                    has_optional_warning = true;
                }
                // Las reglas NO_EVALUADA no computan para el veredicto global.
                _ => {}
            }
        }
    }

    if has_mandatory_error {
        Verdict::NoValida
    } else if has_optional_warning {
        Verdict::ConAdvertencias
    } else {
        Verdict::Valida
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::RuleStatus;

    fn make_evaluation(rule_id: &str, status: RuleStatus) -> RuleEvaluation {
        RuleEvaluation {
            rule_id: rule_id.to_string(),
            status,
            message: None,
        }
    }

    fn make_rule(rule_id: &str, severity: &str) -> VerificationRule {
        VerificationRule {
            id: rule_id.to_string(),
            severity: severity.to_string(),
            params: serde_json::json!({}),
        }
    }

    /// **TC-UNI-AGG-01**: Todas las reglas OK retornan `Valida`.
    ///
    /// ## Escenario
    /// Una regla OBLIGATORIA y una OPCIONAL, ambas con estado `Ok`.
    ///
    /// ## Resultado esperado
    /// `Verdict::Valida` — sin errores ni advertencias.
    ///
    /// ## Cobertura
    /// Transición base: 0 errores obligatorios + 0 advertencias opcionales.
    #[test]
    fn tc_uni_agg_01_all_rules_ok_returns_valida() {
        let evaluations = vec![
            make_evaluation("RV-01", RuleStatus::Ok),
            make_evaluation("RV-02", RuleStatus::Ok),
        ];
        let rules = vec![
            make_rule("RV-01", "OBLIGATORIA"),
            make_rule("RV-02", "OPCIONAL"),
        ];

        let verdict = aggregate(&evaluations, &rules);

        assert!(matches!(verdict, Verdict::Valida));
    }

    /// **TC-UNI-AGG-02**: Un error en regla OBLIGATORIA retorna `NoValida`.
    ///
    /// ## Escenario
    /// Una regla OBLIGATORIA con `Error` y una OPCIONAL con `Ok`.
    ///
    /// ## Resultado esperado
    /// `Verdict::NoValida` — el error obligatorio domina sobre el resto.
    ///
    /// ## Cobertura
    /// Caso minimo: exactamente 1 error obligatorio.
    #[test]
    fn tc_uni_agg_02_one_mandatory_error_returns_no_valida() {
        let evaluations = vec![
            make_evaluation("RV-01", RuleStatus::Error),
            make_evaluation("RV-02", RuleStatus::Ok),
        ];
        let rules = vec![
            make_rule("RV-01", "OBLIGATORIA"),
            make_rule("RV-02", "OPCIONAL"),
        ];

        let verdict = aggregate(&evaluations, &rules);

        assert!(matches!(verdict, Verdict::NoValida));
    }

    /// **TC-UNI-AGG-03**: Advertencia en regla OPCIONAL retorna `ConAdvertencias`.
    ///
    /// ## Escenario
    /// Una regla OBLIGATORIA con `Ok` y una OPCIONAL con `Warning`.
    ///
    /// ## Resultado esperado
    /// `Verdict::ConAdvertencias` — sin errores obligatorios, pero con advertencias
    /// opcionales que deben notificarse.
    ///
    /// ## Cobertura
    /// Camino alternativo: warning opcional sin error obligatorio.
    #[test]
    fn tc_uni_agg_03_optional_warning_without_mandatory_error_returns_con_advertencias() {
        let evaluations = vec![
            make_evaluation("RV-01", RuleStatus::Ok),
            make_evaluation("RV-02", RuleStatus::Warning),
        ];
        let rules = vec![
            make_rule("RV-01", "OBLIGATORIA"),
            make_rule("RV-02", "OPCIONAL"),
        ];

        let verdict = aggregate(&evaluations, &rules);

        assert!(matches!(verdict, Verdict::ConAdvertencias));
    }

    /// **TC-UNI-AGG-04**: Transicion de 0 a 1 errores obligatorios.
    ///
    /// ## Escenario
    /// Subcaso A: 1 regla OBLIGATORIA con `Ok` → `Valida`.
    /// Subcaso B: la misma regla con `Error` → `NoValida`.
    ///
    /// ## Resultado esperado
    /// Cambio abrupto del veredicto al superar el umbral de 0 errores. Valida
    /// que no existe zona gris entre `Valida` y `NoValida`.
    ///
    /// ## Cobertura
    /// Valor limite: el minimo numero de errores que cambia el veredicto.
    #[test]
    fn tc_uni_agg_04_transition_zero_to_one_mandatory_errors() {
        let evaluations_zero = vec![
            make_evaluation("RV-01", RuleStatus::Ok),
        ];
        let rules = vec![
            make_rule("RV-01", "OBLIGATORIA"),
        ];

        let verdict_zero = aggregate(&evaluations_zero, &rules);
        assert!(matches!(verdict_zero, Verdict::Valida));

        let evaluations_one = vec![
            make_evaluation("RV-01", RuleStatus::Error),
        ];

        let verdict_one = aggregate(&evaluations_one, &rules);
        assert!(matches!(verdict_one, Verdict::NoValida));
    }

    /// **TC-UNI-AGG-05**: Reglas EXCLUIDA (`NoEvaluada`) no afectan al veredicto.
    ///
    /// ## Escenario
    /// 1 regla OBLIGATORIA `Ok` + 1 regla EXCLUIDA con `NoEvaluada`.
    ///
    /// ## Resultado esperado
    /// `Verdict::Valida` — las reglas excluidas son ignoradas por el agregador,
    /// independientemente de su estado.
    ///
    /// ## Cobertura
    /// Comportamiento de la severidad `EXCLUIDA` en el flujo de agregacion.
    #[test]
    fn tc_uni_agg_05_excluida_rules_no_evaluada_do_not_affect_verdict() {
        let evaluations = vec![
            make_evaluation("RV-01", RuleStatus::Ok),
            make_evaluation("RV-02", RuleStatus::NoEvaluada),
        ];
        let rules = vec![
            make_rule("RV-01", "OBLIGATORIA"),
            make_rule("RV-02", "EXCLUIDA"),
        ];

        let verdict = aggregate(&evaluations, &rules);

        assert!(matches!(verdict, Verdict::Valida));
    }

    /// **TC-UNI-AGG-06**: Error OBLIGATORIO prevalece sobre Warning OPCIONAL.
    ///
    /// ## Escenario
    /// 1 regla OBLIGATORIA con `Error` + 1 OPCIONAL con `Warning`.
    ///
    /// ## Resultado esperado
    /// `Verdict::NoValida` — el error obligatorio debe tener precedencia sobre
    /// cualquier advertencia opcional. No se debe retornar `ConAdvertencias`.
    ///
    /// ## Cobertura
    /// Regla de precedencia: OBLIGATORIA Error > OPCIONAL Warning.
    #[test]
    fn tc_uni_agg_06_mandatory_error_overrides_optional_warning() {
        let evaluations = vec![
            make_evaluation("RV-01", RuleStatus::Error),
            make_evaluation("RV-02", RuleStatus::Warning),
        ];
        let rules = vec![
            make_rule("RV-01", "OBLIGATORIA"),
            make_rule("RV-02", "OPCIONAL"),
        ];

        let verdict = aggregate(&evaluations, &rules);

        assert!(
            matches!(verdict, Verdict::NoValida),
            "OBLIGATORIA Error debe prevalecer sobre OPCIONAL Warning"
        );
    }

    /// **TC-UNI-AGG-07**: Multiples errores obligatorios confirman `NoValida`.
    ///
    /// ## Escenario
    /// 2 reglas OBLIGATORIA con `Error` + 1 OPCIONAL con `Warning`.
    ///
    /// ## Resultado esperado
    /// `Verdict::NoValida` — N errores obligatorios producen el mismo veredicto
    /// que 1. La presencia de advertencias no atenua el resultado.
    ///
    /// ## Cobertura
    /// Acumulacion: multiples errores obligatorios no degradan ni mejoran el
    /// veredicto (sigue siendo `NoValida`).
    #[test]
    fn tc_uni_agg_07_multiple_mandatory_errors_returns_no_valida() {
        let evaluations = vec![
            make_evaluation("RV-01", RuleStatus::Error),
            make_evaluation("RV-02", RuleStatus::Error),
            make_evaluation("RV-03", RuleStatus::Warning),
        ];
        let rules = vec![
            make_rule("RV-01", "OBLIGATORIA"),
            make_rule("RV-02", "OBLIGATORIA"),
            make_rule("RV-03", "OPCIONAL"),
        ];

        let verdict = aggregate(&evaluations, &rules);

        assert!(matches!(verdict, Verdict::NoValida));
    }
}