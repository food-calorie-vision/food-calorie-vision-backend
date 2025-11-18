"""GPT-Vision 음식 분석 서비스"""
import base64
import io
from typing import Optional, List

from openai import OpenAI
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.food_nutrients_service import get_all_food_classes, get_foods_by_class
from app.db.models_food_nutrients import FoodNutrient

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
주요재료1: [첫 번째 주요 재료]
주요재료2: [두 번째 주요 재료]
주요재료3: [세 번째 주요 재료]
주요재료4: [네 번째 주요 재료 (선택)]

[후보2]
음식명: [한국어 음식 이름]
신뢰도: [0-100%, 숫자만]
설명: [음식에 대한 간단한 설명 1문장]
주요재료1: [첫 번째 주요 재료]
주요재료2: [두 번째 주요 재료]
주요재료3: [세 번째 주요 재료]
주요재료4: [네 번째 주요 재료 (선택)]

[후보3]
음식명: [한국어 음식 이름]
신뢰도: [0-100%, 숫자만]
설명: [음식에 대한 간단한 설명 1문장]
주요재료1: [첫 번째 주요 재료]
주요재료2: [두 번째 주요 재료]
주요재료3: [세 번째 주요 재료]
주요재료4: [네 번째 주요 재료 (선택)]

[후보4]
음식명: [한국어 음식 이름]
신뢰도: [0-100%, 숫자만]
설명: [음식에 대한 간단한 설명 1문장]
주요재료1: [첫 번째 주요 재료]
주요재료2: [두 번째 주요 재료]
주요재료3: [세 번째 주요 재료]
주요재료4: [네 번째 주요 재료 (선택)]

