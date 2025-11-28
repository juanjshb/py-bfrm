from pydantic import BaseModel
from typing import Dict, Optional

class TasasCambio(BaseModel):
    rate: Dict[str, float]
    timestamp: Optional[str]
    status: str

class ConversionResultado(BaseModel):
    source_amount: float
    source_currency: str
    target_amount: float
    applied_rate: float
    rate_type: str
    conversion_required: bool
