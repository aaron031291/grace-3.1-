import yaml
import logging
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

logger = logging.getLogger("grace_charter")

class PillarConfig(BaseModel):
    name: str
    description: str
    obligations: List[str]

class ClauseConfig(BaseModel):
    id: str
    text: str

class OKRConfig(BaseModel):
    id: str
    description: str

class Constitution(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: str
    pillars: List[PillarConfig]
    clauses: List[ClauseConfig]
    okrs: List[OKRConfig]

class GraceCharter:
    """
    Loads and enforces the rules from the grace_constitution.yaml.
    Used by the Governance Gate and Unified Logic Hub.
    """
    _constitution: Optional[Constitution] = None
    
    @classmethod
    def load_constitution(cls, override_path: Optional[str] = None) -> Constitution:
        if cls._constitution is not None and override_path is None:
            return cls._constitution
            
        default_path = Path(__file__).parent.parent.parent / "config" / "grace_constitution.yaml"
        path = Path(override_path) if override_path else default_path
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            cls._constitution = Constitution(**data)
            logger.info(f"Loaded Grace Constitution v{cls._constitution.version} with {len(cls._constitution.pillars)} pillars.")
            return cls._constitution
        except Exception as e:
            logger.error(f"Failed to load Grace Constitution from {path}: {e}")
            raise

    @classmethod
    def get_constitution(cls) -> Constitution:
        if cls._constitution is None:
            return cls.load_constitution()
        return cls._constitution

    @classmethod
    def get_pillar(cls, name: str) -> Optional[PillarConfig]:
        constitution = cls.get_constitution()
        for pillar in constitution.pillars:
            if pillar.name == name:
                return pillar
        return None

    @classmethod
    def is_risk_acceptable(cls, risk_score: float) -> bool:
        """
        Helper method checking Clause 4: 
        Actions with risk score > 0.7 must escalate and require explicit approval.
        Reads the threshold dynamically from the actual Constitution text.
        """
        limit = 0.7
        constitution = cls.get_constitution()
        for clause in constitution.clauses:
            if clause.id == "clause_4_approval":
                import re
                match = re.search(r'>\s*([0-9.]+)', clause.text)
                if match:
                    limit = float(match.group(1))
                break
        return risk_score <= limit

    @classmethod
    def validate_kernel_boot(cls, kernel_name: str, has_handshake: bool) -> bool:
        """
        Validates Clause 2: Handshake pipeline requirements.
        Ensures `guardian.signal_kernel_boot()` execution.
        """
        if not has_handshake:
            logger.warning(f"Kernel '{kernel_name}' failed boot validation: missing required handshake.")
            return False
            
        logger.info(f"Kernel '{kernel_name}' successfully passed Handshake Validation.")
        return True
