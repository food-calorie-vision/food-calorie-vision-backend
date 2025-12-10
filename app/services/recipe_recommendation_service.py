"""레시피 추천 서비스 - LangChain 기반 개인화 레시피 추천 및 단계별 조리법"""
import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from app.core.config import get_settings
from app.db.models import User

settings = get_settings()
DETAIL_CACHE_TTL_SECONDS = 300


@dataclass
class RecipePromptContext:
    """LLM 프롬프트를 구성할 때 반복 사용되는 건강/끼니 맥락."""

    health_goal_label: str
    health_info_text: str
    today_status_text: str
    excess_warnings_text: str
    meal_type_text: str


@dataclass
class RecipePipelineTasks:
    """병렬로 실행되는 레시피 관련 LangChain 작업 묶음."""

    health_analysis_task: Optional[asyncio.Task]
    recommendation_task: asyncio.Task
    detail_prefetch_task: Optional[asyncio.Task] = None

    async def get_health_analysis(self) -> Optional[Dict[str, Any]]:
        if not self.health_analysis_task:
            return None
        return await self.health_analysis_task

    async def get_recommendations(self) -> Dict[str, Any]:
        return await self.recommendation_task

    async def get_prefetched_details(self) -> Dict[str, Any]:
        if not self.detail_prefetch_task:
            return {}
        return await self.detail_prefetch_task

    def cancel_pending(self) -> None:
        for task in (self.health_analysis_task, self.recommendation_task, self.detail_prefetch_task):
            if task and not task.done():
                task.cancel()


class RecipeRecommendationService:
    """GPT를 활용한 개인 맞춤 레시피 추천 및 조리법 서비스"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.chat_llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4o-mini",
            temperature=0.7,
        )
        self.json_llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4o-mini",
            temperature=0.4,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self._prefetched_detail_cache: Dict[tuple[int, str], Dict[str, Any]] = {}

    def _build_prompt_context(
        self,
        user: User,
        diseases: Optional[List[str]],
        allergies: Optional[List[str]],
        has_eaten_today: bool,
        deficient_nutrients: Optional[List[Dict[str, Any]]],
        excess_warnings: Optional[List[str]],
        meal_type: Optional[str],
    ) -> RecipePromptContext:
        health_goal_kr = {
            "loss": "체중 감량",
            "maintain": "체중 유지",
            "gain": "체중 증가"
        }.get(user.health_goal, "체중 유지")

        health_info_parts = []
        if diseases:
            health_info_parts.append(f"질병: {', '.join(diseases)}")
        if allergies:
            health_info_parts.append(f"알레르기: {', '.join(allergies)}")
        health_info_text = "\n- " + "\n- ".join(health_info_parts) if health_info_parts else "\n- 없음"

        today_status_text = ""
        if not has_eaten_today:
            today_status_text = "\n\n**오늘 식사 현황:**\n- 오늘 아직 아무것도 먹지 않았습니다."
        elif deficient_nutrients:
            deficient_list = [
                f"- {n['name']}: 권장량의 {n['percentage']}%만 섭취 (부족)"
                for n in deficient_nutrients
            ]
            today_status_text = f"\n\n**오늘 식사 현황 및 부족 영양소:**\n" + "\n".join(deficient_list)
            today_status_text += "\n\n**중요:** 사용자가 요청한 재료에 추가로 부족한 영양소를 보완할 수 있는 재료를 포함한 레시피를 추천해주세요."
            today_status_text += "\n예: 단백질이 부족하면 흰살 생선, 콩류, 살코기, 해산물 등을 다양하게 활용하고, 식이섬유가 부족하면 해조류, 버섯, 다양한 색깔의 채소 등을 추가하여 식단의 단조로움을 피하세요."

        excess_warnings_text = ""
        if excess_warnings:
            excess_warnings_text = "\n\n**⚠️ 건강 알림:**\n" + "\n".join(
                [f"- {w}" for w in excess_warnings]
            )
            excess_warnings_text += "\n\n**중요:** 위 경고를 사용자에게 알리되, 레시피는 반드시 추천해주세요. 다만 칼로리와 나트륨이 낮은 건강한 레시피를 우선 추천해주세요."

        meal_type_kr = {
            "breakfast": "아침",
            "lunch": "점심",
            "dinner": "저녁",
            "snack": "간식"
        }.get(meal_type, "")
        meal_type_text = (
            f"\n- **식사 유형:** {meal_type_kr} (이 시간대에 적합한 레시피를 추천하세요)"
            if meal_type_kr else ""
        )

        return RecipePromptContext(
            health_goal_label=health_goal_kr,
            health_info_text=health_info_text,
            today_status_text=today_status_text,
            excess_warnings_text=excess_warnings_text,
            meal_type_text=meal_type_text,
        )

    def _prepare_conversation_messages(
        self,
        conversation_history: Optional[List[Dict[str, str]]],
        keep_last: int = 6,
    ) -> List[Any]:
        """LLM에 전달할 대화 히스토리를 최신 n개만 남겨 구성."""
        if not conversation_history:
            return []
        trimmed = conversation_history[-keep_last:]
        prepared: List[Any] = []
        for msg in trimmed:
            role = msg.get("role")
            content = msg.get("content", "")
            if not content:
                continue
            if role == "assistant":
                prepared.append(AIMessage(content=content))
            else:
                prepared.append(HumanMessage(content=content))
        return prepared

    def _build_recipe_prompt(
        self,
        user: User,
        intent_text: str,
        context: RecipePromptContext,
        diseases: Optional[List[str]] = None,
        allergies: Optional[List[str]] = None,
        intent_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        metadata_text = ""
        safety_directive = ""
        
        # 리스트 포맷팅 (빈 리스트 처리)
        diseases_str = ", ".join(diseases) if diseases else "없음"
        allergies_str = ", ".join(allergies) if allergies else "없음"
        
        if intent_metadata:
            safe_items = []
            if intent_metadata.get("intent_summary"):
                safe_items.append(f"- 의도: {intent_metadata['intent_summary']}")
            
            # 위험 요소 요약
            risk_flags = intent_metadata.get("risk_flags")
            if isinstance(risk_flags, list) and risk_flags:
                safe_items.append(f"- 위험: {', '.join(risk_flags)}")
            
            safety_mode = intent_metadata.get("safety_mode")
            
            # === [분기 처리] safety_mode에 따라 지시 사항 최적화 ===
            if safety_mode == "health_first":
                safe_items.append("- 모드: 건강/안전 우선 (대체 레시피)")
                
                # 3단계 안전 계층 (Safety Hierarchy) & 맛의 조화
                safety_directive = f"""
