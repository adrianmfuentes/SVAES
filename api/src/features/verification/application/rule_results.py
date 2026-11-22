import uuid

from shared.domain.enums import SeverityType, rule_severity_to_string, severity_to_rule_severity
from features.verification.domain.rule_names import RULE_NAMES, RULE_DEFAULT_ARTIFACT_TYPES, RULE_CONNECTOR_TYPES, RULE_CONNECTOR_TYPES_MODE


RULE_OK_EVIDENCE: dict[str, str] = {
    "RV-01": "rule_evidence.ok.RV-01",
    "RV-02": "rule_evidence.ok.RV-02",
    "RV-03": "rule_evidence.ok.RV-03",
    "RV-04": "rule_evidence.ok.RV-04",
    "RV-05": "rule_evidence.ok.RV-05",
    "RV-06": "rule_evidence.ok.RV-06",
    "RV-07": "rule_evidence.ok.RV-07",
    "RV-08": "rule_evidence.ok.RV-08",
    "RV-09": "rule_evidence.ok.RV-09",
    "RV-10": "rule_evidence.ok.RV-10",
    "custom_field_check": "rule_evidence.ok.custom_field_check",
}


def _map_severity_to_engine(severity: SeverityType) -> str:
    return rule_severity_to_string(severity_to_rule_severity(severity))


def _get_connector_types_fallback(
    rid: str, connector_type_map: dict[str, str]
) -> str:
    required_types = RULE_CONNECTOR_TYPES.get(rid, [])
    if not required_types:
        return ""
    mode = RULE_CONNECTOR_TYPES_MODE.get(rid, "ALL")
    names = [connector_type_map[t] for t in required_types if t in connector_type_map]
    satisfied = bool(names) if mode == "ANY" else len(names) == len(required_types)
    if not satisfied:
        return ""
    # De-duplicate while preserving order (a single connector may cover multiple required types)
    return " + ".join(dict.fromkeys(names))


def _get_artifact_fetch_error_connector(
    rule_result: dict, connector_names: dict
) -> str:
    ciid_str = rule_result.get("connector_instance_id", "")
    if ciid_str:
        try:
            return connector_names.get(uuid.UUID(ciid_str), "")
        except (ValueError, KeyError):
            return ""
    return ""


def _get_artifact_type_fallback(
    rid: str, rule_lookup: dict, artifact_type_connector: dict[str, str]
) -> str:
    profile_rule = rule_lookup.get(rid)
    params = profile_rule.params if profile_rule else {}
    artifact_type = params.get("artifact_type") or RULE_DEFAULT_ARTIFACT_TYPES.get(rid)
    if artifact_type:
        return artifact_type_connector.get(artifact_type, "")
    return ""


def _get_connector_for_rule(
    rid: str,
    rule_result: dict,
    rule_lookup: dict,
    connector_names: dict,
    artifact_type_connector: dict[str, str] | None = None,
    connector_type_map: dict[str, str] | None = None,
) -> str:
    if rid == "artifact_fetch_error":
        return _get_artifact_fetch_error_connector(rule_result, connector_names)

    profile_rule = rule_lookup.get(rid)
    if profile_rule and profile_rule.connector_instance_id:
        name = connector_names.get(profile_rule.connector_instance_id, "")
        if name:
            return name

    # Rules requiring more than one connector type (e.g. RV-02, RV-07, RV-08) cannot be
    # resolved through a single default artifact type: check the connector types actually
    # present among the release's artifacts instead.
    if len(RULE_CONNECTOR_TYPES.get(rid, [])) > 1 and connector_type_map is not None:
        return _get_connector_types_fallback(rid, connector_type_map)

    if artifact_type_connector:
        return _get_artifact_type_fallback(rid, rule_lookup, artifact_type_connector)

    return ""


def _recompute_verdict(rule_results: list, active_rules: list) -> str:
    """Recompute the verdict after `_enrich_rule_results` may have downgraded some
    rules from OK/ERROR to NO_EVALUADA (e.g. a rule with no linked artifact/connector).
    The engine's original verdict was computed from the pre-downgrade statuses, so a
    rule that flips to NO_EVALUADA must stop counting towards NO_VALIDA/CON_ADVERTENCIAS
    - otherwise the verdict can end up NO_VALIDA while every visible rule is green or gray.
    Matches rule_results to active_rules positionally (same order the engine received
    them in _build_rules_data), since a profile can repeat the same rule template with
    different severities.
    """
    has_mandatory_error = False
    has_optional_warning = False
    for rule_result, rule in zip(rule_results, active_rules):
        status = rule_result.get("status")
        severity = _map_severity_to_engine(rule.severity)
        if status == "ERROR" and severity == "OBLIGATORIA":
            has_mandatory_error = True
        elif status == "ERROR" and severity == "OPCIONAL":
            has_optional_warning = True
        elif status == "WARNING" and severity == "OPCIONAL":
            has_optional_warning = True

    if has_mandatory_error:
        return "NO_VALIDA"
    if has_optional_warning:
        return "CON_ADVERTENCIAS"
    return "VALIDA"


def _enrich_rule_results(
    result_data: dict,
    rule_lookup: dict,
    connector_names: dict,
    artifact_type_connector: dict[str, str] | None = None,
    connector_type_map: dict[str, str] | None = None,
) -> None:
    for rule_result in result_data.get("rule_results", []):
        rid = rule_result.get("rule_id", "")
        rule_result["rule_name"] = RULE_NAMES.get(rid, rid)

        if rid == "RV-01":
            # RV-01 checks artifact existence — no connector involved; always show dash
            rule_result["connector"] = "-"
        else:
            connector = _get_connector_for_rule(
                rid, rule_result, rule_lookup, connector_names, artifact_type_connector, connector_type_map
            )
            rule_result["connector"] = connector
            # A rule with no linked artifact cannot be OK or ERROR: mark not evaluated
            if (not connector
                    and rule_result.get("status") in ("OK", "ERROR")
                    and rid != "artifact_fetch_error"):
                rule_result["status"] = "NO_EVALUADA"
                rule_result["message"] = "rule_evidence.no_connector"
                rule_result["message_params"] = None

        rule_result["evidence"] = rule_result.get("message", "")
        rule_result["evidence_params"] = rule_result.get("message_params")
        if not rule_result["evidence"] and rule_result.get("status") == "OK":
            rule_result["evidence"] = RULE_OK_EVIDENCE.get(rid, "rule_evidence.ok.default")
            rule_result["evidence_params"] = None