**선택된 음식 (후보1) 상세 정보:**
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
5. **각 후보마다** 주요재료 3-4개를 이미지 분석 결과를 기반으로 작성하세요.
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
                        "description": "",
                        "ingredients": []  # 후보별 재료
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
                        elif key.startswith("주요재료"):
                            # 후보의 재료도 추출
                            if value and value.strip() and value.strip() != "-" and value != "[선택]":
                                current_candidate["ingredients"].append(value.strip())
                    
                    # 선택된 음식 정보 파싱 (레거시 호환)
                    elif current_section == "selected" or current_section is None:
                        if key == "음식명":
                            result["food_name"] = value
                        elif key == "설명" and not result["description"]:
                            result["description"] = value
                        elif key.startswith("주요재료"):
                            # 빈 값, "-", "[선택]" 제외
                            if value and value.strip() and value.strip() != "-" and value != "[선택]":
                                result["ingredients"].append(value.strip())
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
    
    async def analyze_food_with_db_guidance(
        self,
        image_bytes: bytes,
        yolo_detection_result: dict,
        session: AsyncSession
    ) -> dict:
        """
        2단계 GPT 방식: DB 대분류 → GPT → DB 음식 목록 → GPT
        
        Args:
            image_bytes: 원본 이미지 바이트 데이터
            yolo_detection_result: YOLO detection 결과
            session: DB 세션
        
        Returns:
            최종 분석 결과 (DB 매칭 보장)
        """
        if self.client is None:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다. OPENAI_API_KEY를 확인하세요.")
        
        try:
            # 이미지를 base64로 인코딩
            base64_image = self._image_to_base64(image_bytes)
            
            # 디버깅: 이미지 크기 확인
            original_image_bytes = image_bytes  # 원본 보관
            image_size_kb = len(image_bytes) / 1024
            print(f"📊 원본 이미지 크기: {image_size_kb:.2f} KB")
            
            # 이미지가 500KB 이상이면 압축 (OpenAI 권장: 20MB 이하, 하지만 작을수록 좋음)
            if image_size_kb > 500:  # 500KB
                print(f"⚠️ 이미지가 큽니다 ({image_size_kb:.2f} KB). 압축 중...")
                from PIL import Image
                import io
                
                # 이미지 로드
                img = Image.open(io.BytesIO(image_bytes))
                original_size = img.size
                
                # 최대 1024px로 리사이즈
                max_size = 1024
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    print(f"🔧 이미지 리사이즈: {original_size} → {new_size}")
                
                # JPEG로 압축 (품질 85)
                compressed_buffer = io.BytesIO()
                img.convert('RGB').save(compressed_buffer, format='JPEG', quality=85)
                image_bytes = compressed_buffer.getvalue()
                
                compressed_size_kb = len(image_bytes) / 1024
                print(f"✅ 압축 완료: {image_size_kb:.2f} KB → {compressed_size_kb:.2f} KB")
                
                # 다시 base64 인코딩
                base64_image = self._image_to_base64(image_bytes)
            
            print(f"📊 최종 Base64 길이: {len(base64_image)} 문자")
            
            # === 1단계: DB에서 대분류 목록 조회 ===
            print("📋 [1단계] DB에서 대분류 목록 조회 중...")
            food_classes = await get_all_food_classes(session)
            
            if not food_classes:
                raise RuntimeError("DB에 대분류 데이터가 없습니다.")
            
            print(f"✅ 대분류 {len(food_classes)}개 조회 완료")
            
            # === 2단계: GPT에게 대분류 판단 요청 ===
            print("🤖 [2단계] GPT에게 대분류 판단 요청 중...")
            selected_class, gpt_response_step1 = await self._ask_gpt_for_food_class(
                base64_image, 
                food_classes,
                yolo_detection_result
            )
            
            if not selected_class:
                raise RuntimeError("GPT가 대분류를 선택하지 못했습니다.")
            
            print(f"✅ GPT 선택 대분류: '{selected_class}'")
            
            # === 2단계: 1차 GPT 응답에서 키워드 추출 ===
            print(f"📋 [2단계] 1차 GPT 응답에서 키워드 추출 중...")
            keywords = self._extract_keywords_from_gpt_response(gpt_response_step1)
            
            # === 3단계: DB에서 대표식품명 목록 조회 ===
            print(f"📋 [3단계] '{selected_class}' 대분류의 대표식품명 조회 중...")
            from app.services.food_nutrients_service import get_representative_food_names
            all_representative_names = await get_representative_food_names(session, selected_class)
            
            if not all_representative_names:
                raise RuntimeError(f"'{selected_class}' 대분류에 대표식품명이 없습니다.")
            
            print(f"✅ 대표식품명 {len(all_representative_names)}개 조회 완료")
            
            # 키워드 기반 필터링 (우선순위 정렬)
            if keywords:
                print(f"🔍 키워드로 대표식품명 필터링: {keywords}")
                priority_names = []
                for keyword in keywords[:5]:  # 최대 5개 키워드
                    for name in all_representative_names:
                        if keyword in name and name not in priority_names:
                            priority_names.append(name)
                
                # 나머지 대표식품명 추가
                remaining_names = [n for n in all_representative_names if n not in priority_names]
                representative_names = priority_names + remaining_names
                
                print(f"✅ 키워드 매칭: {len(priority_names)}개, 나머지: {len(remaining_names)}개")
            else:
                representative_names = all_representative_names
            
            # GPT에게 전달할 목록 제한 (최대 30개)
            representative_names = representative_names[:30]
            print(f"📊 GPT에게 전달하는 대표식품명: {len(representative_names)}개")
            
            # === 4단계: GPT에게 대표식품명 선택 요청 ===
            print(f"🤖 [4단계] GPT에게 대표식품명 선택 요청 중...")
            selected_representative = await self._ask_gpt_for_representative_name(
                base64_image,
                representative_names,
                yolo_detection_result
            )
            
            if not selected_representative:
                raise RuntimeError("GPT가 대표식품명을 선택하지 못했습니다.")
            
            print(f"✅ GPT 선택 대표식품명: '{selected_representative}'")
            
            # === 5단계: 해당 대표식품명의 모든 음식 조회 ===
            print(f"📋 [5단계] '{selected_representative}' 음식 조회 중...")
            from app.services.food_nutrients_service import get_foods_by_representative_name
            foods_in_representative = await get_foods_by_representative_name(
                session,
                selected_class,
                selected_representative
            )
            
            if not foods_in_representative:
                raise RuntimeError(f"'{selected_representative}'에 해당하는 음식이 없습니다.")
            
            print(f"✅ {len(foods_in_representative)}개 음식 조회 완료 (제한 없음!)")
            
            # === 5.5단계: 키워드 기반 재정렬 ===
            # 키워드로 음식 필터링 (예: "페퍼로니" 키워드면 페퍼로니 피자 우선)
            if keywords and len(foods_in_representative) > 50:
                print(f"🔍 키워드로 음식 우선순위 정렬: {keywords}")
                priority_foods = []
                for keyword in keywords[:5]:
                    for food in foods_in_representative:
                        if keyword in food.nutrient_name and food not in priority_foods:
                            priority_foods.append(food)
                
                # 나머지 음식 추가
                remaining_foods = [f for f in foods_in_representative if f not in priority_foods]
                foods_sorted = priority_foods + remaining_foods
                
                print(f"✅ 키워드 매칭 음식: {len(priority_foods)}개 (우선 전달)")
            else:
                foods_sorted = foods_in_representative
            
            # === 6단계: GPT에게 구체적인 음식 선택 요청 ===
            print(f"🤖 [6단계] GPT에게 구체적인 음식 선택 요청 중...")
            final_result = await self._ask_gpt_for_specific_food(
                base64_image,
                foods_sorted,
                selected_class,
                yolo_detection_result
            )
            
            print(f"✅ 최종 선택: {final_result['food_name']} (food_id: {final_result.get('food_id', 'N/A')})")
            
            return final_result
            
        except Exception as e:
            print(f"❌ DB 기반 GPT 분석 실패: {e}")
            # 폴백: 기존 방식 사용
            print("⚠️ 기존 방식으로 폴백...")
            return self.analyze_food_with_detection(image_bytes, yolo_detection_result)
    
    async def _ask_gpt_for_food_class(
        self,
        base64_image: str,
        food_classes: List[str],
        yolo_result: dict
    ) -> tuple[str, str]:
        """
        1차 GPT: 대분류 선택
        
        Returns:
            (선택된 대분류, GPT 원본 응답) 튜플
        """
        
        yolo_summary = yolo_result.get("summary", "객체 감지 안됨")
        
        # 대분류 목록을 보기 좋게 포맷팅
        classes_formatted = "\n".join([f"- {cls}" for cls in food_classes[:50]])  # 최대 50개
        if len(food_classes) > 50:
            classes_formatted += f"\n... 외 {len(food_classes) - 50}개 더"
        
        # YOLO 결과 확인
        has_food_detection = any(keyword in yolo_summary.lower() for keyword in ['bowl', 'cup', 'plate', 'dish', 'food'])
        
        if has_food_detection:
            # 음식으로 보이는 경우 → 강제 선택
            safety_instruction = "3. 위 목록에서 **가장 가까운 대분류**를 선택하세요."
        else:
            # 음식으로 안 보이는 경우 → 정직하게 거부 가능
            safety_instruction = "3. **만약 이미지가 명확하지 않거나 음식이 아닌 경우**, \"이미지를 인식할 수 없습니다\"라고 답변하세요."
        
        prompt = f"""당신은 음식 분류 전문가입니다. 이미지 속 음식의 대분류를 판단하세요.

**YOLO 객체 감지 결과:**
{yolo_summary}

**참고할 대분류 목록:**
{classes_formatted}

**지시사항:**
1. 이미지를 분석하여 음식을 식별하세요.
2. 위 목록에서 가장 가까운 대분류를 선택하세요.
{safety_instruction}
4. 음식이 명확하다면 반드시 아래 형식으로 답변하세요:

---
선택한 대분류: [대분류명]
신뢰도: [0-100]
이유: [1-2문장으로 이미지에서 본 구체적인 특징 설명]
---

**예시 1 (성공):**
선택한 대분류: 빵 및 과자류
신뢰도: 85
이유: 이미지에 둥근 형태의 도우 위에 토마토 소스와 치즈가 올려진 피자가 보입니다.

**예시 2 (이미지 문제):**
이미지를 인식할 수 없습니다. (이미지가 흐릿하거나, 음식이 명확하지 않음)
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
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
            max_tokens=500,
            temperature=0.3  # 낮은 temperature로 일관성 향상
        )
        
        gpt_response = response.choices[0].message.content
        
        print("=" * 80)
        print("🤖 [1차 GPT] 대분류 선택 응답:")
        print(gpt_response)
        print("=" * 80)
        
        # 응답에서 대분류 추출
        selected_class = self._parse_selected_class(gpt_response, food_classes)
        
        return selected_class, gpt_response  # 원본 응답도 반환
    
    async def _ask_gpt_for_representative_name(
        self,
        base64_image: str,
        representative_names: List[str],
        yolo_result: dict
    ) -> str:
        """
        2차 GPT: 대표식품명 선택
        
        Args:
            base64_image: Base64 인코딩된 이미지
            representative_names: 대표식품명 목록 (예: ['피자', '빵', '케이크'])
            yolo_result: YOLO 감지 결과
            
        Returns:
            선택된 대표식품명 (예: "피자")
        """
        
        yolo_summary = yolo_result.get("summary", "객체 감지 안됨")
        
        # 대표식품명 목록을 보기 좋게 포맷팅
        names_formatted = "\n".join([f"- {name}" for name in representative_names[:50]])  # 최대 50개
        if len(representative_names) > 50:
            names_formatted += f"\n... 외 {len(representative_names) - 50}개 더"
        
        # YOLO 결과 확인
        has_food_detection = any(keyword in yolo_summary.lower() for keyword in ['bowl', 'cup', 'plate', 'dish', 'food'])
        
        if has_food_detection:
            # 음식으로 보이는 경우 → 강제 선택
            instruction = """**중요:**