**[핵심 지시: 3단계 안전 및 맛 보장]**
사용자의 건강을 위해 다음 3단계를 순서대로 적용하세요.

1. **[Level 1: 알레르기 절대 배제 (Critical)]**
   - 알레르기 유발 재료({allergies_str})는 소스/육수를 포함해 **0.01%도 남기지 말고 제거**하세요.
   - 대체가 불가능하면 메뉴 자체를 안전한 것으로 변경하세요.

2. **[Level 2: 질병 관리 (Strict Constraint)]**
   - 질병({diseases_str})에 치명적인 재료(예: 고지혈증-내장류, 당뇨-설탕)는 조리법 변경 대신 **식재료를 '완전 대체'**하세요.
   - 예: "기름 뺀 대창"(X) -> "식감이 쫄깃한 새송이 버섯/관자"(O)

3. **[Level 3: 식감 유지 및 요리적 조화 (Culinary Harmony)]**
   - **금지:** 무조건적인 '닭가슴살', '곤약' 반복 추천, 맛이 없는 괴식(끔찍한 혼종).
   - **권장:** 제외된 재료의 **식감(Texture)과 풍미**를 살리는 **검증된 맛있는 건강 재료**를 사용하세요.
   - 조화 예시: 
     - 쫄깃한 식감(내장) -> 버섯, 전복, 오징어, 두부면
     - 튀김 요리 -> 에어프라이어 구이, 콩가루/현미 베이크
     - 국물 요리 -> 염분을 줄인 채수, 건더기 위주

위 원칙을 지켜 **"맛과 건강을 모두 잡은 현실적인 레시피"**를 제안하세요."""

            elif safety_mode == "proceed":
                safe_items.append("- 모드: 사용자 요청 강행 (경고 무시)")
                safety_directive = """
**[핵심 지시: 사용자 요청 그대로 진행]**
- 사용자가 건강 경고를 인지하고도 **원래의 맛**을 선택했습니다. (타인을 위한 요리일 수 있음)
- 알레르기나 질병 정보를 이유로 재료를 변경하지 마세요.
- **사용자가 요청한 음식의 오리지널 레시피**를 그대로 추천하세요."""
            
            if safe_items:
                metadata_text = "\n\n**추가 분석:**\n" + "\n".join(safe_items)

        prompt = f"""당신은 전문 영양사이자 셰프입니다. 아래 정보를 바탕으로 레시피 3개를 추천하세요.
{safety_directive}

**사용자 프로필:**
- 건강 목표: {context.health_goal_label}
- 기저 질환: {diseases_str}
- 알레르기: {allergies_str}
- 현재 상태:{context.today_status_text}{context.meal_type_text}

**요청 분석:**
{intent_text or "특별한 요청 없음"}{metadata_text}

**작성 규칙:**
1. **1인분 기준:** 모든 레시피의 칼로리와 설명은 **1인분**을 기준으로 작성하세요.
2. **식감/맛 추론:** 사용자가 원하는 식감과 맛의 포인트를 파악하여 반영하세요.
3. **영양 보완:** 부족한 영양소는 자연스러운 재료 추가로 보완하세요. (예: 단백질 부족 -> 흰살생선/콩류/살코기 등 다양화)
4. **메뉴명 작성 (맛집 스타일):** 당신은 5성급 호텔 셰프입니다. 메뉴 이름은 손님이 보자마자 군침이 돌도록 **매력적이고 고급스럽게** 지으세요.
   - **Tone:** 감각적인 형용사(얼큰, 아삭, 고소, 진한)를 활용하세요.
   - **Rule:** 'OO 대신', 'OO 없는' 같은 설명조의 표현은 빼고, **완성된 요리의 맛과 주재료**에만 집중하세요.
   - **예시:** (X) 해물 뺀 채소 짬뽕 -> (O) **진한 사골 버섯 짬뽕**
4. **공감 대화:** 사용자 발화를 반복하지 말고 의도를 재진술하며 공감하세요.
5. **JSON 응답:** 아래 형식만 반환하세요.

