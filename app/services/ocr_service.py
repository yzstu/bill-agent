# app/services/ocr_service.py
import paddleocr
import cv2
import numpy as np
from PIL import Image
import io
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def _reconstruct_text(text_blocks):
    """根据位置信息重构文本顺序"""
    if not text_blocks:
        return ""

    try:
        # 按Y坐标排序（从上到下）
        text_blocks.sort(key=lambda x: min(point[1] for point in x['position']))

        # 分组并排序
        lines = []
        current_line = []
        y_threshold = 20  # 行高阈值

        for block in text_blocks:
            if not current_line:
                current_line.append(block)
            else:
                current_y = min(point[1] for point in block['position'])
                last_y = min(point[1] for point in current_line[-1]['position'])

                if abs(current_y - last_y) <= y_threshold:
                    current_line.append(block)
                else:
                    # 按X坐标排序当前行（从左到右）
                    current_line.sort(key=lambda x: min(point[0] for point in x['position']))
                    lines.append(current_line)
                    current_line = [block]

        if current_line:
            current_line.sort(key=lambda x: min(point[0] for point in x['position']))
            lines.append(current_line)

        # 合并文本
        result_text = ""
        for line in lines:
            line_text = " ".join([block['text'] for block in line])
            result_text += line_text + "\n"

        return result_text.strip()
    except Exception as e:
        logger.error(f"文本重构失败: {e}")
        # 如果重构失败，返回原始文本
        return " ".join([block['text'] for block in text_blocks])


class OCRService:
    """增强的OCR服务"""

    def __init__(self):
        try:
            # 修复初始化参数
            self.ocr = paddleocr.PaddleOCR(
                use_angle_cls=False,
                lang='ch',
                enable_mkldnn=True
            )
            logger.info("OCR服务初始化成功")
        except Exception as e:
            logger.error(f"OCR服务初始化失败: {e}")
            # 备用初始化
            self.ocr = self._fallback_init()

    def _optimize_image_for_ocr(self, image_bytes: bytes, max_size: int = 1200) -> np.ndarray:
        """
        优化图片二进制数据以减少内存使用

        Args:
            image_bytes: 图片的二进制数据
            max_size: 最大尺寸限制

        Returns:
            numpy.ndarray: 优化后的图片数组
        """
        try:
            # 将二进制数据转换为numpy数组[7](@ref)
            np_arr = np.frombuffer(image_bytes, dtype=np.uint8)

            # 解码图片[7](@ref)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is None:
                raise ValueError("无法解码图片二进制数据")

            # 获取原始尺寸
            h, w = img.shape[:2]

            # 如果图片太大，进行缩放
            if max(h, w) > max_size:
                scale = max_size / max(h, w)
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # 转为灰度图（可选，根据实际情况）
            # if len(img.shape) == 3:  # 如果是彩色图
            #     img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            return img

        except Exception as e:
            logger.error(f"图片优化失败: {e}")
            raise

    def _fallback_init(self):
        """备用初始化方法"""
        try:
            # 最简单的初始化
            return paddleocr.PaddleOCR()
        except:
            try:
                # 只设置语言
                return paddleocr.PaddleOCR(lang='ch')
            except Exception as e:
                logger.error(f"备用初始化也失败: {e}")
                raise

    async def extract_text_from_image(self, image_data: bytes) -> str:
        """从图片中提取文本"""
        try:
            # 优化图片
            optimized_img = self._optimize_image_for_ocr(image_bytes=image_data, max_size=1200)

            # OCR识别 - 使用更安全的方式
            result = self.ocr.predict(optimized_img)

            if not result or not result[0]:
                logger.warning("未识别到文本内容")
                return ""

            # 提取和重构文本
            text_blocks = []
            if result:
                for item in result:
                    for text, score, poly in zip(item['rec_texts'], item['rec_scores'], item['rec_scores']):
                        if score > 0.5:  # 置信度阈值
                            text_blocks.append({
                                'text': text,
                                'score': score,
                                'position': poly
                            })

            # 按位置排序文本
            sorted_text = _reconstruct_text(text_blocks)
            logger.info(f"OCR识别成功，文本长度: {len(sorted_text)}")
            return sorted_text

        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            return f"图片文字识别失败: {e}"

