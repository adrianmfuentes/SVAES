RULE_DEFAULT_ARTIFACT_TYPES: dict[str, str] = {
    "RV-03": "TAREA",
    "RV-04": "TAREA",
    "RV-05": "DOCUMENTO",
    "RV-06": "DOCUMENTO",
    "RV-09": "CODIGO",
    "RV-10": "DOCUMENTO",
    "custom_field_check": "TAREA",
}

CUSTOM_FIELD_CHECK_OPERATORS: set[str] = {
    "non_empty",
    "equals",
    "not_equals",
    "contains",
    "gt",
    "gte",
    "lt",
    "lte",
}

RULE_CONNECTOR_TYPES_MODE: dict[str, str] = {
    "RV-07": "ANY",
}

RULE_CONNECTOR_TYPES: dict[str, list[str]] = {
    "RV-01": [],
    "RV-02": ["GESTOR_TAREAS", "REPO_CODIGO"],
    "RV-03": ["GESTOR_TAREAS"],
    "RV-04": ["GESTOR_TAREAS"],
    "RV-05": ["SISTEMA_DOCUMENTAL"],
    "RV-06": ["SISTEMA_DOCUMENTAL"],
    "RV-07": ["GESTOR_TAREAS", "GESTION_CAMBIOS", "HERRAMIENTA_PLANIFICACION"],
    "RV-08": ["GESTOR_TAREAS", "HERRAMIENTA_PLANIFICACION"],
    "RV-09": ["REPO_CODIGO"],
    "RV-10": ["SISTEMA_DOCUMENTAL"],
}

RULE_NAMES: dict[str, str] = {
    "RV-01": "Artefactos existentes",
    "RV-02": "Coherencia IDs",
    "RV-03": "Estado de tareas",
    "RV-04": "Estimación esfuerzo",
    "RV-05": "Documentos existentes",
    "RV-06": "Versión documentos",
    "RV-07": "Release planificada",
    "RV-08": "Coherencia planificación",
    "RV-09": "Referencias código",
    "RV-10": "Informe pruebas",
    "custom_field_check": "Regla personalizada",
}
