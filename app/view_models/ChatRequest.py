from pydantic import BaseModel
from typing import Any, List, Optional, Dict

class ChatRequest(BaseModel):
    programID: int
    questionText: str
    historyText: Optional[str] = None
    pillarID: Optional[int] = None

class ChatGlobalRequest(BaseModel):
    questionText: str
    historyText: Optional[str] = None
    faqid: Optional[int] = None

class ChatCountryRequest(BaseModel):
    programID: int
    questionText: str
    historyText: Optional[str] = None
    faqid: Optional[int] = None
    pillarID: Optional[int] = None


class ChatCrossComparisionRequest(BaseModel):
    questionText: str
    programIDs: list[int]
    historyText: Optional[str] = None
    faqid: Optional[int] = None


class ChatCountryExecutiveSlidesRequest(BaseModel):
    programId: int

class ChatCountryExecutiveSlidesResponse(BaseModel):
    success: bool
    message: str
    result: Any