**응답 형식 (JSON):**
{{
  "inferred_preference": "추론된 선호도 (예: '매콤하고 쫄깃한 식감 선호')",
  "health_warning": "적용된 건강 조치 설명 (예: '대창 대신 식감이 비슷한 새송이버섯을 사용했어요.')",
  "recommendations": [
    {{
      "name": "레시피 제목",
      "description": "한 줄 소개 (맛과 건강 포인트)",
      "calories": 450,
      "cooking_time": "30분",
      "difficulty": "보통",
      "suitable_reason": "추천 이유"
    }}
  ]
}}"""
        return prompt

    def launch_parallel_recipe_pipeline(
        self,
        *,
        recommendation_kwargs: Dict[str, Any],
        health_check_kwargs: Optional[Dict[str, Any]] = None,
        prefetch_detail_limit: int = 0,
    ) -> RecipePipelineTasks:
        """레시피 추천/건강 분석/상세 조리법 생성을 병렬로 준비."""

        try:
            user_for_detail = recommendation_kwargs["user"]
            diseases_for_detail = recommendation_kwargs.get("diseases")
            allergies_for_detail = recommendation_kwargs.get("allergies")
        except KeyError as exc:  # pragma: no cover - guardrail
            raise ValueError("recommendation_kwargs must include 'user'") from exc

        loop = asyncio.get_running_loop()

        recommendation_task = loop.create_task(
            self.get_recipe_recommendations(**recommendation_kwargs)
        )

        health_task = (
            loop.create_task(self.quick_analyze_intent(**health_check_kwargs))
            if health_check_kwargs
            else None
        )

        detail_task: Optional[asyncio.Task] = None
        if prefetch_detail_limit > 0:
            async def _prefetch_details() -> Dict[str, Any]:
                try:
                    payload = await recommendation_task
                except asyncio.CancelledError:
                    raise
                except Exception:
                    return {}

                recipes = (payload.get("recommendations") or [])[:prefetch_detail_limit]
                recipe_names = [rec.get("name") for rec in recipes if rec.get("name")]
                if not recipe_names:
                    return {}

                detail_results = await asyncio.gather(
                    *[
                        self.get_recipe_detail(
                            recipe_name=name, 
                            user=user_for_detail,
                            diseases=diseases_for_detail,
                            allergies=allergies_for_detail
                        )
                        for name in recipe_names
                    ],
                    return_exceptions=True,
                )
                details: Dict[str, Any] = {}
                for name, result in zip(recipe_names, detail_results):
                    if isinstance(result, Exception):
                        continue
                    details[name] = result
                    self._store_prefetched_detail(user_for_detail, name, result)
                return details

            detail_task = loop.create_task(_prefetch_details())
            detail_task.add_done_callback(self._silence_background_task)

        return RecipePipelineTasks(
            health_analysis_task=health_task,
            recommendation_task=recommendation_task,
            detail_prefetch_task=detail_task,
        )

    async def get_recipe_recommendations(
        self,
        user: User,
        user_request: str = "",
        llm_user_intent: Optional[str] = None,
        conversation_history: List[Dict[str, str]] = None,
        diseases: List[str] = None,
        allergies: List[str] = None,
        user_nickname: str = "",
        has_eaten_today: bool = True,
        deficient_nutrients: List[Dict[str, any]] = None,
        excess_warnings: List[str] = None,
        meal_type: str = None,
        intent_metadata: Optional[Dict[str, Any]] = None,
        safety_mode: str = None,
    ) -> dict:
        """
        사용자 정보를 기반으로 GPT가 레시피 3개를 추천
        
        Args:
            user: User 객체 (gender, age, weight, health_goal 포함)
            user_request: 사용자의 최신 발화
            llm_user_intent: LLM 프롬프트에 사용할 확장된 사용자 의도(없으면 user_request 사용)
            conversation_history: 대화 히스토리 (선택사항)
            diseases: 사용자의 질병 목록 (예: ["고지혈증", "고혈압"])
            allergies: 사용자의 알레르기 목록
            user_nickname: 사용자 닉네임 (메시지 생성용)
            intent_metadata: 이전 단계에서 분석된 intent/risk 정보(JSON)
            safety_mode: 'proceed' (그대로 진행) 또는 'health_first' (건강 우선)
        
        Returns:
            dict: {
                "recommendations": [레시피 3개],
                "health_warning": 건강 경고 메시지 (있으면),
                "inferred_preference": 추론된 선호도 (시스템용),
                "user_friendly_message": 사용자에게 보여줄 친화적 메시지
            }
        """
        if safety_mode:
            if intent_metadata is None:
                intent_metadata = {}
            intent_metadata["safety_mode"] = safety_mode

        context = self._build_prompt_context(
            user=user,
            diseases=diseases,
            allergies=allergies,
            has_eaten_today=has_eaten_today,
            deficient_nutrients=deficient_nutrients,
            excess_warnings=excess_warnings,
            meal_type=meal_type,
        )
        prompt = self._build_recipe_prompt(
            user=user,
            intent_text=llm_user_intent or user_request or "특별한 요청 없음",
            context=context,
            diseases=diseases,
            allergies=allergies,
            intent_metadata=intent_metadata,
        )

        print("🤖 LangChain LLM에게 레시피 추천 요청 중...")
        
        chat_messages = [
            SystemMessage(content="당신은 전문 영양사이자 요리 전문가입니다. JSON 형식으로만 응답합니다.")
        ]
        chat_messages.extend(self._prepare_conversation_messages(conversation_history))
        chat_messages.append(HumanMessage(content=prompt))
        
        response = await self.json_llm.ainvoke(chat_messages)
        gpt_response = response.content
        print("✅ LangChain 응답 수신 완료")
        
        # JSON 파싱
        try:
            result = json.loads(gpt_response)
            
            # 사용자 친화적 메시지 생성
            user_friendly_message = self._generate_user_friendly_message(
                user_request=user_request,
                inferred_preference=result.get("inferred_preference", ""),
                health_warning=result.get("health_warning"),
                diseases=diseases,
                user_nickname=user_nickname,
                has_eaten_today=has_eaten_today,
                deficient_nutrients=deficient_nutrients,
                excess_warnings=excess_warnings  # ✨ 초과 경고 전달
            )
            
            result["user_friendly_message"] = user_friendly_message
            return result
        except json.JSONDecodeError:
            # 파싱 실패 시 기본값 반환
            default_result = {
                "inferred_preference": "다양한 영양소가 골고루 들어간 음식",
                "health_warning": None,
                "recommendations": [
                    {
                        "name": "닭가슴살 샐러드",
                        "description": "고단백 저칼로리 건강식",
                        "calories": 350,
                        "cooking_time": "20분",
                        "difficulty": "쉬움",
                        "suitable_reason": "건강 목표에 적합한 균형 잡힌 식단"
                    },
                    {
                        "name": "연어 덮밥",
                        "description": "오메가-3가 풍부한 영양식",
                        "calories": 480,
                        "cooking_time": "25분",
                        "difficulty": "보통",
                        "suitable_reason": "필수 지방산과 단백질이 풍부"
                    },
                    {
                        "name": "두부 스테이크",
                        "description": "식물성 단백질이 풍부한 요리",
                        "calories": 320,
                        "cooking_time": "15분",
                        "difficulty": "쉬움",
                        "suitable_reason": "저칼로리 고단백 식품"
                    }
                ]
            }
            default_result["user_friendly_message"] = self._generate_user_friendly_message(
                user_request=user_request,
                inferred_preference=default_result["inferred_preference"],
                health_warning=None,
                diseases=diseases,
                user_nickname=user_nickname,
                excess_warnings=excess_warnings  # ✨ 초과 경고 전달
            )
            return default_result

    async def quick_analyze_intent(
        self,
        user: User,
        intent_text: str,
        diseases: Optional[List[str]] = None,
        allergies: Optional[List[str]] = None,
        has_eaten_today: bool = True,
        deficient_nutrients: Optional[List[Dict[str, Any]]] = None,
        excess_warnings: Optional[List[str]] = None,
        meal_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """레시피 생성 전에 건강 경고 여부를 구조화해 반환"""
        context = self._build_prompt_context(
            user=user,
            diseases=diseases,
            allergies=allergies,
            has_eaten_today=has_eaten_today,
            deficient_nutrients=deficient_nutrients,
            excess_warnings=excess_warnings,
            meal_type=meal_type,
        )
        disease_list = ", ".join(diseases or []) or "없음"
        allergy_list = ", ".join(allergies or []) or "없음"
        prompt = f"""당신은 한국어 영양사입니다. 사용자의 요청을 검토해 건강상 위험 여부를 구조화해 판단하세요.

