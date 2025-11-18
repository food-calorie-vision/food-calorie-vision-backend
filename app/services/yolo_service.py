"""YOLO 음식 detection 서비스"""
import io
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

from app.core.config import get_settings

settings = get_settings()


class YOLOService:
    """YOLO 음식 detection 서비스"""
    
    def __init__(self):
        self.model: Optional[YOLO] = None
        self._load_model()
    
    def _load_model(self):
        """YOLO 모델 로드"""
        try:
            model_path = settings.vision_model_path or "yolo11n.pt"
            
            # 모델 파일 존재 확인
            if Path(model_path).exists():
                print(f"✅ YOLO 모델 로드 중: {model_path}")
                self.model = YOLO(model_path)
                print(f"✅ YOLO 모델 로드 완료!")
            else:
                print(f"⚠️ YOLO 모델 파일을 찾을 수 없습니다: {model_path}")
                print(f"⚠️ 기본 YOLO 모델(yolo11n.pt)을 다운로드합니다...")
                self.model = YOLO("yolo11n.pt")  # 자동 다운로드
                print(f"✅ YOLO 모델 다운로드 및 로드 완료!")
        except Exception as e:
            print(f"❌ YOLO 모델 로드 실패: {e}")
            self.model = None
    
    def detect_food(self, image_bytes: bytes) -> dict:
        """
        이미지에서 음식 객체 detection
        
        Args:
            image_bytes: 이미지 바이트 데이터
            
        Returns:
            detection 결과 딕셔너리
            {
                "detected_objects": [
                    {
                        "class_name": "pizza",
                        "confidence": 0.87,
                        "bbox": [x1, y1, x2, y2]
                    },
                    ...
                ],
                "image_with_boxes": bytes,  # 바운딩 박스가 그려진 이미지
                "summary": "피자 1개 감지됨"
            }
        """
        if self.model is None:
            raise RuntimeError("YOLO 모델이 로드되지 않았습니다.")
        
        try:
            # 이미지 바이트 -> PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # PIL Image -> numpy array (OpenCV 형식)
            image_np = np.array(image)
            if image_np.shape[-1] == 4:  # RGBA -> RGB
                image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
            elif len(image_np.shape) == 2:  # Grayscale -> RGB
                image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
            
            # YOLO detection 실행
            results = self.model(image_np, conf=0.25)  # confidence threshold 25%
            
            # Detection 결과 파싱
            detected_objects = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # 클래스 이름 가져오기
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    confidence = float(box.conf[0])
                    bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    
                    detected_objects.append({
                        "class_name": class_name,
                        "confidence": confidence,
                        "bbox": bbox
                    })
            
            # 바운딩 박스가 그려진 이미지 생성
            annotated_image = results[0].plot()  # OpenCV 형식 (BGR)
            annotated_image_rgb = cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB)
            
            # numpy array -> PIL Image -> bytes
            annotated_pil = Image.fromarray(annotated_image_rgb)
            img_byte_arr = io.BytesIO()
            annotated_pil.save(img_byte_arr, format='JPEG')
            annotated_image_bytes = img_byte_arr.getvalue()
            
            # 요약 생성
            if detected_objects:
                object_counts = {}
                for obj in detected_objects:
                    name = obj["class_name"]
                    object_counts[name] = object_counts.get(name, 0) + 1
                
                summary_parts = [f"{name} {count}개" for name, count in object_counts.items()]
                summary = ", ".join(summary_parts) + " 감지됨"
            else:
                summary = "음식이 감지되지 않았습니다."
            
            return {
                "detected_objects": detected_objects,
                "image_with_boxes": annotated_image_bytes,
                "summary": summary,
                "total_objects": len(detected_objects)
            }
            
        except Exception as e:
            print(f"❌ YOLO detection 실패: {e}")
            raise RuntimeError(f"음식 detection 중 오류 발생: {str(e)}")


# 싱글톤 인스턴스
_yolo_service_instance: Optional[YOLOService] = None


def get_yolo_service() -> YOLOService:
    """YOLO 서비스 싱글톤 인스턴스 반환"""
    global _yolo_service_instance
    if _yolo_service_instance is None:
        _yolo_service_instance = YOLOService()
    return _yolo_service_instance

