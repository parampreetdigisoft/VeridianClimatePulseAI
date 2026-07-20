from typing import Optional
from pydantic import BaseModel

class MissingPillarQuestionRequest(BaseModel):
    programID: int
    pillarID: Optional[int] = None