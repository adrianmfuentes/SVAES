from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from .enums import VerdictType

@dataclass
class VerificationResult:
    """Entity representing the result of a verification process for a specific release. Each verification result contains information about 
    the release being verified, the verdict of the verification, the duration of the process, detailed results for each rule applied, 
    and a snapshot of the verification profile used during the process.

    Attributes:
        release_id (uuid.UUID): Identifier of the release that was verified.
        verdict (VerdictType): Overall verdict of the verification process (e.g., 'APROBADO', 'RECHAZADO').
        duration_ms (int): Duration of the verification process in milliseconds.
        rule_results (dict): Detailed results for each rule applied during the verification, keyed by rule identifier.
        profile_snapshot (dict): Snapshot of the verification profile used during the process for historical traceability.
        id (uuid.UUID): Unique identifier for the verification result.
        executed_at (datetime): Timestamp when the verification was executed.
    """
    release_id: uuid.UUID
    verdict: VerdictType
    duration_ms: int
    rule_results: dict = field(default_factory=dict)  # Detalle por regla
    profile_snapshot: dict = field(default_factory=dict) # Trazabilidad histórica
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))