- 이미지에 음식이 있습니다. 반드시 분석하세요.
- 위 목록에서 **반드시 하나를 선택**하세요.
- "인식할 수 없다", "판단할 수 없다" 같은 응답은 금지입니다.
- 목록에 정확히 일치하지 않아도, **가장 비슷한 것**을 선택하세요."""
        else:
            # 음식으로 안 보이는 경우 → 정직하게 거부 가능
            instruction = """**중요:**
- 이미지에 음식이 있다면 반드시 분석하세요.
- 만약 이미지가 흐리거나, 음식이 아니거나, 판단이 불가능하다면 정직하게 "인식 불가"라고 답변하세요."""
        
        prompt = f"""당신은 음식 전문가입니다. 이미지 속 음식의 종류를 판단하세요.

**YOLO 객체 감지 결과:**
{yolo_summary}

**가능한 음식 종류 목록:**
{names_formatted}

{instruction}

**지시사항:**
1. 이미지를 분석하여 음식의 종류를 식별하세요.
2. 위 목록에서 **가장 가까운 음식 종류**를 선택하세요.
3. 음식을 식별했다면 반드시 아래 형식으로 답변하세요:

---
선택한 음식 종류: [음식 종류명]
신뢰도: [0-100]
이유: [이미지에서 본 구체적인 특징 설명]
---