**사용자 요청**
{intent_text or "특별한 요청 없음"}

**건강 맥락**
- 목표: {context.health_goal_label}
{context.health_info_text}{context.excess_warnings_text or ""}

규칙:
1. disease_conflict: 등록된 질병({disease_list})과 요청 메뉴가 충돌하면 true, 아니면 false.
2. allergy_conflict: 등록된 알레르기({allergy_list})에 사용자가 요청한 재료가 포함되면 true, 아니면 false.
3. health_warning: 위험 요인을 한국어 한 문장으로 설명. 둘 다 false면 null.
4. user_message: 공감형 안내 1~2문장.
5. JSON만 출력하고 불리언은 true/false로 표현하세요.

예시:
{{
  "disease_conflict": true,
  "allergy_conflict": false,
  "health_warning": "고혈압이 있어 나트륨 많은 음식은 주의해주세요.",
  "user_message": "좋아하시는 메뉴를 더 건강하게 즐길 수 있도록 도와드릴게요!"
}}"""

        try:
            response = await self.json_llm.ainvoke(
                [
                    SystemMessage(content="당신은 엄격하지만 친절한 한국어 영양사입니다. JSON으로만 응답하세요."),
                    HumanMessage(content=prompt),
                ]
            )
            parsed = json.loads(response.content)
            return {
                "disease_conflict": bool(parsed.get("disease_conflict")),
                "allergy_conflict": bool(parsed.get("allergy_conflict")),
                "health_warning": parsed.get("health_warning"),
                "user_message": parsed.get("user_message"),
            }
        except Exception:
            return {
                "disease_conflict": False,
                "allergy_conflict": False,
                "health_warning": None,
                "user_message": "말씀해주신 내용을 참고해 레시피를 찾아볼게요!",
            }
    
    async def decide_recipe_tool(
        self,
        user: User,
        user_request: str,
        health_context: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """레시피 툴 호출 여부를 판단"""
        history_snippets = []
        if conversation_history:
            for item in conversation_history[-6:]:
                role = item.get("role", "")
                content = item.get("content", "")
                if content:
                    history_snippets.append({"role": role, "content": content})
        history_json = json.dumps(history_snippets, ensure_ascii=False)
        
        prompt = f"""당신은 사용자의 건강 정보를 아는 한국어 영양사입니다.
대화 기록과 사용자의 최신 발화를 보고 레시피 추천 툴을 호출할지 판단하세요.

- call_tool이 true이면 즉시 레시피 카드를 보여주는 것이 좋다고 확신한 경우입니다.
- false이면 아직 상담이나 추가 질문이 필요하다고 판단한 경우이며, assistant_reply에 자연스러운 후속 질문 또는 제안을 작성하세요.
- meal_type은 사용자가 언급했다면 breakfast/lunch/dinner/snack 중 하나로 추측하고, 모르겠으면 null로 두세요.
- intent_summary는 사용자의 확정된 의도를 1문장으로 요약하세요.
- risk_flags는 ["high_sodium", "late_snack"] 처럼 건강상 주의가 필요한 신호를 짧게 담으세요. 없으면 빈 배열을 유지하세요.
- suggestions 배열에는 해당 단계에서 사용자가 실제로 누를 수 있는 2~3개의 짧은 한국어 문장을 넣으세요.
  - call_tool=false: 추가 정보 요청/확인과 관련된 문장만 넣고, 레시피를 바로 보여달라는 문장은 피하세요.
  - call_tool=true인데 meal_type=null: 아침/점심/저녁/간식 중 선택하거나 더 필요한 정보를 말하도록 유도하세요.
  - call_tool=true이고 meal_type이 존재: 레시피 카드를 보여주기 직전 사용자에게 필요한 확답이나 옵션(예: "지금 보여줘", "다른 메뉴 얘기할게")만 넣으세요.
- JSON 형식으로만 답하세요.

예시 형식:
{{
  "call_tool": false,
  "assistant_reply": "오리고기와 닭고기 중 어떤 게 더 끌리시나요?",
  "meal_type": null,
  "intent_summary": "사용자가 구체적인 단백질 메뉴 비교를 원함",
  "risk_flags": [],
  "suggestions": ["닭고기 레시피 말해줘", "다른 재료 알려줄게"]
}}

**사용자 기본 정보**
- 나이: {user.age or 30}세
- 건강 목표: {user.health_goal or 'maintain'}
- 건강 맥락: {health_context or '기록 없음'}

**대화 히스토리(최신 6개)**
{history_json}

**사용자 최신 발화**
{user_request or "입력 없음"}
"""
        messages = [
            SystemMessage(content="JSON으로만 답하는 판단 시스템입니다."),
            HumanMessage(content=prompt),
        ]
        response = await self.json_llm.ainvoke(messages)
        try:
            parsed = json.loads(response.content)
            suggestions = parsed.get("suggestions")
            if not isinstance(suggestions, list):
                parsed["suggestions"] = []
            if "intent_summary" not in parsed:
                parsed["intent_summary"] = user_request or ""
            if "risk_flags" not in parsed or not isinstance(parsed["risk_flags"], list):
                parsed["risk_flags"] = []
            return parsed
        except json.JSONDecodeError:
            return {
                "call_tool": False,
                "assistant_reply": "조금 더 자세히 말씀해주시면 도와드릴게요!",
                "meal_type": None,
                "intent_summary": user_request or "",
                "risk_flags": [],
                "suggestions": ["아침인지 알려줄게", "식사 목적을 설명할게"]
            }

    async def generate_action_suggestions(
        self,
        action_type: str,
        user_request: str = "",
        meal_type: Optional[str] = None,
        recommendations: Optional[List[Dict[str, Any]]] = None,
        deficient_nutrients: Optional[List[Dict[str, Any]]] = None,
        diseases: Optional[List[str]] = None,
        assistant_message: str = ""
    ) -> List[str]:
        """Generative UI 단계에 맞는 follow-up 문구 생성"""
        action_type_upper = (action_type or "").upper()
        fallback_candidates = {
            "TEXT_ONLY": ["자세히 말해볼게", "다른 재료 이야기할게"],
            "CONFIRMATION": ["아침으로 먹을래", "점심으로 부탁해"],
            "RECOMMENDATION_RESULT": ["다른 메뉴도 추천해줘", "다른 식사로 바꿀래"]
        }
        fallback = fallback_candidates.get(action_type_upper, ["다른 메뉴도 추천해줘"])
        
        meal_type_map = {
            "breakfast": "아침",
            "lunch": "점심",
            "dinner": "저녁",
            "snack": "간식"
        }
        meal_label = meal_type_map.get(meal_type or "", "")
        
        recommendations_summary = []
        if recommendations:
            for rec in recommendations[:3]:
                name = rec.get("name")
                reason = rec.get("suitable_reason") or rec.get("description")
                if name:
                    recommendations_summary.append(f"- {name}: {reason or ''}")
        recommendations_text = "\n".join(recommendations_summary) or "없음"
        
        deficient_text = ", ".join(
            [n.get("name") for n in deficient_nutrients or [] if n.get("name")]
        ) or "없음"
        disease_text = ", ".join(diseases or []) or "없음"
        
        prompt = f"""당신은 한국어 영양사 챗봇입니다.
