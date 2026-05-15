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