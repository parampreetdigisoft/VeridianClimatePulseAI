from pydantic import BaseModel
from typing import List, Optional, Dict

class ImmediateSituationRequest(BaseModel):
    program_id: int
    programName: str
    continent: str
