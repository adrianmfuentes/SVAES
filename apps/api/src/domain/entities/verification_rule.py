from dataclasses import dataclass, field

@dataclass
class VerificationRule:
    """Entity representing a verification rule within the system. A verification rule defines the criteria and logic for evaluating a specific 
    aspect of a release during the verification process.

    Attributes:
        rule_id (str): Unique identifier for the verification rule (e.g., 'RV-01', 'RV-02').
        enabled (bool): Flag indicating whether the rule is currently enabled or disabled.
        config (dict): Configuration parameters for the rule, allowing for customization of the rule's behavior during verification.    
    """
    rule_id: str  # RV-01 .. RV-10
    enabled: bool = True
    config: dict = field(default_factory=dict)