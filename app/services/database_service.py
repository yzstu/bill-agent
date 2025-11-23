# app/services/database_service.py
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.database import BillRecord
from app.models.schemas import BillCreate
from app.services.ai_agent import BillRecordModel

logger = logging.getLogger(__name__)


class DatabaseService:
    """异步数据库服务类"""

    def __init__(self):
        self.engine = None
        self.async_session = None
        self._initialized = False

    async def initialize(self):
        """初始化数据库连接池"""
        if self._initialized:
            return

        try:
            mysql_url = f'mysql+aiomysql://{settings.mysql_user}:{settings.mysql_password}@{settings.mysql_host}:3306/{settings.mysql_database}'
            # 创建异步引擎 - 使用连接池
            self.engine = create_async_engine(
                mysql_url,
                echo=settings.debug,  # 调试模式下显示SQL语句
                future=True,
                pool_size=10,  # 连接池大小
                max_overflow=20,  # 最大溢出连接数
                pool_pre_ping=True,  # 连接前ping检测
                pool_recycle=3600,  # 连接回收时间(秒)
            )

            # 创建异步会话工厂
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True
            )

            self._initialized = True
            logger.info("数据库服务初始化成功")

        except Exception as e:
            logger.error(f"数据库服务初始化失败: {e}")
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话的上下文管理器"""
        if not self._initialized:
            await self.initialize()

        session = self.async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库操作失败，已回滚: {e}")
            raise
        finally:
            await session.close()

    async def check_connection(self) -> bool:
        """检查数据库连接是否正常"""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False

    async def create_bill_record(
            self,
            bill_data: BillRecordModel,
            image_path: str,
            ocr_text: str
    ) -> str:
        """创建账单记录"""
        try:
            async with self.get_session() as session:
                # 创建账单记录对象
                db_bill = BillRecord(
                    payment_method=bill_data.payment_method,
                    amount=bill_data.amount,
                    currency="CNY",  # 默认人民币
                    transaction_time=bill_data.transaction_time,
                    product_type=bill_data.product_type,
                    merchant=bill_data.merchant,
                    description=bill_data.description,
                    image_path=image_path,
                    ocr_text=ocr_text,
                    status="completed"
                )

                session.add(db_bill)
                await session.flush()  # 刷新获取ID但不提交
                record_id = db_bill.record_id
                await session.commit()

                logger.info(f"账单记录创建成功，记录ID: {record_id}")
                return record_id

        except Exception as e:
            logger.error(f"创建账单记录失败: {e}")
            raise Exception(f"数据库操作失败: {e}")

    async def get_bill_by_id(self, record_id: str) -> Optional[BillRecord]:
        """根据ID获取账单记录"""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    text("SELECT * FROM bill_records WHERE record_id = :record_id"),
                    {"record_id": record_id}
                )
                bill_data = result.mappings().first()
                return BillRecord(**bill_data) if bill_data else None

        except Exception as e:
            logger.error(f"获取账单记录失败: {e}")
            return None

    async def get_bills_by_time_range(
            self,
            start_time: str,
            end_time: str,
            page: int = 1,
            page_size: int = 20
    ) -> Dict[str, Any]:
        """根据时间范围查询账单记录（分页）"""
        try:
            async with self.get_session() as session:
                # 计算偏移量
                offset = (page - 1) * page_size

                # 查询数据
                result = await session.execute(
                    text("""
                    SELECT * FROM bill_records 
                    WHERE transaction_time BETWEEN :start_time AND :end_time
                    ORDER BY transaction_time DESC
                    LIMIT :limit OFFSET :offset
                    """),
                    {
                        "start_time": start_time,
                        "end_time": end_time,
                        "limit": page_size,
                        "offset": offset
                    }
                )

                bills = [BillRecord(**row) for row in result.mappings().all()]

                # 查询总数
                count_result = await session.execute(
                    text("""
                    SELECT COUNT(*) as total 
                    FROM bill_records 
                    WHERE transaction_time BETWEEN :start_time AND :end_time
                    """),
                    {"start_time": start_time, "end_time": end_time}
                )

                total = count_result.scalar()

                return {
                    "bills": bills,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }

        except Exception as e:
            logger.error(f"查询账单记录失败: {e}")
            return {"bills": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    async def get_bills_by_payment_method(
            self,
            payment_method: str,
            page: int = 1,
            page_size: int = 20
    ) -> Dict[str, Any]:
        """根据支付方式查询账单记录"""
        try:
            async with self.get_session() as session:
                offset = (page - 1) * page_size

                result = await session.execute(
                    text("""
                    SELECT * FROM bill_records 
                    WHERE payment_method = :payment_method
                    ORDER BY transaction_time DESC
                    LIMIT :limit OFFSET :offset
                    """),
                    {
                        "payment_method": payment_method,
                        "limit": page_size,
                        "offset": offset
                    }
                )

                bills = [BillRecord(**row) for row in result.mappings().all()]

                count_result = await session.execute(
                    text("SELECT COUNT(*) as total FROM bill_records WHERE payment_method = :payment_method"),
                    {"payment_method": payment_method}
                )

                total = count_result.scalar()

                return {
                    "bills": bills,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }

        except Exception as e:
            logger.error(f"按支付方式查询账单失败: {e}")
            return {"bills": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    async def get_spending_statistics(
            self,
            start_time: str,
            end_time: str
    ) -> Dict[str, Any]:
        """获取消费统计信息"""
        try:
            async with self.get_session() as session:
                # 按商品类型统计
                type_stats = await session.execute(
                    text("""
                    SELECT product_type, COUNT(*) as count, SUM(amount) as total_amount
                    FROM bill_records 
                    WHERE transaction_time BETWEEN :start_time AND :end_time
                    GROUP BY product_type
                    ORDER BY total_amount DESC
                    """),
                    {"start_time": start_time, "end_time": end_time}
                )

                # 按支付方式统计
                method_stats = await session.execute(
                    text("""
                    SELECT payment_method, COUNT(*) as count, SUM(amount) as total_amount
                    FROM bill_records 
                    WHERE transaction_time BETWEEN :start_time AND :end_time
                    GROUP BY payment_method
                    ORDER BY total_amount DESC
                    """),
                    {"start_time": start_time, "end_time": end_time}
                )

                # 总体统计
                overall_stats = await session.execute(
                    text("""
                    SELECT 
                        COUNT(*) as total_count,
                        SUM(amount) as total_amount,
                        AVG(amount) as average_amount,
                        MAX(amount) as max_amount,
                        MIN(amount) as min_amount
                    FROM bill_records 
                    WHERE transaction_time BETWEEN :start_time AND :end_time
                    """),
                    {"start_time": start_time, "end_time": end_time}
                )

                overall = overall_stats.mappings().first()

                return {
                    "overall": dict(overall) if overall else {},
                    "by_product_type": [dict(row) for row in type_stats.mappings().all()],
                    "by_payment_method": [dict(row) for row in method_stats.mappings().all()],
                    "time_range": {
                        "start_time": start_time,
                        "end_time": end_time
                    }
                }

        except Exception as e:
            logger.error(f"获取消费统计失败: {e}")
            return {
                "overall": {},
                "by_product_type": [],
                "by_payment_method": [],
                "time_range": {"start_time": start_time, "end_time": end_time}
            }

    async def update_bill_status(
            self,
            record_id: str,
            status: str,
            description: Optional[str] = None
    ) -> bool:
        """更新账单状态"""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    text("""
                    UPDATE bill_records 
                    SET status = :status, 
                        description = COALESCE(:description, description),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE record_id = :record_id
                    """),
                    {
                        "record_id": record_id,
                        "status": status,
                        "description": description
                    }
                )

                await session.commit()
                affected_rows = result.rowcount

                if affected_rows > 0:
                    logger.info(f"账单状态更新成功，记录ID: {record_id}, 新状态: {status}")
                    return True
                else:
                    logger.warning(f"未找到要更新的账单记录: {record_id}")
                    return False

        except Exception as e:
            logger.error(f"更新账单状态失败: {e}")
            return False

    # async def delete_bill_record(self, record_id: str) -> bool:
    #     """删除账单记录"""
    #     try:
    #         async_with
    #         self.get_session() as session:
    #         result = await session.execute(
    #             text("DELETE FROM bill_records WHERE record_id = :record_id"),
    #             {"record_id": record_id}
    #         )
    #
    #         await session.commit()
    #         affected_rows = result.rowcount
    #
    #         if affected_rows > 0:
    #             logger.info(f"账单记录删除成功，记录ID: {record_id}")
    #             return True
    #         else:
    #             logger.warning(f"未找到要删除的账单记录: {record_id}")
    #             return False
    #
    # except Exception as e:
    # logger.error(f"删除账单记录失败: {e}")
    # return False


async def close(self):
    """关闭数据库连接池"""
    if self.engine:
        await self.engine.dispose()
        self._initialized = False
        logger.info("数据库连接池已关闭")


# 创建全局数据库服务实例
database_service = DatabaseService()


# 依赖注入函数
async def get_database_service() -> DatabaseService:
    """获取数据库服务的依赖注入函数"""
    await database_service.initialize()
    return database_service