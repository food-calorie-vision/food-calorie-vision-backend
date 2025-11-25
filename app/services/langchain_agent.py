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

    name = "diet_plan_tool"
    description = (
        "사용자의 건강 정보(나이, 성별, 체중, 건강목표)를 기반으로 하루 식단 계획을 생성합니다. "
        "입력은 사용자의 자유로운 요청 문장이어야 하며, 반환값은 JSON 문자열입니다."
    )

    def __init__(self, service: DietRecommendationService, user: User):
        super().__init__()
        self.service = service
        self.user = user

    def _run(self, user_request: str) -> str:
        raise NotImplementedError("diet_plan_tool은 비동기 호출만 지원합니다.")

    async def _arun(self, user_request: str) -> str:
        result = await self.service.generate_diet_plan(
            user=self.user,
            user_request=user_request or "",
        )
        return json.dumps(result, ensure_ascii=False)


class RecipeRecommendationTool(BaseTool):
    """RecipeRecommendationService를 호출하는 도구."""

    name = "recipe_recommendation_tool"
    description = (
        "사용자의 건강 상태, 기저질환, 선호도를 고려해 레시피 3개를 추천합니다. "
        "입력은 사용자의 요청 문장 혹은 JSON({\"prompt\": \"...\", \"meal_type\": \"lunch\"}) 형태를 지원합니다."
    )

    def __init__(
        self,
        service: RecipeRecommendationService,
        user: User,
        diseases: Optional[List[str]] = None,
        allergies: Optional[List[str]] = None,
        has_eaten_today: Optional[bool] = None,
        deficient_nutrients: Optional[List[Dict[str, Any]]] = None,
        excess_warnings: Optional[List[str]] = None,
        meal_type: Optional[str] = None,
    ):
        super().__init__()
        self.service = service
        self.user = user
        self.diseases = diseases or []
        self.allergies = allergies or []
        self.has_eaten_today = has_eaten_today if has_eaten_today is not None else True
        self.deficient_nutrients = deficient_nutrients or []
        self.excess_warnings = excess_warnings or []
        self.meal_type = meal_type

    def _run(self, tool_input: str) -> str:
        raise NotImplementedError("recipe_recommendation_tool은 비동기 호출만 지원합니다.")

    async def _arun(self, tool_input: str | Dict[str, Any]) -> str:
        prompt_text = ""
        meal_type = self.meal_type

        if isinstance(tool_input, dict):
            prompt_text = tool_input.get("prompt", "")
            meal_type = tool_input.get("meal_type", meal_type)
        else:
            prompt_text = tool_input

        result = await self.service.get_recipe_recommendations(
            user=self.user,
            user_request=prompt_text,
            llm_user_intent=prompt_text,
            diseases=self.diseases,
            allergies=self.allergies,
            has_eaten_today=self.has_eaten_today,
            deficient_nutrients=self.deficient_nutrients,
            excess_warnings=self.excess_warnings,
            meal_type=meal_type,
        )
        return json.dumps(result, ensure_ascii=False)


class FoodMatchingTool(BaseTool):
    """FoodMatchingService를 호출하는 도구."""

    name = "food_matching_tool"
    description = (
        "추천 음식명을 식약처 DB 또는 사용자 기여 음식과 매칭합니다. "
        "입력은 JSON 문자열이어야 하며 예시는 "
        '{"food_name": "닭가슴살 샐러드", "ingredients": ["닭가슴살", "양상추"], "food_class_hint": "샐러드"}. '
        "결과는 매칭된 음식 정보 JSON 문자열입니다."
    )

    def __init__(self, service: FoodMatchingService, session: AsyncSession, user_id: int):
        super().__init__()
        self.service = service
        self.session = session
        self.user_id = user_id

    def _run(self, tool_input: str) -> str:
        raise NotImplementedError("food_matching_tool은 비동기 호출만 지원합니다.")

    async def _arun(self, tool_input: str | Dict[str, Any]) -> str:
        if isinstance(tool_input, str):
            payload = json.loads(tool_input)
        else:
            payload = tool_input

        match = await self.service.match_food_to_db(
            session=self.session,
            food_name=payload.get("food_name"),
            ingredients=payload.get("ingredients", []),
            food_class_hint=payload.get("food_class_hint"),
            user_id=self.user_id,
        )

        if not match:
            return json.dumps({"match": None, "message": "No matching food was found."}, ensure_ascii=False)

        serialized: Dict[str, Any]
        if isinstance(match, FoodNutrient):
            serialized = {
                "source": "food_nutrients",
                "food_id": match.food_id,
                "name": match.nutrient_name,
                "food_class1": match.food_class1,
                "food_class2": match.food_class2,
            }
        else:
            match = cast(UserContributedFood, match)
            serialized = {
                "source": "user_contributed_foods",
                "food_id": match.food_id,
                "name": match.food_name,
                "ingredients": match.ingredients,
                "food_class1": match.food_class1,
                "food_class2": match.food_class2,
            }

        return json.dumps({"match": serialized}, ensure_ascii=False)


