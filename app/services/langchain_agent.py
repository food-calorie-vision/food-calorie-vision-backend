"""LangChain 기반 에이전트 팩토리

이 모듈은 단일 OpenAI API 키를 사용하는 LangChain AgentExecutor를 생성해
각 LLM 기반 서비스(diet, recipe, food matching, vision)를 통합적으로 호출한다.
"""

from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, cast

from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationSummaryBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User
from app.db.models_food_nutrients import FoodNutrient
from app.db.models_user_contributed import UserContributedFood
from app.services.diet_recommendation_service import DietRecommendationService
from app.services.food_matching_service import FoodMatchingService
from app.services.gpt_vision_service import GPTVisionService
from app.services.recipe_recommendation_service import RecipeRecommendationService

settings = get_settings()


@dataclass
class AgentContext:
    """에이전트 생성 시 필요한 컨텍스트."""

    user: Optional[User] = None
    session: Optional[AsyncSession] = None
    diseases: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    conversation_summary: Optional[str] = None
    has_eaten_today: Optional[bool] = None
    deficient_nutrients: Optional[List[Dict[str, Any]]] = None
    excess_warnings: Optional[List[str]] = None
    meal_type: Optional[str] = None


class DietPlanTool(BaseTool):
    """DietRecommendationService를 호출하는 LangChain 도구."""

    name: str = "diet_plan_tool"
    description: str = (
        "사용자의 건강 정보(나이, 성별, 체중, 건강목표)를 기반으로 하루 식단 계획을 생성합니다. "
        "입력은 사용자의 자유로운 요청 문장이어야 하며, 반환값은 JSON 문자열입니다."
    )
    service: DietRecommendationService
    user: User

    def _run(self, query: str) -> str:
        """Use the tool."""
        return asyncio.get_event_loop().run_until_complete(self._arun(query))

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        result = await self.service.generate_diet_plan_async(user=self.user, prompt=query)
        return json.dumps(result, ensure_ascii=False)


class RecipeRecommendationTool(BaseTool):
    """RecipeRecommendationService를 호출하는 도구."""

    name: str = "recipe_recommendation_tool"
    description: str = (
        "사용자의 건강 상태, 기저질환, 선호도를 고려해 레시피 3개를 추천합니다. "
        "입력은 사용자의 요청 문장 혹은 JSON({\"prompt\": \"...\", \"meal_type\": \"lunch\"}) 형태를 지원합니다."
    )
    service: RecipeRecommendationService
    user: User
    diseases: List[str] = []
    allergies: List[str] = []
    has_eaten_today: bool = True
    deficient_nutrients: List[Dict[str, Any]] = []
    excess_warnings: List[str] = []
    meal_type: Optional[str] = None

    def _run(self, query: str) -> str:
        """Use the tool."""
        return asyncio.get_event_loop().run_until_complete(self._arun(query))

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        # 쿼리가 JSON 형태일 수 있으므로 파싱 시도
        try:
            params = json.loads(query)
            prompt = params.get("prompt", "")
            meal_type = params.get("meal_type")
        except json.JSONDecodeError:
            prompt = query
            meal_type = self.meal_type

        result = await self.service.recommend_recipes_async(
            prompt=prompt,
            user=self.user,
            diseases=self.diseases,
            allergies=self.allergies,
            has_eaten_today=self.has_eaten_today,
            deficient_nutrients=self.deficient_nutrients,
            excess_warnings=self.excess_warnings,
            meal_type=meal_type,
        )
        return json.dumps([r.dict() for r in result], ensure_ascii=False)


class FoodMatchingTool(BaseTool):
    """FoodMatchingService를 호출하는 도구."""

    name: str = "food_matching_tool"
    description: str = (
        "추천 음식명을 식약처 DB 또는 사용자 기여 음식과 매칭합니다. "
        "입력은 JSON 문자열이어야 하며 예시는 "
        '{"food_name": "닭가슴살 샐러드", "ingredients": ["닭가슴살", "양상추"], "food_class_hint": "샐러드"}. '
        "결과는 매칭된 음식 정보 JSON 문자열입니다."
    )
    service: FoodMatchingService
    session: AsyncSession
    user_id: int

    def _run(self, query: str) -> str:
        """Use the tool."""
        return asyncio.get_event_loop().run_until_complete(self._arun(query))

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        try:
            params = json.loads(query)
            food_name = params["food_name"]
            ingredients = params.get("ingredients")
            food_class_hint = params.get("food_class_hint")
        except (json.JSONDecodeError, KeyError) as e:
            return f"Error: Invalid JSON input for FoodMatchingTool. {e}"

        matched_food = await self.service.match_food_item_async(
            session=self.session,
            user_id=self.user_id,
            food_name=food_name,
            ingredients=ingredients,
            food_class_hint=food_class_hint,
        )
        if isinstance(matched_food, (FoodNutrient, UserContributedFood)):
            return json.dumps(matched_food.to_dict(), ensure_ascii=False)
        return json.dumps(
            {"error": "Food not found or could not be matched."}, ensure_ascii=False
        )