Generative UI에서 사용할 클릭형 추천 문구 2~3개를 JSON으로 만드세요.

- action_type: {action_type_upper or 'UNKNOWN'}
- 식사 유형: {meal_label or '미정'}
- 사용자가 방금 한 말: {user_request or '정보 없음'}
- 당신이 방금 한 말: {assistant_message or '정보 없음'}
- 부족 영양소: {deficient_text}
- 질병/주의: {disease_text}
- 추천 레시피 요약:
{recommendations_text}

지침:
1. suggestions 배열에 2~3개의 짧은 한국어 문장을 넣고, 각 문장은 최대 12자 이내로 자연스럽게 작성하세요.
2. action_type별 제약을 지키세요.
   - TEXT_ONLY: 더 필요한 정보나 사용자의 취향을 묻는 문장만.
   - CONFIRMATION: 아침/점심/저녁/간식 중 택일 또는 필요 정보를 확인하는 문장만.
   - RECOMMENDATION_RESULT: 추천 결과를 기반으로 선택/다른 옵션 요청/저장 등에 해당하는 문장만.
3. 구어체 존댓말을 사용하고, 문장 끝에는 조사나 간단한 긍정 표현으로 마무리하세요.
4. JSON 형식 {{"suggestions": ["...", "..."]}}으로만 응답하세요."""
        
        try:
            response = await self.json_llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(response.content)
            suggestions = parsed.get("suggestions")
            if isinstance(suggestions, list) and suggestions:
                # 문자열만 필터링
                cleaned = [s for s in suggestions if isinstance(s, str) and s.strip()]
                return cleaned or fallback
            return fallback
        except Exception:
            return fallback
    
    async def get_ingredient_check(self, recipe_name: str) -> List[Dict[str, str]]:
        """선택된 레시피의 필수 재료 목록을 빠르게 조회"""
        prompt = f"""당신은 한국어 요리 전문가입니다.

"{recipe_name}" 레시피를 만들 때 필요한 핵심 재료를 5~8개 정도로 간결히 정리해주세요.

**중요 규칙:**
- **모든 재료의 양은 반드시 '1인분'을 기준으로 작성하세요.** (예: 2인분 기준 양파 1개 -> 1인분 양파 1/2개)
- 단위는 g, 개, 큰술 등으로 명확히 표기하세요.

JSON 형식:
{{
  "ingredients": [
    {{"name": "아보카도", "amount": "1개"}},
    {{"name": "바나나", "amount": "1개"}}
  ]
}}

마크다운을 쓰지 말고 JSON만 반환하세요."""
        response = await self.json_llm.ainvoke([
            SystemMessage(content="당신은 재료 정리에 능한 한국어 셰프입니다. JSON으로만 응답하세요."),
            HumanMessage(content=prompt)
        ])
        try:
            parsed = json.loads(response.content)
            items = parsed.get("ingredients") or []
            normalized: List[Dict[str, str]] = []
            for item in items:
                if isinstance(item, dict):
                    normalized.append({
                        "name": item.get("name", "").strip(),
                        "amount": item.get("amount", "").strip()
                    })
                elif isinstance(item, str):
                    normalized.append({"name": item.strip(), "amount": ""})
            return normalized
        except Exception:
            return []
    
    async def generate_custom_cooking_steps(
        self,
        user: User,
        recipe_name: str,
        excluded_ingredients: Optional[List[str]] = None,
        allowed_ingredients: Optional[List[str]] = None,
        meal_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """사용자 제외 재료를 반영한 맞춤 조리법 생성"""
        excluded = excluded_ingredients or []
        allowed = allowed_ingredients or []
        excluded_text = ", ".join(excluded) if excluded else "없음"
        allowed_text = ", ".join(allowed) if allowed else "알 수 없음"
        meal_type_kr = {
            "breakfast": "아침",
            "lunch": "점심",
            "dinner": "저녁",
            "snack": "간식"
        }.get(meal_type or "", "")
        meal_line = f"\n- 식사 유형: {meal_type_kr}" if meal_type_kr else ""
        prompt = f"""당신은 창의적인 한국어 셰프입니다.

레시피 이름: {recipe_name}
제외할 재료: {excluded_text}{meal_line}
원래 재료 목록: {allowed_text}

[작성 규칙]
- **모든 재료 분량과 조리법은 '1인분'을 기준으로 작성하세요.**
- 사용자가 제외한 재료는 조리 과정에 포함하지 마세요.
- 재료를 대체할 경우 ~~원재료~~ **대체재** 표기, 대체가 불가능하면 ~~원재료~~ (생략)으로 명시하세요.
- 단계별 설명은 마크다운으로 작성하고 숫자 목록을 사용하세요.
- 각 단계의 Tip에는 재료 변경에 따른 맛 차이 또는 보완 팁을 포함하세요.
- 사용자의 요청을 그대로 반복하지 말고 공감형 톤으로 안내하세요.
- 레시피 전체 단계는 유지하고, 제외된 재료가 쓰이는 단계만 취소선/생략으로 표시하세요.
- 재료 목록에는 원래 재료를 모두 나열하되, 제외된 재료에는 "(보유 X)" 같은 메모를 붙이세요.
- 반드시 원래 재료 목록에 있는 재료(또는 대체 가능한 합리적 재료)만 사용하고, 존재하지 않는 재료는 추가하지 마세요.
- **메뉴명 작성 (맛집 스타일):** 당신은 5성급 호텔 셰프입니다. 메뉴 이름은 'OO 대신' 같은 변경 내역을 적지 말고, **'얼큰 버섯 황제 짬뽕'**처럼 완성된 요리의 매력적인 이름으로 지으세요.

