from typing import Optional
from pydantic import BaseModel

class MissingPillarQuestionRequest(BaseModel):
    climateProgramID: int
    pillarID: Optional[int] = None