"""Roboflow 식재료 탐지 서비스"""
import base64
import io
from typing import List, Dict, Any
import requests
from PIL import Image
import cv2
import numpy as np

from app.core.config import get_settings

settings = get_settings()


class RoboflowService:
    """Roboflow 객체 탐지 서비스"""
    
    def __init__(self):
        self.api_url = "https://detect.roboflow.com/food-ingredient-for-detection/3"
        self.api_key = "MfrBSqko2aeFsU83n5Od"  # Private API Key
        
    def detect_ingredients(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Roboflow API로 식재료 탐지
        
        Args:
            image_bytes: 이미지 바이트 데이터
            
        Returns:
            탐지된 객체 리스트 (Bounding Box 포함)
            [
                {
                    "class": "carrot",
                    "confidence": 0.95,
                    "x": 100,  # 중심 x
                    "y": 200,  # 중심 y
                    "width": 50,
                    "height": 60
                },
                ...
            ]
        """
        try:
            # 이미지를 base64로 인코딩
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Roboflow API 호출
            response = requests.post(
                f"{self.api_url}?api_key={self.api_key}&confidence=20",
                data=image_base64,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Roboflow API 오류: HTTP {response.status_code}")
                return []
            
            result = response.json()
            predictions = result.get("predictions", [])
            
            print(f"✅ Roboflow 탐지 완료: {len(predictions)}개 객체 발견")
            
            return predictions
            
        except Exception as e:
            print(f"❌ Roboflow 탐지 실패: {e}")
            return []
    
    def crop_image_from_bbox(
        self, 
        image_bytes: bytes, 
        bbox: Dict[str, float]
    ) -> bytes:
        """
        Bounding Box 좌표로 이미지 자르기
        
        Args:
            image_bytes: 원본 이미지 바이트
            bbox: Bounding Box 정보 (x, y, width, height)
            
        Returns:
            잘린 이미지 바이트
        """
        try:
            # PIL Image로 변환
            image = Image.open(io.BytesIO(image_bytes))
            
            # Roboflow는 중심 좌표 + width/height 형식
            x_center = bbox["x"]
            y_center = bbox["y"]
            width = bbox["width"]
            height = bbox["height"]
            
            # 좌상단, 우하단 좌표로 변환
            left = int(x_center - width / 2)
            top = int(y_center - height / 2)
            right = int(x_center + width / 2)
            bottom = int(y_center + height / 2)
            
            # 이미지 범위 내로 제한
            left = max(0, left)
            top = max(0, top)
            right = min(image.width, right)
            bottom = min(image.height, bottom)
            
            # 이미지 자르기
            cropped_image = image.crop((left, top, right, bottom))
            
            # 바이트로 변환
            buffer = io.BytesIO()
            cropped_image.save(buffer, format="JPEG")
            return buffer.getvalue()
            
        except Exception as e:
            print(f"❌ 이미지 크롭 실패: {e}")
            return image_bytes  # 실패시 원본 반환


    def draw_bboxes_on_image(
        self,
        image_bytes: bytes,
        detections: List[Dict[str, Any]]
    ) -> bytes:
        """
        원본 이미지에 Bounding Box를 그립니다 (GPT Vision용)
        
        Args:
            image_bytes: 원본 이미지 바이트
            detections: Roboflow 탐지 결과 리스트
            
        Returns:
            박스가 그려진 이미지 바이트
        """
        try:
            # 이미지를 numpy array로 변환
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                print("❌ 이미지 디코딩 실패")
                return image_bytes
            
            # 각 탐지 결과에 대해 박스 그리기
            for i, det in enumerate(detections):
                class_name = det.get('class', det.get('className', '?'))
                confidence = det.get('confidence', 0)
                x_center = det.get('x', 0)
                y_center = det.get('y', 0)
                box_width = det.get('width', 0)
                box_height = det.get('height', 0)
                
                # 좌상단, 우하단 좌표 계산
                x1 = int(x_center - box_width / 2)
                y1 = int(y_center - box_height / 2)
                x2 = int(x_center + box_width / 2)
                y2 = int(y_center + box_height / 2)
                
                # 박스 그리기 (초록색, 두께 3)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                
                # 라벨 그리기
                label = f"#{i+1}: {class_name} ({confidence:.2f})"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                thickness = 2
                (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
                
                # 배경 사각형
                cv2.rectangle(img, (x1, y1 - text_h - 10), (x1 + text_w + 10, y1), (0, 255, 0), -1)
                
                # 텍스트
                cv2.putText(img, label, (x1 + 5, y1 - 5), font, font_scale, (255, 255, 255), thickness)
            
            # 이미지를 바이트로 변환
            _, buffer = cv2.imencode('.jpg', img)
            print(f"✅ Bounding Box 그리기 완료: {len(detections)}개")
            
            return buffer.tobytes()
            
        except Exception as e:
            print(f"❌ 박스 그리기 실패: {e}")
            return image_bytes


def get_roboflow_service() -> RoboflowService:
    """Roboflow 서비스 싱글톤 인스턴스 반환"""
    return RoboflowService()