JSON 형식:
{{
  "intro": "간단 소개",
  "estimated_time": "25분",
  "ingredients": [
    {{"name": "아보카도", "amount": "1개"}},
    {{"name": "아몬드 우유", "amount": "1컵 (보유 X)"}}
  ],
  "steps": [
    {{"step_number": 1, "title": "재료 손질", "description": "아보카도의 씨를 제거하고 속을 파냅니다.", "tip": "레몬즙을 조금 뿌리면 색이 덜 변합니다."}},
    ...
  ],
  "instructions_markdown": "1. ...",
  "nutrition_info": {{
    "calories": 420,
    "protein": "18g",
    "carbs": "45g",
    "fat": "12g",
    "fiber": "6g",
    "sodium": "300mg"
  }},
  "total_weight_g": 350
}}

JSON으로만 응답하세요."""
        response = await self.json_llm.ainvoke([
            SystemMessage(content="당신은 재료 변형에 능한 한국어 셰프입니다. JSON으로만 응답하세요."),
            HumanMessage(content=prompt)
        ])
        try:
            result = json.loads(response.content)
            # 총 중량 기본값 처리
            if "total_weight_g" not in result:
                result["total_weight_g"] = 250.0
            
            processed = self._apply_exclusion_annotations(result, excluded, allowed)
            if not processed.get("steps"):
                processed["steps"] = self._derive_steps_from_markdown(processed.get("instructions_markdown"), allowed, excluded)
            return processed
        except json.JSONDecodeError:
            return {
                "intro": "",
                "estimated_time": "",
                "ingredients": [{"name": name, "amount": ""} for name in allowed] or [{"name": recipe_name, "amount": "적당량"}],
                "steps": self._derive_steps_from_markdown("", allowed, excluded) or [
                    {
                        "step_number": 1,
                        "title": "재료 준비",
                        "description": f"{recipe_name}에 필요한 재료를 손질합니다.",
                        "tip": "제외한 재료는 다른 재료로 대체하거나 생략하세요."
                    }
                ],
                "instructions_markdown": f"1. {recipe_name} 레시피를 준비합니다.\n\n~~제외된 재료~~ (생략)",
                "nutrition_info": {
                    "calories": 400,
                    "protein": "20g",
                    "carbs": "40g",
                    "fat": "10g",
                    "fiber": "5g",
                    "sodium": "500mg"
                },
                "total_weight_g": 250.0
            }
    
    def _apply_exclusion_annotations(
        self,
        payload: Dict[str, Any],
        excluded: Optional[List[str]],
        allowed: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        normalized = [item.strip() for item in (excluded or []) if item and item.strip()]
        allowed_list = [item.strip() for item in (allowed or []) if item and item.strip()]
        if not normalized:
            if allowed_list:
                payload["ingredients"] = [{"name": name, "amount": ""} for name in allowed_list]
            return payload
        
        def annotate_text(text: Optional[str]) -> Optional[str]:
            if not text:
                return text
            updated = text
            for keyword in normalized:
                pattern_existing = re.compile(rf"~~[^~]*{re.escape(keyword)}[^~]*~~", re.IGNORECASE)
                if pattern_existing.search(updated):
                    continue
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                updated = pattern.sub(lambda m: f"~~{m.group(0)}~~ (생략)", updated)
            return updated
        
        payload["instructions_markdown"] = annotate_text(payload.get("instructions_markdown"))
        
        steps = payload.get("steps")
        if isinstance(steps, list):
            for step in steps:
                for field in ("title", "description", "tip"):
                    if field in step:
                        step[field] = annotate_text(step.get(field))
            payload["steps"] = steps
        
        if allowed_list:
            rebuilt = []
            for item in allowed_list:
                amount = ""
                base_name = item
                rebuilt.append({
                    "name": annotate_text(base_name if base_name not in normalized else f"{base_name}"),
                    "amount": "(보유 X)" if item in normalized else amount
                })
            payload["ingredients"] = rebuilt
        else:
            ingredients = payload.get("ingredients")
            if isinstance(ingredients, list):
                for ingredient in ingredients:
                    name = ingredient.get("name") or ""
                    for keyword in normalized:
                        if keyword.lower() in name.lower():
                            amount = (ingredient.get("amount") or "").strip()
                            if "(보유 X)" not in amount:
                                ingredient["amount"] = f"{amount} (보유 X)".strip() if amount else "(보유 X)"
                            ingredient["name"] = annotate_text(name)
                            break
                payload["ingredients"] = ingredients
        
        return payload

    def _derive_steps_from_markdown(
        self,
        markdown: Optional[str],
        allowed: Optional[List[str]],
        excluded: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        if not markdown:
            return []
        matches = list(re.finditer(r'(?m)^\s*(\d+)[\.\)]\s+(.*)', markdown))
        if not matches:
            return []
        steps = []
        for idx, match in enumerate(matches):
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
            body = (match.group(2) or "").strip()
            extra = markdown[start:end].strip()
            description = "\n".join(filter(None, [body, extra]))
            steps.append({
                "step_number": idx + 1,
                "title": f"단계 {idx + 1}",
                "description": description,
                "tip": None
            })
        return steps
    
    async def evaluate_health_warning(
        self,
        user: User,
        user_request: str,
        health_warning: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """건강 경고 시 추가 확인이 필요한지 LLM에게 판단 요청"""
        history_snippets = []
        if conversation_history:
            for item in conversation_history[-6:]:
                role = item.get("role", "")
                content = item.get("content", "")
                if content:
                    history_snippets.append({"role": role, "content": content})
        history_json = json.dumps(history_snippets, ensure_ascii=False)
        
        prompt = f"""당신은 한국어 영양사입니다.
사용자의 대화 기록과 건강 경고를 참고해, 레시피를 바로 보여줄지 전에 한 번 더 확인할지 판단하세요.

- health_warning: "{health_warning}"
- user_request: "{user_request or '정보 없음'}"
- conversation_history(최신 6건): {history_json}

