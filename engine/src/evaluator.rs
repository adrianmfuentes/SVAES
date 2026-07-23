use rayon::prelude::*; // Importamos Rayon para la ejecución paralela de las reglas de verificación.
use crate::models::{VerificationPayload, EngineResult, RuleEvaluation, RuleStatus}; // Importamos las estructuras de datos definidas en el módulo models.
use crate::aggregator::aggregate; // Importamos la función de agregación para calcular el veredicto global a partir de los resultados individuales de las reglas.
use crate::rules; // Importamos el módulo de reglas donde se implementarán las funciones de evaluación específicas para cada regla del catálogo.

/*
Esta función es el core del motor de verificación. Recibe un payload con los artefactos y las reglas a evaluar, ejecuta cada regla en paralelo utilizando Rayon,
y luego agrega los resultados para determinar el veredicto global. El resultado final se devuelve en una estructura EngineResult que incluye tanto el veredicto 
como los detalles de la evaluación de cada regla.

Parámetros:
    - payload: Estructura que contiene el release_id, la lista de artefactos a evaluar y la lista de reglas de verificación a aplicar.

Lógica de la función:
    1. Se ejecutan las reglas en paralelo utilizando Rayon. Para cada regla, se verifica si está marcada como "EXCLUIDA" y se omite su evaluación si es así.
    2. Se utiliza un despachador para llamar a la función de evaluación correspondiente a cada regla. Si una regla no está implementada, se marca como "NoEvaluada".
    3. Una vez obtenidos los resultados de todas las reglas, se llama a la función de agregación para calcular el veredicto global.
    4. Finalmente, se devuelve un EngineResult que contiene el veredicto global y la lista de resultados detallados de cada regla evaluada.

Retorna:
    - EngineResult: Estructura que incluye el veredicto global de la verificación y los resultados detallados de cada regla evaluada.
*/
pub fn evaluate(payload: VerificationPayload) -> EngineResult {
    // 1. Ejecución paralela de las reglas mediante Rayon
    let rule_results: Vec<RuleEvaluation> = payload.rules // Creamos un iterador sobre las reglas de recibidas en el payload
        .par_iter() // Transformamos el iterador en uno paralelo
        .map(|rule_config| { // Para cada regla:            
            if rule_config.severity == "EXCLUIDA" {  // 1. Saltamos la evaluación si la regla está marcada como EXCLUIDA
                return RuleEvaluation {
                    rule_id: rule_config.id.clone(),
                    status: RuleStatus::NoEvaluada,
                    message: Some("Regla excluida en el perfil".to_string()),
                    message_params: None,
                };
            }
                                                                                    
            match rule_config.id.as_str() { // Despachador de reglas
                "RV-01" => rules::rv01::evaluate(&payload.artifacts, rule_config),
                "RV-02" => rules::rv02::evaluate(&payload.artifacts, rule_config),
                "RV-03" => rules::rv03::evaluate(&payload.artifacts, rule_config),
                "RV-04" => rules::rv04::evaluate(&payload.artifacts, rule_config),
                "RV-05" => rules::rv05::evaluate(&payload.artifacts, rule_config),
                "RV-06" => rules::rv06::evaluate(&payload.artifacts, rule_config, payload.release_version.as_deref()),
                "RV-07" => rules::rv07::evaluate(&payload.artifacts, rule_config),
                "RV-08" => rules::rv08::evaluate(&payload.artifacts, rule_config),
                "RV-09" => rules::rv09::evaluate(&payload.artifacts, rule_config),
                "RV-10" => rules::rv10::evaluate(&payload.artifacts, rule_config),
                "custom_field_check" => rules::custom_field_check::evaluate(&payload.artifacts, rule_config),
                _ => RuleEvaluation {
                    rule_id: rule_config.id.clone(),
                    status: RuleStatus::NoEvaluada,
                    message: Some("ID de regla no reconocido en el catálogo".to_string()),
                    message_params: None,
                },
            }
        }) // Mapeamos cada regla a su resultado de evaluación, obteniendo un iterador de RuleEvaluation
        .collect(); // Colectamos los resultados en un vector de RuleEvaluation

    // Agregación de resultados para calcular el veredicto global
    let verdict = aggregate(&rule_results, &payload.rules);

    let summary = generate_summary(&verdict, &rule_results);

    EngineResult {
        verdict,
        rule_results,
        summary,
    }
}

fn generate_summary(_verdict: &crate::models::Verdict, rule_results: &[RuleEvaluation]) -> crate::models::SummaryData {
    let total = rule_results.len();
    let ok_count = rule_results.iter().filter(|r| r.status == RuleStatus::Ok).count();
    let error_count = rule_results.iter().filter(|r| r.status == RuleStatus::Error).count();
    let warning_count = rule_results.iter().filter(|r| r.status == RuleStatus::Warning).count();
    let not_evaluated = rule_results.iter().filter(|r| r.status == RuleStatus::NoEvaluada).count();

    crate::models::SummaryData {
        total,
        ok: ok_count,
        error: error_count,
        warning: warning_count,
        not_evaluated,
    }
}