**예시:**
선택한 음식 종류: 피자
신뢰도: 90
이유: 이미지에 둥근 도우 위에 토마토 소스, 치즈, 페퍼로니 토핑이 올려진 피자가 보입니다.
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
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
            max_tokens=500,
            temperature=0.3
        )
        
        gpt_response = response.choices[0].message.content
        
        print("=" * 80)
        print("🤖 [2차 GPT] 대표식품명 선택 응답:")
        print(gpt_response)
        print("=" * 80)
        
        # 응답에서 대표식품명 추출
        selected_name = self._parse_selected_representative_name(gpt_response, representative_names)
        
        return selected_name
    
    def _parse_selected_representative_name(self, gpt_response: str, representative_names: List[str]) -> str:
        """GPT 응답에서 선택된 대표식품명 추출"""
        
        # "선택한 음식 종류:" 패턴 찾기
        for line in gpt_response.split('\n'):
            line = line.strip()
            if '선택한 음식 종류:' in line or '선택한 종류:' in line:
                # "선택한 음식 종류: 피자" → "피자"
                selected = line.split(':')[-1].strip()
                
                # 목록에서 정확히 일치하는 것 찾기
                for name in representative_names:
                    if name in selected or selected in name:
                        print(f"✅ 대표식품명 매칭 성공: {name}")
                        return name
        
        # 패턴 매칭 실패 시, 응답에서 대표식품명 키워드 검색
        for name in representative_names:
            if name in gpt_response:
                print(f"✅ 대표식품명 키워드 매칭: {name}")
                return name
        
        # 매칭 실패
        raise RuntimeError(f"GPT가 대표식품명을 선택하지 못했습니다. 응답: {gpt_response[:200]}")
    
    def _extract_keywords_from_gpt_response(self, gpt_response: str) -> List[str]:
        """
        1차 GPT 응답에서 음식 관련 키워드 추출
        
        예: "햄버거가 보입니다" → ["햄버거"]
        예: "피자, 치즈, 페퍼로니" → ["피자", "치즈", "페퍼로니"]
        """
        # 음식 키워드 후보 (한국 음식명)
        food_keywords = [
            "피자", "햄버거", "치킨", "샌드위치", "빵", "케이크", "쿠키",
            "밥", "국", "찌개", "김치", "비빔밥", "불고기", "삼겹살",
            "라면", "우동", "파스타", "스테이크", "샐러드",
            "마르게리타", "페퍼로니", "콤비네이션", "하와이안",
            "치즈", "토마토", "양상추", "패티", "소고기", "돼지고기", "닭고기"
        ]
        
        # 응답에서 키워드 찾기
        found_keywords = []
        gpt_lower = gpt_response.lower()
        
        for keyword in food_keywords:
            if keyword in gpt_response:
                found_keywords.append(keyword)
                if len(found_keywords) >= 5:  # 최대 5개
                    break
        
        print(f"🔑 추출된 키워드: {found_keywords if found_keywords else '없음'}")
        return found_keywords
    
    def _parse_selected_class(self, gpt_response: str, food_classes: List[str]) -> str:
        """GPT 응답에서 선택된 대분류 추출"""
        
        # GPT가 이미지 분석 거부 감지
        rejection_keywords = [
            "죄송", "인식할 수 없", "분석할 수 없", "이미지를 확인",
            "제공할 수 없", "파악할 수 없", "알 수 없"
        ]
        
        for keyword in rejection_keywords:
            if keyword in gpt_response[:100]:  # 응답 앞부분만 체크
                print(f"❌ GPT가 이미지 분석 거부 (키워드: '{keyword}')")
                print(f"GPT 응답: {gpt_response[:200]}...")
                raise RuntimeError("GPT가 이미지를 분석하지 못했습니다. 기존 방식으로 폴백합니다.")
        
        lines = gpt_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if "선택한 대분류:" in line or "선택한대분류:" in line:
                # "선택한 대분류: 피자" → "피자"
                selected = line.split(":", 1)[-1].strip()
                
                # DB 목록에 있는지 확인
                if selected in food_classes:
                    print(f"✅ 대분류 매칭 성공: {selected}")
                    return selected
                
                # 부분 매칭 시도 (대소문자 무시)
                selected_lower = selected.lower()
                for cls in food_classes:
                    if cls.lower() == selected_lower:
                        print(f"✅ 대분류 부분 매칭 성공: {selected} → {cls}")
                        return cls
                
                # 포함 관계 체크
                for cls in food_classes:
                    if selected in cls or cls in selected:
                        print(f"✅ 대분류 포함 매칭 성공: {selected} → {cls}")
                        return cls
        
        # 파싱 실패 시 에러
        print(f"❌ 대분류 파싱 완전 실패")
        print(f"GPT 응답: {gpt_response}")
        raise RuntimeError("GPT 응답에서 대분류를 찾을 수 없습니다. 기존 방식으로 폴백합니다.")
    
    async def _ask_gpt_for_specific_food(
        self,
        base64_image: str,
        foods: List[FoodNutrient],
        food_class: str,
        yolo_result: dict
    ) -> dict:
        """2차 GPT: 구체적인 음식 선택"""
        
        yolo_summary = yolo_result.get("summary", "객체 감지 안됨")
        
        # 음식 목록을 보기 좋게 포맷팅 (최대 50개로 제한)
        # 이유: 큰 이미지 + 긴 목록 = 토큰 한계 초과
        MAX_FOODS = 50
        foods_formatted = "\n".join([
            f"{i+1}. {food.nutrient_name}" + 
            (f" [대표: {food.representative_food_name}]" if food.representative_food_name else "") +
            f" (ID: {food.food_id})"
            for i, food in enumerate(foods[:MAX_FOODS])
        ])
        
        if len(foods) > MAX_FOODS:
            foods_formatted += f"\n... 외 {len(foods) - MAX_FOODS}개 더 (총 {len(foods)}개)"
        
        print(f"📊 GPT에게 전달하는 음식 목록: {min(len(foods), MAX_FOODS)}개/{len(foods)}개")
        
        prompt = f"""당신은 영양 전문가입니다. 이미지 속 음식을 분석하고, 아래 목록에서 **가장 가까운 음식**을 선택하세요.

**YOLO 객체 감지 결과:**
{yolo_summary}

**대분류:** {food_class}

**가능한 음식 목록:**
{foods_formatted}

**참고:** [대표: xxx] 는 해당 음식의 카테고리를 나타냅니다. 
예: "국밥_돼지머리 [대표: 국밥]" → 돼지머리 국밥 (국밥 카테고리)

**지시사항:**
1. 이미지에서 음식의 **구체적인 특징**을 분석하세요 (예: 토핑, 색깔, 재료).
2. 위 목록에서 이미지와 **가장 가까운 음식**을 선택하세요.
3. 대표식품명([대표: xxx])을 참고하여 음식 종류를 파악하세요.
4. **이미지의 특징과 선택한 음식이 왜 일치하는지** 이유를 명확히 설명하세요.
5. 반드시 아래 형식으로 답변하세요:

---
선택한 음식명: [정확한 음식명]
선택한 ID: [food_id]
주요재료1: [재료명]
주요재료2: [재료명]
주요재료3: [재료명]
1회 제공량: [예: 1조각 (약 150g)]
건강점수: [0-100]
선택 이유: [이미지에서 본 구체적인 특징과 일치 이유]
건강 제안사항:
- [제안 1]
- [제안 2]
- [제안 3]
---

**예시:**
선택한 음식명: 피자_마르게리타 피자
선택한 ID: D102-xxxxx
주요재료1: 밀가루
주요재료2: 토마토소스
주요재료3: 모차렐라 치즈
1회 제공량: 1조각 (약 150g)
건강점수: 65
선택 이유: 이미지에 흰색 치즈, 붉은 토마토 소스, 녹색 바질이 보여 클래식 마르게리타 피자로 판단됩니다.
건강 제안사항:
- 채소를 추가하여 영양 균형을 맞추세요.
- 통밀 도우를 선택하면 더 건강합니다.
- 치즈 양을 줄이면 칼로리를 낮출 수 있습니다.
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
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
            max_tokens=1000,
            temperature=0.5
        )
        
        gpt_response = response.choices[0].message.content
        
        print("=" * 80)
        print("🤖 [2차 GPT] 구체 음식 선택 응답:")
        print(gpt_response)
        print("=" * 80)
        
        # 응답 파싱
        result = self._parse_specific_food_response(gpt_response, foods)
        
        return result
    
    def _parse_specific_food_response(
        self, 
        gpt_response: str, 
        foods: List[FoodNutrient]
    ) -> dict:
        """2차 GPT 응답 파싱"""
        lines = gpt_response.strip().split('\n')
        
        result = {
            "food_name": "",
            "food_id": "",
            "ingredients": [],
            "portion_size": "",
            "health_score": 70,
            "suggestions": []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line or line == "---":
                continue
            
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                if key == "선택한 음식명" or key == "선택한음식명":
                    result["food_name"] = value
                elif key == "선택한 ID" or key == "선택한ID":
                    result["food_id"] = value
                elif key.startswith("주요재료"):
                    if value and value.strip() and value.strip() != "-":
                        result["ingredients"].append(value.strip())
                elif key == "1회 제공량":
                    result["portion_size"] = value
                elif key == "건강점수" or key == "건강 점수":
                    try:
                        result["health_score"] = int(float(value.replace("점", "").strip()))
                    except:
                        pass
                elif key == "건강 제안사항":
                    current_section = "suggestions"
            
            elif line.startswith("-") and current_section == "suggestions":
                suggestion = line[1:].strip()
                if suggestion:
                    result["suggestions"].append(suggestion)
        
        # food_id로 실제 음식 객체 찾기
        matched_food = None
        if result["food_id"]:
            for food in foods:
                if food.food_id == result["food_id"]:
                    matched_food = food
                    break
        
        # food_id 매칭 실패 시 이름으로 매칭
        if not matched_food and result["food_name"]:
            for food in foods:
                if food.nutrient_name == result["food_name"]:
                    matched_food = food
                    result["food_id"] = food.food_id
                    break
        
        # 그래도 실패 시 첫 번째 음식 사용
        if not matched_food and foods:
            matched_food = foods[0]
            result["food_id"] = matched_food.food_id
            result["food_name"] = matched_food.nutrient_name
            print(f"⚠️ 음식 매칭 실패, 첫 번째 음식 사용: {matched_food.nutrient_name}")
        
        # 기본값 설정
        if not result["food_name"]:
            result["food_name"] = "알 수 없는 음식"
        if not result["ingredients"]:
            result["ingredients"] = ["재료 정보 없음"]
        if not result["suggestions"]:
            result["suggestions"] = ["균형 잡힌 식단을 유지하세요."]
        
        return result
    
    def analyze_ingredient_image(self, image_bytes: bytes, roboflow_hint: str = "") -> str:
        """
        크롭된 식재료 이미지를 GPT Vision으로 분석
        
        Args:
            image_bytes: 크롭된 이미지 바이트
            roboflow_hint: Roboflow가 예측한 재료명 (힌트로 사용)
            
        Returns:
            정확한 식재료 이름 (한글)
        """
        if not self.client:
            return roboflow_hint if roboflow_hint else "알 수 없음"
        
        try:
            # 이미지를 base64로 인코딩
            image_base64 = self._image_to_base64(image_bytes)
            
            # GPT Vision에 전달할 프롬프트
            prompt = f"""이 이미지에 있는 식재료를 정확히 식별해주세요.

