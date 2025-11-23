# app/services/minio_client.py
from minio import Minio
from minio.error import S3Error
import uuid
import io
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class MinioClient:
    """增强的MiniO客户端"""

    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False
        )
        self.bucket_name = settings.minio_bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"创建存储桶: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"存储桶创建失败: {e}")
            raise

    async def upload_image(self, image_data: bytes, file_extension: str) -> str:
        """上传图片到MiniO"""
        try:
            object_name = f"bill_images/{uuid.uuid4()}.{file_extension}"

            self.client.put_object(
                self.bucket_name,
                object_name,
                io.BytesIO(image_data),
                length=len(image_data),
                content_type=f"image/{file_extension}"
            )

            logger.info(f"图片上传成功: {object_name}")
            return object_name

        except S3Error as e:
            logger.error(f"图片上传失败: {e}")
            raise Exception(f"图片上传失败: {e}")

    async def get_image_url(self, object_name: str) -> str:
        """获取图片访问URL"""
        try:
            return self.client.presigned_get_object(
                self.bucket_name,
                object_name
            )
        except S3Error as e:
            logger.error(f"生成图片URL失败: {e}")
            raise