규칙:
1. 사용자가 이미 "그래도 진행할게", "그대로 보여줘", "상관없어" 등 경고를 인지하고 계속 원한다는 의사를 분명히 표현했다면 requires_confirmation을 false로 설정하세요.
2. 그렇지 않다면 requires_confirmation을 true로 두고, assistant_reply에 경고를 다시 친절히 설명하며 "정말 이 조합으로 진행할까요?" 같은 확인 질문을 포함하세요.
3. suggestions 배열에 사용자가 누를 수 있는 2~3개의 짧은 문장을 넣으세요. 예: ["그래도 진행할래", "다른 메뉴 추천해줘"].

JSON 형식:
{{
  "requires_confirmation": true,
  "assistant_reply": "메시지",
  "suggestions": ["...", "..."]
}}"""
        
        try:
            response = await self.json_llm.ainvoke([HumanMessage(content=prompt)])
            return json.loads(response.content)
        except Exception:
            return {
                "requires_confirmation": True,
                "assistant_reply": f"{health_warning}\n\n그래도 그대로 진행할까요?",
                "suggestions": ["그래도 진행할래", "다른 메뉴 추천해줘"]
            }
    
    def _generate_user_friendly_message(
        self,
        user_request: str,
        inferred_preference: str,
        health_warning: Optional[str],
        diseases: List[str] = None,
        user_nickname: str = "",
        has_eaten_today: bool = True,
        deficient_nutrients: List[Dict[str, any]] = None,
        excess_warnings: List[str] = None
    ) -> str:
        """
        사용자에게 보여줄 친화적 메시지 생성
        추론된 선호도를 자연스럽게 표현하고, 건강 상태를 고려한 안내를 포함
        """
        # 사용자 요청에서 음식 키워드 추출 시도
        food_keywords = []
        common_foods = ["대창", "삼겹살", "치킨", "피자", "햄버거", "라면", "떡볶이", "족발", "보쌈"]
        for food in common_foods:
            if food in user_request:
                food_keywords.append(food)
        
        # 닉네임 설정
        name_prefix = f"{user_nickname}님, " if user_nickname else ""
        
        # 메시지 구성
        message_parts = []
        
        # 사용자 요청이 실제로 있는지 확인 (빈 문자열이나 의미 없는 텍스트 제외)
        has_meaningful_request = user_request and len(user_request.strip()) > 0 and not user_request.strip().startswith("오늘")
        
        # 1. 오늘 식사 현황 안내
        if not has_eaten_today:
            message_parts.append(f"{name_prefix}오늘 아직 아무것도 드시지 않으셨네요!")
            message_parts.append("건강한 식사를 시작할 수 있도록 레시피를 추천해드릴게요! 🍳")
        elif has_meaningful_request:
            # 사용자가 실제로 음식 요청을 한 경우에만 인정
            if food_keywords:
                food_text = ", ".join(food_keywords)
                message_parts.append(f"{name_prefix}{food_text} 관련 음식을 드시고 싶으시군요!")
            else:
                # 요청 문장을 그대로 반복하지 말고 일반화된 코멘트로 응답
                message_parts.append(f"{name_prefix}말씀해주신 취향을 참고해 레시피를 찾아볼게요!")
        
        # 2. 초과 경고 안내 (칼로리/나트륨)
        # → 제거됨: 이미 별도의 빨간색 경고 메시지로 표시되므로 여기서는 언급하지 않음
        
        # 3. 부족한 영양소 안내
        if deficient_nutrients and len(deficient_nutrients) > 0:
            nutrient_names = [n['name'] for n in deficient_nutrients]
            nutrient_text = ", ".join(nutrient_names)
            message_parts.append(f"\n오늘 섭취한 영양소를 확인해보니 {nutrient_text}이(가) 부족하시네요!")
            message_parts.append("요청하신 재료에 추가로 부족한 영양소를 보완할 수 있는 재료가 들어간 레시피를 추천해드릴게요! 💚")
        
        # 4. 건강 상태 고려 안내 (질병이 있는 경우)
        if diseases and health_warning:
            disease_text = ", ".join(diseases)
            if name_prefix:
                # "홍길동님, " -> "홍길동님의 "
                name_for_health = name_prefix.replace("님, ", "님의 ")
            else:
                name_for_health = ""
            message_parts.append(f"\n또한 {name_for_health}건강을 살펴보니 {disease_text}이(가) 있으시네요!")
            message_parts.append(f"{health_warning}")
        elif health_warning:
            message_parts.append(f"\n{health_warning}")
        
        # 5. 마무리 메시지
        if not has_eaten_today or deficient_nutrients or health_warning or diseases:
            message_parts.append("\n건강을 고려한 레시피를 추천해드릴게요! 아래에서 원하시는 레시피를 선택해주세요 🍳")
        else:
            message_parts.append("\n아래에서 원하시는 레시피를 선택해주세요! 🍳")
        
        return "\n".join(message_parts)
    
    async def get_recipe_detail(
        self,
        recipe_name: str,
        user: User,
        diseases: Optional[List[str]] = None,
        allergies: Optional[List[str]] = None
    ) -> dict:
        """
        선택한 레시피의 상세 단계별 조리법을 제공
        
        Args:
            recipe_name: 선택한 레시피 이름
            user: User 객체
            diseases: 사용자 질병 목록
            allergies: 사용자 알레르기 목록
        
        Returns:
            dict: 상세 레시피 정보
        """
        health_goal_kr = {
            "loss": "체중 감량",
            "maintain": "체중 유지",
            "gain": "체중 증가"
        }.get(user.health_goal, "체중 유지")
        
        # 안전성 정보 구성
        diseases_str = ", ".join(diseases) if diseases else "없음"
        allergies_str = ", ".join(allergies) if allergies else "없음"
        
        safety_context = ""
        if diseases or allergies:
            safety_context = f"""
**🚨 [중요: 안전성 유지 및 재료 검열]**
이 사용자는 다음 건강 위험 요소를 가지고 있습니다:
- 질병: {diseases_str}
- 알레르기: {allergies_str}

**필수 지침:**
1. **[재료 검열]**: 위 질병이나 알레르기에 해로운 재료가 원래 레시피에 포함되어 있다면, **절대 재료 목록이나 조리 과정에 포함시키지 마세요.**
2. **[안전 대체]**: 만약 레시피 이름(예: '{recipe_name}')이 위험한 재료를 암시하더라도, **무조건 안전한 대체재(버섯, 해산물, 두부 등)로 바뀐 버전**의 조리법을 작성하세요.
   - 예: '대창 전골' -> 대창을 100% 제거하고 식감이 비슷한 '새송이 버섯'으로 대체하여 조리법 작성.