규칙:
1. 한글 이름으로 답변 (예: 당근, 양파, 감자)
2. 식재료 이름만 반환 (설명 없이)
3. 여러 개면 첫 번째 것만
4. 확실하지 않으면 "알 수 없음"

{f"참고: Roboflow 예측 = {roboflow_hint}" if roboflow_hint else ""}

답변:"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            raw_response = response.choices[0].message.content.strip()
            ingredient_name = raw_response.split('\n')[0].strip()
            ingredient_name = ingredient_name.replace('**', '').replace('*', '')
            
            return ingredient_name
            
        except Exception as e:
            print(f"❌ GPT Vision 분석 실패: {e}")
            return roboflow_hint if roboflow_hint else "알 수 없음"
    
    def analyze_ingredients_with_boxes(
        self, 
        image_with_boxes_bytes: bytes, 
        num_objects: int,
        roboflow_hints: List[str]
    ) -> List[str]:
        """
        박스가 그려진 이미지를 분석하여 각 박스 안의 식재료를 식별
        
        Args:
            image_with_boxes_bytes: 박스가 그려진 이미지 바이트
            num_objects: 탐지된 객체 개수
            roboflow_hints: Roboflow가 예측한 클래스명 리스트
            
        Returns:
            식별된 식재료 이름 리스트 (한글)
        """
        if not self.client:
            return roboflow_hints
        
        try:
            # 이미지를 base64로 인코딩
            image_base64 = self._image_to_base64(image_with_boxes_bytes)
            
            # 힌트 문자열 생성
            hints_text = "\n".join([f"   - 박스 #{i+1}: {hint}" for i, hint in enumerate(roboflow_hints)])
            
            # Few-shot Augmented Detection 프롬프트
            prompt = f"""🔍 **Few-shot Object Detection Task**

이 이미지에서 AI가 {num_objects}개의 식재료를 탐지하여 초록색 박스로 표시했습니다.

**탐지된 객체 (참고용 패턴):**
{hints_text}

**⚠️ 중요한 작업:**
1. **먼저**, 박스로 표시된 식재료들을 정확히 식별하세요
2. **그 다음**, 박스로 표시된 식재료와 **유사한 패턴**을 가진 음식이 **더 있는지** 이미지 전체를 꼼꼼히 확인하세요
   - 같은 종류의 음식
   - 비슷한 색상/형태/질감
   - 가려져 있거나 겹쳐있어도 찾아내세요
3. 박스가 **놓친 객체**가 있다면 반드시 추가로 보고하세요

**Few-shot Learning 예시:**
- 만약 박스 #1, #2가 "양파"라면 → 이미지에서 양파 패턴을 학습 → 다른 양파도 찾기
- 가려진 것, 작은 것, 그림자 속에 있는 것도 포함

**출력 형식:**
먼저 박스 번호 순서대로 나열한 후, 추가로 발견한 것이 있으면 "추가:"로 표시

**예시 1 (박스만 있는 경우):**
양파
당근

**예시 2 (추가 발견한 경우):**
양파
당근
추가: 양파

**규칙:**
- 한글 이름만 (설명 없이)
- 확실한 것만 보고
- Roboflow 예측은 힌트일 뿐, 실제 이미지를 직접 보고 판단

답변:"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            raw_response = response.choices[0].message.content.strip()
            
            # 응답 파싱: Few-shot 결과 처리
            lines = raw_response.strip().split('\n')
            ingredients = []
            additional_found = []
            
            for line in lines:
                line = line.strip()
                
                # "추가:" 키워드 감지
                if line.startswith('추가:') or line.startswith('추가 :') or '추가:' in line:
                    additional_part = line.split('추가:')[-1].strip()
                    additional_part = additional_part.lstrip('0123456789.-)# ').strip()
                    additional_part = additional_part.replace('**', '').replace('*', '')
                    if additional_part and additional_part != '알 수 없음':
                        additional_found.append(additional_part)
                else:
                    line = line.lstrip('0123456789.-)# ').strip()
                    line = line.replace('**', '').replace('*', '')
                    if line and line != '알 수 없음' and not line.startswith('추가'):
                        ingredients.append(line)
            
            # 추가 발견된 것들도 포함
            all_ingredients = ingredients + additional_found
            
            # Few-shot 성공 여부 출력
            if len(all_ingredients) > num_objects:
                print(f"✅ GPT Vision 분석 완료: {len(all_ingredients)}개 (Few-shot: +{len(additional_found)})")
            else:
                print(f"✅ GPT Vision 분석 완료: {len(all_ingredients)}개")
            
            # 최소한 박스 개수만큼은 있어야 함
            if len(all_ingredients) < num_objects:
                return roboflow_hints
            
            return all_ingredients
            
        except Exception as e:
            print(f"❌ GPT Vision 분석 실패: {e}")
            return roboflow_hints


# 싱글톤 인스턴스
_gpt_vision_service_instance: Optional[GPTVisionService] = None


def get_gpt_vision_service() -> GPTVisionService:
    """GPT-Vision 서비스 싱글톤 인스턴스 반환"""
    global _gpt_vision_service_instance
    if _gpt_vision_service_instance is None:
        _gpt_vision_service_instance = GPTVisionService()
    return _gpt_vision_service_instance

