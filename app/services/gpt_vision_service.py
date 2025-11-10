"""GPT-Vision 음식 분석 서비스"""
import base64
import io
from typing import Optional

from openai import OpenAI
from PIL import Image

from app.core.config import get_settings

settings = get_settings()


class GPTVisionService:
    """GPT-Vision 음식 분석 서비스"""
    
    def __init__(self):
        self.client: Optional[OpenAI] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """OpenAI 클라이언트 초기화"""
        if settings.openai_api_key:
            try:
                self.client = OpenAI(api_key=settings.openai_api_key)
                print("✅ OpenAI GPT-Vision 클라이언트 초기화 완료!")
            except Exception as e:
                print(f"❌ OpenAI 클라이언트 초기화 실패: {e}")
                self.client = None
        else:
            print("⚠️ OPENAI_API_KEY가 설정되지 않았습니다.")
            self.client = None
    
    def _image_to_base64(self, image_bytes: bytes) -> str:
        """이미지 바이트를 base64 문자열로 변환"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def analyze_food_with_detection(
        self,
        image_bytes: bytes,
        yolo_detection_result: dict
    ) -> dict:
        """
        YOLO detection 결과와 함께 GPT-Vision으로 음식 분석
        
        Args:
            image_bytes: 원본 이미지 바이트 데이터
            yolo_detection_result: YOLO detection 결과
                {
                    "detected_objects": [...],
                    "summary": "피자 1개 감지됨",
                    "total_objects": 1
                }
        
        Returns:
            GPT-Vision 분석 결과
            {
                "food_name": "페퍼로니 피자",
                "description": "...",
                "calories": 800,
                "nutrients": {
                    "protein": 30.0,
                    "carbs": 80.0,
                    "fat": 40.0,
                    "sodium": 1500.0,
                    "fiber": 3.0
                },
                "portion_size": "1조각 (약 150g)",
                "health_score": 65,
                "suggestions": [
                    "...",
                    "..."
                ]
            }
        """
        if self.client is None:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다. OPENAI_API_KEY를 확인하세요.")
        
        try:
            # 이미지를 base64로 인코딩
            base64_image = self._image_to_base64(image_bytes)
            
            # YOLO detection 결과 요약
            detected_objects_summary = yolo_detection_result.get("summary", "객체 감지 안됨")
            detected_objects_list = yolo_detection_result.get("detected_objects", [])
            
            # GPT-Vision 프롬프트 구성
            prompt = self._build_analysis_prompt(detected_objects_summary, detected_objects_list)
            
            # GPT-Vision API 호출
            response = self.client.chat.completions.create(
                model="gpt-4o",  # 또는 "gpt-4-vision-preview"
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            # 응답 파싱
            gpt_response = response.choices[0].message.content
            
            # 디버깅: GPT 원본 응답 출력
            print("=" * 80)
            print("🤖 GPT-Vision 원본 응답:")
            print(gpt_response)
            print("=" * 80)
            
            # GPT 응답을 구조화된 데이터로 변환
            analysis_result = self._parse_gpt_response(gpt_response)
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ GPT-Vision 분석 실패: {e}")
            raise RuntimeError(f"GPT-Vision 분석 중 오류 발생: {str(e)}")
    
    def _build_analysis_prompt(self, yolo_summary: str, detected_objects: list) -> str:
        """GPT-Vision 분석 프롬프트 생성 (음식명 + 주요 재료 추출)"""
        
        objects_detail = ""
        if detected_objects:
            objects_detail = "\n\nYOLO가 감지한 객체 상세:\n"
            for i, obj in enumerate(detected_objects, 1):
                objects_detail += f"{i}. {obj['class_name']} (신뢰도: {obj['confidence']:.2%})\n"
        
        prompt = f"""당신은 영양 전문가입니다. 이미지 속 음식을 분석하여 다음 정보를 제공해주세요.

**YOLO 모델 detection 결과:**
{yolo_summary}{objects_detail}

위 detection 결과를 참고하여 이미지를 분석하고, 다음 형식으로 **정확하게** 답변해주세요:

---
**가장 가능성 높은 음식 (신뢰도 순위 1~4위)**

[후보1]
음식명: [한국어 음식 이름]
신뢰도: [0-100%, 숫자만]
설명: [음식에 대한 간단한 설명 1문장]

[후보2]
음식명: [한국어 음식 이름]
신뢰도: [0-100%, 숫자만]
설명: [음식에 대한 간단한 설명 1문장]

[후보3]
음식명: [한국어 음식 이름]
신뢰도: [0-100%, 숫자만]
설명: [음식에 대한 간단한 설명 1문장]

[후보4]
음식명: [한국어 음식 이름]
신뢰도: [0-100%, 숫자만]
설명: [음식에 대한 간단한 설명 1문장]

**선택된 음식 (후보1) 상세 정보:**
주요재료1: [첫 번째 주요 재료]
주요재료2: [두 번째 주요 재료]
주요재료3: [세 번째 주요 재료]
주요재료4: [네 번째 주요 재료 (선택)]
1회 제공량: [예: 1조각 (약 150g)]
건강점수: [0-100점, 숫자만]
건강 제안사항:
- [제안 1]
- [제안 2]
- [제안 3]
---

