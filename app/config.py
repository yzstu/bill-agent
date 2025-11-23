import os
from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    # MiniO配置
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "qOna5NMgB6sCeDXp"
    minio_secret_key: str = "82jQy1nPFA0k7kiwUMGeJBpAidYFT5ey"
    minio_bucket: str = "bill-images"

    # MySQL配置
    mysql_host: str = "192.168.100.1"
    mysql_database: str = "yzstu_base"
    mysql_user: str = "yzstu"
    mysql_password: str = ""

    # 轨迹流动API配置[10](@ref)
    siliconflow_api_key: str = "sk-"
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_model_deepseek_v3: str = "deepseek-ai/DeepSeek-V3"

    # 应用配置
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # OCR配置
    ocr_language: str = "ch"
    ocr_use_angle_cls: bool = False

    # 异步任务配置
    max_workers: int = 4
    task_timeout: int = 300

    class Config:
        env_file = ".env"


settings = Settings()