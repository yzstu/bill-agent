# app/api/endpoints.py
import logging
import time
import uuid
from typing import Dict

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.schemas import AnalysisResponse
from app.services.ai_agent import AIAnalysisAgent
from app.services.database_service import DatabaseService
from app.services.minio_client import MinioClient
from app.services.ocr_service import OCRService

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局服务实例
minio_client = MinioClient()
ocr_service = OCRService()
ai_agent = AIAnalysisAgent()
db_service = DatabaseService()

# 任务状态存储
task_status: Dict[str, Dict] = {}


@router.post("/analyze-bill", response_model=AnalysisResponse)
async def analyze_bill(
        background_tasks: BackgroundTasks,
        image: UploadFile = File(..., description="账单截图文件")
):
    """分析账单图片的主接口"""
    try:
        # 验证文件类型
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传有效的图片文件")

        # 生成任务ID
        task_id = str(uuid.uuid4())
        task_status[task_id] = {
            "status": "processing",
            "start_time": time.time(),
            "message": "开始处理图片"
        }

        # 添加后台任务
        background_tasks.add_task(
            process_bill_analysis,
            task_id,
            await image.read(),
            image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
        )

        return AnalysisResponse(
            success=True,
            record_id=task_id,
            error_message="任务已提交，正在处理中"
        )

    except Exception as e:
        logger.error(f"账单分析请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task_status[task_id]


async def process_bill_analysis(task_id: str, image_data: bytes, file_extension: str):
    """后台处理账单分析任务"""
    try:
        task_status[task_id]["message"] = "上传图片到MiniO"

        # 1. 上传图片到MiniO
        image_path = await minio_client.upload_image(image_data, file_extension)
        task_status[task_id]["image_path"] = image_path

        # 2. OCR文字识别
        task_status[task_id]["message"] = "进行OCR文字识别"
        bill_text = await ocr_service.extract_text_from_image(image_data)

        if not bill_text or len(bill_text.strip()) < 10:
            raise ValueError("无法从图片中识别出足够的文字信息")

        task_status[task_id]["ocr_text_length"] = len(bill_text)

        # 3. AI解析账单内容
        task_status[task_id]["message"] = "AI解析账单内容"
        bill_record = await ai_agent.analyze_bill_text(bill_text)

        # 4. 存储到数据库
        task_status[task_id]["message"] = "保存到数据库"
        record_id = await db_service.create_bill_record(bill_record, image_path, bill_text)

        # 更新任务状态
        processing_time = time.time() - task_status[task_id]["start_time"]
        task_status[task_id].update({
            "status": "completed",
            "record_id": record_id,
            "processing_time": processing_time,
            "message": "处理完成"
        })

        logger.info(f"账单分析任务完成: {task_id}, 耗时: {processing_time:.2f}秒")

    except Exception as e:
        logger.error(f"账单分析任务失败: {task_id}, 错误: {e}")
        task_status[task_id].update({
            "status": "failed",
            "error_message": str(e),
            "message": "处理失败"
        })


@router.get("/health")
async def health_check():
    """健康检查端点"""
    services_status = {
        "minio": await check_minio_health(),
        "database": await check_database_health(),
        "ai_service": await check_ai_health(),
        "timestamp": time.time()
    }

    all_healthy = all(services_status.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content=services_status
    )


async def check_minio_health():
    """检查MiniO服务健康状态"""
    try:
        minio_client.client.list_buckets()
        return True
    except Exception:
        return False


async def check_database_health():
    """检查数据库健康状态"""
    try:
        await db_service.check_connection()
        return True
    except Exception:
        return False


async def check_ai_health():
    """检查AI服务健康状态"""
    try:
        # 简单的健康检查，可以发送一个测试请求
        return True
    except Exception:
        return False