**중요:**
1. 위 형식을 정확히 따라주세요.
2. 후보 음식은 신뢰도가 높은 순서대로 4개를 제시하세요.
3. 각 후보의 신뢰도는 퍼센트(%) 단위로, 합이 100이 될 필요는 없습니다.
4. 음식명은 구체적으로 작성하세요 (예: "피자" → "마르게리타 피자", "밥" → "흰쌀밥")
5. 주요재료는 후보1 음식에 들어간 핵심 재료 3-4개를 작성하세요.
   - 예: 피자 → 밀가루, 토마토소스, 치즈, 페퍼로니
   - 예: 김치찌개 → 김치, 돼지고기, 두부, 파
6. 건강점수는 영양 균형, 칼로리, 나트륨 등을 고려하여 0-100점으로 평가하세요.
7. 건강 제안사항은 3개를 작성하세요.
8. 1회 제공량은 이미지에 보이는 양을 기준으로 추정하세요.
"""
        return prompt
    
    def _parse_gpt_response(self, gpt_response: str) -> dict:
        """GPT 응답을 구조화된 데이터로 파싱 (여러 후보 + 재료 추출)"""
        try:
            lines = gpt_response.strip().split('\n')
            result = {
                "candidates": [],  # 후보 음식 리스트
                "food_name": "",
                "description": "",
                "ingredients": [],  # 주요 재료 리스트
                "portion_size": "",
                "health_score": 0,
                "suggestions": []
            }
            
            current_section = None
            current_candidate = None
            
            for line in lines:
                line = line.strip()
                if not line or line == "---":
                    continue
                
                # 후보 섹션 시작
                if line.startswith("[후보"):
                    if current_candidate:
                        result["candidates"].append(current_candidate)
                    current_candidate = {
                        "food_name": "",
                        "confidence": 0.0,
                        "description": ""
                    }
                    current_section = "candidate"
                    continue
                
                # 선택된 음식 상세 정보 섹션
                if "선택된 음식" in line or "상세 정보" in line:
                    if current_candidate:
                        result["candidates"].append(current_candidate)
                        current_candidate = None
                    current_section = "selected"
                    continue
                
                # 키-값 파싱
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 후보 정보 파싱
                    if current_section == "candidate" and current_candidate:
                        if key == "음식명":
                            current_candidate["food_name"] = value
                        elif key == "신뢰도":
                            conf_str = value.replace("%", "").strip()
                            try:
                                current_candidate["confidence"] = float(conf_str) / 100.0
                            except:
                                current_candidate["confidence"] = 0.0
                        elif key == "설명":
                            current_candidate["description"] = value
                    
                    # 선택된 음식 정보 파싱 (레거시 호환)
                    elif current_section == "selected" or current_section is None:
                        if key == "음식명":
                            result["food_name"] = value
                        elif key == "설명" and not result["description"]:
                            result["description"] = value
                        elif key.startswith("주요재료"):
                            if value and value != "[선택]":
                                result["ingredients"].append(value)
                        elif key == "1회 제공량":
                            result["portion_size"] = value
                        elif key == "건강점수":
                            result["health_score"] = int(float(value.replace("점", "").strip()))
                        elif key == "건강 제안사항":
                            current_section = "suggestions"
                
                # 제안사항 파싱
                elif line.startswith("-") and current_section == "suggestions":
                    suggestion = line[1:].strip()
                    if suggestion:
                        result["suggestions"].append(suggestion)
            
            # 마지막 후보 추가
            if current_candidate:
                result["candidates"].append(current_candidate)
            
            # 후보1의 정보를 메인 정보로 설정 (food_name이 비어있을 경우)
            if not result["food_name"] and result["candidates"]:
                result["food_name"] = result["candidates"][0]["food_name"]
                if not result["description"]:
                    result["description"] = result["candidates"][0]["description"]
            
            # 기본값 설정 (파싱 실패 시)
            if not result["food_name"]:
                result["food_name"] = "알 수 없는 음식"
            if not result["description"]:
                result["description"] = "음식 정보를 분석할 수 없습니다."
            if not result["ingredients"]:
                result["ingredients"] = ["재료 정보 없음"]
            if not result["suggestions"]:
                result["suggestions"] = ["균형 잡힌 식단을 유지하세요."]
            
            print(f"✅ GPT 파싱 완료: {len(result['candidates'])}개 후보, 선택: {result['food_name']}")
            
            return result
            
        except Exception as e:
            print(f"⚠️ GPT 응답 파싱 실패: {e}")
            print(f"원본 응답:\n{gpt_response}")
            
            # 파싱 실패 시 기본값 반환
            return {
                "candidates": [],
                "food_name": "분석 실패",
                "description": "음식 정보를 파싱할 수 없습니다.",
                "ingredients": ["재료 정보 없음"],
                "portion_size": "알 수 없음",
                "health_score": 0,
                "suggestions": ["음식 정보를 다시 분석해주세요."],
                "raw_response": gpt_response  # 디버깅용
            }


# 싱글톤 인스턴스
_gpt_vision_service_instance: Optional[GPTVisionService] = None


def get_gpt_vision_service() -> GPTVisionService:
    """GPT-Vision 서비스 싱글톤 인스턴스 반환"""
    global _gpt_vision_service_instance
    if _gpt_vision_service_instance is None:
        _gpt_vision_service_instance = GPTVisionService()
    return _gpt_vision_service_instance

