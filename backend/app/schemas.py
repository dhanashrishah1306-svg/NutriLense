from pydantic import BaseModel, Field
from typing import Any, Literal

class Profile(BaseModel):
    diet: Literal['vegetarian','vegan','jain','none'] = 'none'
    restrictions: list[str] = Field(default_factory=list)
    custom_restrictions: list[str] = Field(default_factory=list)
    low_sugar: bool = False
    low_sodium: bool = False
    no_added_sugar: bool = False

class AnalyzeRequest(BaseModel):
    ocr_text: str = ''
    corrected_text: str | None = None
    profile: Profile = Field(default_factory=Profile)
    product_code: str | None = None
    classification: dict[str, Any] | None = None

class OCRCorrection(BaseModel):
    text: str = ''
