from dataclasses import dataclass, field

@dataclass
class VerificationRule:
    rule_id: str  # RV-01 .. RV-10
    enabled: bool = True
    config: dict = field(default_factory=dict)