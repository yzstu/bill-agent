from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class BillCreate(BaseModel):
    """账单创建模型"""
    payment_method: str
    amount: float
    transaction_time: datetime
    product_type: str
    merchant: Optional[str] = None
    description: Optional[str] = None
    image_path: Optional[str] = None

    @field_validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('金额必须大于0')
        return v


class BillResponse(BillCreate):
    """账单响应模型"""
    id: int
    record_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalysisRequest(BaseModel):
    """分析请求模型"""
    image_data: bytes
    file_extension: str


class AnalysisResponse(BaseModel):
    """分析响应模型"""
    success: bool
    record_id: Optional[str] = None
    bill_data: Optional[BillResponse] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None