class VisionAnalysisTool(BaseTool):
    """GPTVisionService를 호출하는 도구."""

    name = "vision_analysis_tool"
    description = (
        "YOLO 감지 결과와 base64 인코딩된 이미지를 받아 GPT-Vision으로 세부 분석합니다. "
        '입력 예시는 {"image_base64": "...", "yolo_detection": {...}} 입니다.'
    )

    def __init__(self, service: GPTVisionService):
        super().__init__()
        self.service = service

    def _run(self, tool_input: str) -> str:
        raise NotImplementedError("vision_analysis_tool은 비동기 호출만 지원합니다.")

    async def _arun(self, tool_input: str | Dict[str, Any]) -> str:
        if isinstance(tool_input, str):
            payload = json.loads(tool_input)
        else:
            payload = tool_input

        image_base64 = payload.get("image_base64")
        if not image_base64:
            return json.dumps({"error": "image_base64 is required"}, ensure_ascii=False)

        image_bytes = base64.b64decode(image_base64)
        yolo_detection = payload.get("yolo_detection", {})

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            self.service.analyze_food_with_detection,
            image_bytes,
            yolo_detection,
        )
        return json.dumps(result, ensure_ascii=False)


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
        )

    def _build_tools(self, context: AgentContext) -> List[BaseTool]:
        tools: List[BaseTool] = []
        if context.user:
            diet_service = DietRecommendationService()
            tools.append(DietPlanTool(diet_service, context.user))

            recipe_service = RecipeRecommendationService()
            tools.append(
                RecipeRecommendationTool(
                    recipe_service,
                    context.user,
                    diseases=context.diseases,
                    allergies=context.allergies,
                    has_eaten_today=context.has_eaten_today,
                    deficient_nutrients=context.deficient_nutrients,
                    excess_warnings=context.excess_warnings,
                    meal_type=context.meal_type,
                )
            )

        if context.session and context.user:
            food_matching_service = FoodMatchingService()
            tools.append(FoodMatchingTool(food_matching_service, context.session, context.user.user_id))

        vision_service = GPTVisionService()
        tools.append(VisionAnalysisTool(vision_service))
        return tools

    def _build_prompt(self, context: AgentContext) -> ChatPromptTemplate:
        diseases_text = ", ".join(context.diseases or []) or "없음"
        allergies_text = ", ".join(context.allergies or []) or "없음"
        health_goal = context.user.health_goal if context.user and context.user.health_goal else "maintain"
        summary_text = context.conversation_summary or "이전 요약 없음"

        system_template = f"""
당신은 Food Calorie Vision의 영양사 챗봇입니다.
- 항상 사용자의 건강 목표({health_goal})와 기저질환({diseases_text})/알레르기({allergies_text})를 고려하세요.
- 필요한 경우 등록된 도구를 호출하여 최신 데이터를 확보하세요.
- 중요 대화 요약: {summary_text}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )
        return prompt


@lru_cache
def get_langchain_agent_factory() -> LangChainAgentFactory:
    """싱글톤 형태의 팩토리를 제공."""
    return LangChainAgentFactory()
