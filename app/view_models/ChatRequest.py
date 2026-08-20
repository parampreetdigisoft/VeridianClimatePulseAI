from pydantic import BaseModel
from typing import Any, List, Optional, Dict

class ChatRequest(BaseModel):
    climateProgramID: int
    questionText: str
    historyText: Optional[str] = None
    pillarID: Optional[int] = None

class ChatGlobalRequest(BaseModel):
    questionText: str
    historyText: Optional[str] = None
    faqid: Optional[int] = None

class ChatProgramRequest(BaseModel):
    climateProgramID: int
    questionText: str
    historyText: Optional[str] = None
    faqid: Optional[int] = None
    pillarID: Optional[int] = None


class ChatCrossComparisionRequest(BaseModel):
    questionText: str
    climateProgramIDs: list[int]
    historyText: Optional[str] = None
    faqid: Optional[int] = None


class ChatProgramExecutiveSlidesRequest(BaseModel):
    climateProgramID: int

class ChatProgramExecutiveSlidesResponse(BaseModel):
    success: bool
    message: str
    result: Any