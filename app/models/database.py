# app/models/database.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class BillRecord(Base):
    """账单记录数据模型"""
    __tablename__ = "bill_records"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String(50), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    payment_method = Column(String(50), nullable=False)  # 支付方式
    amount = Column(Float, nullable=False)  # 金额
    currency = Column(String(10), default="CNY")  # 货币类型
    transaction_time = Column(DateTime, nullable=False)  # 交易时间
    product_type = Column(String(100), nullable=False)  # 商品类型
    merchant = Column(String(200))  # 商户名称
    description = Column(Text)  # 交易描述
    image_path = Column(String(500))  # 图片存储路径
    ocr_text = Column(Text)  # OCR识别文本
    status = Column(String(20), default="pending")  # 处理状态
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
