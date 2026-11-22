from abc import ABC, abstractmethod
from typing import Dict, Any

class IRulesService(ABC):
    @abstractmethod
    async def reload_custom_rules(self) -> Dict[str, Any]:
        pass