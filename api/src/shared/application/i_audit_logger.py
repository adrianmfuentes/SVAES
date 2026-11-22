from typing import Protocol

from shared.domain.audit import AuditEntry


class IAuditLogger(Protocol):
    def log(self, entry: AuditEntry) -> None: ...