class VisionAnalysisTool(BaseTool):
    """GPTVisionService를 호출하는 도구."""

    name: str = "vision_analysis_tool"
    description: str = (
        "YOLO 감지 결과와 base64 인코딩된 이미지를 받아 GPT-Vision으로 세부 분석합니다. "
        '입력 예시는 {"image_base64": "...", "yolo_detection": {...}} 입니다.'
    )
    service: GPTVisionService

    def _run(self, query: str) -> str:
        """Use the tool."""
        return asyncio.get_event_loop().run_until_complete(self._arun(query))

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        try:
            params = json.loads(query)
            image_base64 = params["image_base64"]
            yolo_detection = params["yolo_detection"]
        except (json.JSONDecodeError, KeyError) as e:
            return f"Error: Invalid JSON input for VisionAnalysisTool. {e}"

        # 이미지 데이터는 매우 크므로, base64 문자열 자체는 반환하지 않는다.
        analysis_result = await self.service.analyze_image_async(
            image_base64=image_base64, yolo_detection=yolo_detection
        )
        return analysis_result


class LangChainAgentFactory:
    """LangChain AgentExecutor 생성기."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.4):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않아 LangChain 에이전트를 초기화할 수 없습니다.")

        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=model,
            temperature=temperature,
        )

    async def create_executor(self, context: AgentContext) -> AgentExecutor:
        tools = self._build_tools(context)
        prompt = self._build_prompt(context)
        agent = create_react_agent(self.llm, tools, prompt)

        memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=1500,
        )

        if context.conversation_summary:
            memory.save_context(
                {"input": "대화 요약"},
                {"output": context.conversation_summary},
            )

        return AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            handle_parsing_errors=True,
            max_iterations=8,
            max_execution_time=45,
        )

    def _build_tools(self, context: AgentContext) -> List[BaseTool]:
        tools: List[BaseTool] = []
        if context.user:
            diet_service = DietRecommendationService()
            tools.append(DietPlanTool(service=diet_service, user=context.user))

            recipe_service = RecipeRecommendationService()
            tools.append(
                RecipeRecommendationTool(
                    service=recipe_service,
                    user=context.user,
                    diseases=context.diseases or [],
                    allergies=context.allergies or [],
                    has_eaten_today=context.has_eaten_today if context.has_eaten_today is not None else True,
                    deficient_nutrients=context.deficient_nutrients or [],
                    excess_warnings=context.excess_warnings or [],
                    meal_type=context.meal_type,
                )
            )

        if context.session and context.user:
            food_matching_service = FoodMatchingService()
            tools.append(
                FoodMatchingTool(
                    service=food_matching_service,
                    session=context.session,
                    user_id=context.user.user_id,
                )
            )

        vision_service = GPTVisionService()
        tools.append(VisionAnalysisTool(service=vision_service))
        return tools

    def _build_prompt(self, context: AgentContext) -> ChatPromptTemplate:
        diseases_text = ", ".join(context.diseases or []) or "없음"
        allergies_text = ", ".join(context.allergies or []) or "없음"
        health_goal = context.user.health_goal if context.user and context.user.health_goal else "maintain"
        summary_text = context.conversation_summary or "이전 요약 없음"

        system_template = f"""
당신은 Food Calorie Vision의 영양사 챗봇입니다.
- 항상 사용자의 건강 목표({health_goal})와 기저질환({diseases_text})/알레르기({allergies_text})를 고려하세요.
- 먼저 간단한 대화를 통해 사용자가 무엇을 원하는지 명확히 파악하세요. 질문이 모호하면 Clarification 질문을 던지고, 빠르게 텍스트로 응답합니다.
- 사용 가능한 도구 목록:
{{tools}}
- 반드시 사용자가 명시적으로 추천/레시피를 요청하거나 끼니 등 조건이 확정된 이후에만 도구({{tool_names}})를 호출하세요.
- 임의로 도구를 호출하지 말고, 확인되지 않은 상태에서는 `TEXT_ONLY` 방식으로 답변하세요.
- 건강 경고나 식단 제안은 사용자가 동의했을 때만 제공합니다.
- 중요 대화 요약: {summary_text}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                ("assistant", "{agent_scratchpad}"),
            ]
        )
        return prompt


@lru_cache
def get_langchain_agent_factory() -> LangChainAgentFactory:
    """싱글톤 형태의 팩토리를 제공."""
    return LangChainAgentFactory()