3. **[소스/육수 주의]**: 알레르기 유발 성분은 소스나 육수, 시판 제품에도 포함되어서는 안 됩니다.
"""

        prompt = f"""당신은 요리 전문가입니다. "{recipe_name}" 레시피의 상세한 단계별 조리법을 제공해주세요.
{safety_context}

**사용자 정보:**
- 건강 목표: {health_goal_kr}

**지시사항:**
1. **[필수] 모든 재료의 양과 조리법은 반드시 '1인분'을 기준으로 작성하세요.** (예: 밥 2공기 X -> 밥 1공기 O)
2. 레시피 소개를 작성하세요.
3. 필요한 재료 목록을 작성하세요.
4. 조리 과정을 5~8단계로 나누어 상세하게 설명하세요.
5. 각 단계마다 제목, 상세 설명, 팁(선택사항)을 포함하세요.
6. 영양 정보를 제공하세요.

**응답 형식 (JSON):**
{{
  "recipe_name": "{recipe_name}",
  "intro": "레시피 소개 (2-3문장)",
  "estimated_time": "30분",
  "ingredients": [
    {{"name": "재료명", "amount": "양"}},
    ...
  ],
  "steps": [
    {{
      "step_number": 1,
      "title": "재료 준비",
      "description": "상세한 설명",
      "tip": "팁 (선택사항)",
      "image_suggestion": "이 단계를 나타내는 이미지 설명"
    }},
    ...
  ],
  "nutrition_info": {{
    "calories": 450,
    "protein": "35g",
    "carbs": "45g",
    "fat": "12g",
    "fiber": "8g",
    "sodium": "800mg"
  }},
  "total_weight_g": 350
}}

JSON 형식만 반환하세요."""

        cached = self._get_prefetched_detail(user, recipe_name)
        if cached:
            return cached

        print(f"🤖 LangChain LLM에게 '{recipe_name}' 레시피 상세 요청 중...")
        
        chat_messages = [
            SystemMessage(content="당신은 전문 요리사입니다. JSON 형식으로만 응답합니다."),
            HumanMessage(content=prompt)
        ]
        response = await self.json_llm.ainvoke(chat_messages)
        gpt_response = response.content
        print(f"✅ 레시피 상세 정보 수신 완료")
        
        # JSON 파싱
        try:
            result = json.loads(gpt_response)
            result["total_steps"] = len(result.get("steps", []))
            
            # 총 중량 기본값 처리
            if "total_weight_g" not in result:
                result["total_weight_g"] = 250.0
            
            self._store_prefetched_detail(user, recipe_name, result)
            return result
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {e}")
            # 파싱 실패 시 기본 레시피 반환
            fallback = self._get_fallback_recipe(recipe_name)
            self._store_prefetched_detail(user, recipe_name, fallback)
            return fallback
    
    def _get_fallback_recipe(self, recipe_name: str) -> dict:
        """JSON 파싱 실패 시 기본 레시피 반환"""
        return {
            "recipe_name": recipe_name,
            "intro": f"{recipe_name}는 건강하고 맛있는 요리입니다.",
            "estimated_time": "30분",
            "total_steps": 5,
            "ingredients": [
                {"name": "주재료", "amount": "적당량"},
                {"name": "양념", "amount": "적당량"}
            ],
            "steps": [
                {
                    "step_number": 1,
                    "title": "재료 준비",
                    "description": "필요한 재료들을 준비합니다.",
                    "tip": "신선한 재료를 사용하세요.",
                    "image_suggestion": "준비된 재료들"
                },
                {
                    "step_number": 2,
                    "title": "조리 시작",
                    "description": "재료를 조리합니다.",
                    "tip": "중불에서 천천히 조리하세요.",
                    "image_suggestion": "조리 중인 모습"
                },
                {
                    "step_number": 3,
                    "title": "간 맞추기",
                    "description": "기호에 맞게 간을 맞춥니다.",
                    "tip": "소금은 조금씩 넣으며 맛을 봅니다.",
                    "image_suggestion": "양념을 추가하는 모습"
                },
                {
                    "step_number": 4,
                    "title": "마무리",
                    "description": "요리를 마무리합니다.",
                    "tip": "불을 끄기 전에 한 번 더 간을 확인하세요.",
                    "image_suggestion": "완성된 요리"
                },
                {
                    "step_number": 5,
                    "title": "플레이팅",
                    "description": "접시에 예쁘게 담아냅니다.",
                    "tip": "허브나 고명으로 장식하면 더 좋습니다.",
                    "image_suggestion": "플레이팅된 완성 요리"
                }
            ],
            "nutrition_info": {
                "calories": 400,
                "protein": "30g",
                "carbs": "40g",
                "fat": "15g",
                "fiber": "5g",
                "sodium": "800mg"
            },
            "total_weight_g": 250.0
        }

    def _store_prefetched_detail(self, user: User, recipe_name: str, payload: Dict[str, Any]) -> None:
        key = self._detail_cache_key(user, recipe_name)
        if not key:
            return
        self._prefetched_detail_cache[key] = {
            "expires_at": time.time() + DETAIL_CACHE_TTL_SECONDS,
            "data": payload,
        }

    def _get_prefetched_detail(self, user: User, recipe_name: str) -> Optional[Dict[str, Any]]:
        key = self._detail_cache_key(user, recipe_name)
        if not key:
            return None
        entry = self._prefetched_detail_cache.get(key)
        if not entry:
            return None
        if entry["expires_at"] < time.time():
            self._prefetched_detail_cache.pop(key, None)
            return None
        return entry["data"]

    def _detail_cache_key(self, user: User, recipe_name: str) -> Optional[tuple[int, str]]:
        if not user or not getattr(user, "user_id", None) or not recipe_name:
            return None
        return (user.user_id, recipe_name.strip().lower())

    @staticmethod
    def _silence_background_task(task: asyncio.Task) -> None:
        try:
            task.result()
        except Exception:
            pass


# 싱글톤 인스턴스
_recipe_recommendation_service: Optional[RecipeRecommendationService] = None


def get_recipe_recommendation_service() -> RecipeRecommendationService:
    """RecipeRecommendationService 싱글톤 인스턴스 반환"""
    global _recipe_recommendation_service
    if _recipe_recommendation_service is None:
        _recipe_recommendation_service = RecipeRecommendationService()
    return _recipe_recommendation_service
