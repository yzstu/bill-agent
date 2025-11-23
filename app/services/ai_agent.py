# app/services/ai_agent.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class BillRecordModel(BaseModel):
    """账单数据模型（用于AI解析）"""
    payment_method: str = Field(description="支付方式：支付宝、微信支付、华为支付等")
    amount: float = Field(description="交易金额，数字格式")
    transaction_time: str = Field(description="交易时间，YYYY-MM-DD HH:MM:SS格式")
    product_type: str = Field(description="商品类型：餐饮、购物、交通、娱乐等")
    merchant: Optional[str] = Field(None, description="商户名称")
    description: Optional[str] = Field(None, description="交易描述")


class AIAnalysisAgent:
    """增强的AI解析服务"""

    def __init__(self):
        try:
            # 初始化DeepSeek模型
            self.llm = ChatOpenAI(
                model=settings.siliconflow_model_deepseek_v3,
                api_key=settings.siliconflow_api_key,
                base_url=settings.siliconflow_base_url,
                temperature=0.1
            )

            # 创建JSON解析器
            self.parser = JsonOutputParser(pydantic_object=BillRecordModel)

            # 构建增强的Prompt模板
            self.prompt = ChatPromptTemplate.from_template("""""
你是一个专业的账单分析AI助手。请从以下账单文本中提取关键信息，并以JSON格式返回。

账单文本内容：
{bill_text}

提取字段说明：
- payment_method: 支付方式（支付宝、微信支付、华为支付、云闪付等）
- amount: 交易金额（纯数字，如18.50）
- transaction_time: 交易时间（标准格式：YYYY-MM-DD HH:MM:SS）
- product_type: 商品类型（餐饮、购物、交通、娱乐、医疗、教育、生活缴费等）
- merchant: 商户名称（如：星巴克、美团、淘宝等）
- description: 交易描述（可选）

请按照以下步骤进行分析：
1. 识别支付平台特征关键词
2. 提取金额数字和货币单位，统一转换为数字格式
3. 分析时间信息并标准化为YYYY-MM-DD HH:MM:SS格式
4. 根据商品描述智能分类商品类型
5. 提取商户名称信息
6. 验证数据逻辑合理性

思考过程要详细分析文本中的每个相关信息。

{format_instructions}
""")

            # 创建处理链
            self.chain = self.prompt | self.llm | self.parser
            logger.info("AI解析服务初始化成功")

        except Exception as e:
            logger.error(f"AI解析服务初始化失败: {e}")
            raise

    async def analyze_bill_text(self, bill_text: str) -> BillRecordModel:
        """分析账单文本并返回结构化数据"""
        try:
            if not bill_text or len(bill_text.strip()) < 10:
                raise ValueError("账单文本内容过短，无法分析")

            # 执行处理链
            result = await self.chain.ainvoke({
                "bill_text": bill_text,
                "format_instructions": self.parser.get_format_instructions()
            })

            logger.info("AI分析完成")
            return BillRecordModel(**result)

        except Exception as e:
            logger.error(f"账单分析失败: {e}")
            raise Exception(f"AI账单分析失败: {e}")