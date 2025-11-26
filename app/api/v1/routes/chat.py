import json
import re
import uuid
from datetime import datetime
from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.api.v1.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.core.config import get_settings
from app.db.models import ChatHistory, Conversation, User
from app.db.redis_session import get_redis_client
from app.db.session import get_session
from app.services.chat_service import ChatService
from app.services.langchain_agent import AgentContext, get_langchain_agent_factory
from app.services.recipe_recommendation_service import get_recipe_recommendation_service
from app.services.user_context_cache import get_or_build_user_context, refresh_user_context

router = APIRouter(prefix="/chat", tags=["Chat"])

settings = get_settings()


@lru_cache
def get_clarify_llm() -> ChatOpenAI:
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured.")
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model="gpt-4o-mini",
        temperature=0.4,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


CLARIFY_CONFIRMATION_MESSAGE = "레시피를 추천해드릴까요? 진행을 원하시면 '네' 또는 '응'이라고 답해주세요."

RECIPE_NEGATION_KEYWORDS = [
    "레시피 말고",
    "레시피 필요 없어",
    "레시피 필요없어",
    "아니",
    "아니요",
    "아니오",
    "싫어",
    "됐어",
    "괜찮아",
]


RECIPE_REQUEST_PATTERNS = [
    re.compile(
        r"(레시피|조리법|요리법|만드는\s?법|만드는\s?방법).*(알려|추천|보여|찾아|줄|해줘|부탁|가능|가르쳐)"
    ),
    re.compile(
        r"(알려|추천|보여|찾아|줄|해줘|부탁|가능|가르쳐).*(레시피|조리법|요리법|만드는\s?법|만드는\s?방법)"
    ),
    re.compile(r"(어떻게|방법).*(만들|요리해)"),
    re.compile(r"(레시피|조리법|만드는\s?법).*(추천해줘|알려줘|보여줘|찾아줘)"),
]


CLARIFY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """너는 친근한 한국어 영양사 챗봇이야.
- 최근 대화 요약: {summary}
- 항상 JSON 객체만 출력해야 해. 필드는 response_id, action_type, message, suggestions, needs_tool_call.
- 사용자가 잡담이나 영양/건강 관련 질문을 하면 자연스럽게 답하고, 필요한 경우 부드럽게 추가 정보를 물어봐.
- 사용자가 “아니”, “싫어” 등 부정 표현을 쓰면 needs_tool_call은 false로 유지하고 대화형 텍스트로 응답해.
- "레시피 추천해줘", "만드는 법 알려줘", "~ 어떻게 만들어?"처럼 명확하게 추천/조리법을 요청할 때만 needs_tool_call을 true로 하고, message에 확인 문구를 넣어.
- needs_tool_call이 true일 때만 message에 "레시피를 추천해드릴까요? 진행을 원하시면 '네' 또는 '응'이라고 답해주세요."를 포함해.
- needs_tool_call이 false일 때는 확인 문구나 과한 추가 질문 없이 자연스러운 대화/질문/정보만 message에 담아.
- 모호한 질문이나 정보 탐색, 부정 표현은 needs_tool_call=false로 유지해.
- suggestions에는 사용자가 바로 클릭해서 보낼 수 있는 짧은 발화 예시 2~3개(예: "매콤한 레시피 추천해줘", "다른 질문 있어")만 넣어. 챗봇이 던지는 질문은 message에만 넣어.
- action_type은 항상 TEXT_ONLY로 고정해.
""",
        ),
        ("human", "{user_message}"),
    ]
)


def _normalize_text_for_intent(text: str) -> str:
    return (text or "").strip().lower()


def _matches_recipe_request(text: str) -> bool:
    normalized = _normalize_text_for_intent(text)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in RECIPE_REQUEST_PATTERNS)


def _evaluate_recipe_intent_flags(user_message: str) -> tuple[bool, bool]:
    normalized = _normalize_text_for_intent(user_message)
    if not normalized:
        return False, False
    has_negation = any(keyword in normalized for keyword in RECIPE_NEGATION_KEYWORDS)
    if has_negation:
        return False, True
    has_recipe_request = _matches_recipe_request(normalized)
    return has_recipe_request, False


async def _generate_clarify_payload(summary: str, user_message: str) -> dict:
    clarify_llm = get_clarify_llm()
    messages = CLARIFY_PROMPT.format_messages(
        summary=summary or "이전 대화 없음",
        user_message=user_message,
    )
    try:
        response = await clarify_llm.ainvoke(messages)
        payload = json.loads(response.content)
    except Exception:
        payload = {}

    payload.setdefault("response_id", f"clarify-{uuid.uuid4()}")
    payload.setdefault("action_type", "TEXT_ONLY")
    payload.setdefault("message", "사용자님의 요청을 이해했어요. 더 자세히 말씀해주실까요?")
    suggestions = payload.get("suggestions")
    if not isinstance(suggestions, list) or len(suggestions) == 0:
        payload["suggestions"] = ["레시피 추천해줘", "다른 질문 있어"]
    payload.setdefault("needs_tool_call", False)
    return payload


@router.get("/context")
async def refresh_chat_context(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
):
    """Recommend 탭 진입 시 최신 사용자 컨텍스트를 강제로 갱신."""
    ctx = await refresh_user_context(db, current_user.user_id)
    return {
        "success": True,
        "message": "컨텍스트를 새로고침했습니다.",
        "data": {
            "diseases": ctx.diseases,
            "allergies": ctx.allergies,
            "has_eaten_today": ctx.has_eaten_today,
            "last_refreshed": ctx.last_refreshed.isoformat(),
        },
    }


@router.post("/prewarm")
async def prewarm_chat_agent(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Recommend 탭 진입 직후 AI가 기본 정보를 읽어들이도록 워밍업."""
    cached_context = await get_or_build_user_context(db, current_user.user_id)
    conversation = await db.get(Conversation, f"prewarm-{current_user.user_id}")
    agent_context = AgentContext(
        user=current_user,
        session=db,
        conversation_summary=conversation.sum_chat if conversation else None,
        diseases=cached_context.diseases,
        allergies=cached_context.allergies,
        has_eaten_today=cached_context.has_eaten_today,
    )
    agent_factory = get_langchain_agent_factory()
    agent_executor = await agent_factory.create_executor(context=agent_context)
    await agent_executor.ainvoke({"input": "사용자 정보를 준비하고 다음 질문을 받을 준비를 하세요."})
    return {"success": True, "message": "에이전트 워밍업 완료"}


@router.post("/", response_model=ChatMessageResponse)
async def handle_chat_message(
    request: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
    redis_client = Depends(get_redis_client),
):
    """
    Handles incoming chat messages from users.
    - Manages conversation sessions and triggers summarization.
    - Gets a response from the LangChain agent.
    - Saves conversation history.
    """
    chat_service = ChatService(redis_client=redis_client, db_session=db)

    previous_session_id = await chat_service.get_previous_session_id_and_update(
        user_id=current_user.user_id, current_session_id=request.session_id
    )

    if previous_session_id and previous_session_id != request.session_id:
        background_tasks.add_task(
            chat_service.summarize_conversation_if_needed, previous_session_id
        )

    cached_context = await get_or_build_user_context(db, current_user.user_id)
    diseases = cached_context.diseases
    allergies = cached_context.allergies
    has_eaten_today = cached_context.has_eaten_today

    conversation = await db.get(Conversation, request.session_id)
    is_new_conversation = conversation is None

    conversation_summary = ""
    if is_new_conversation:
        summary_stmt = (
            select(Conversation.sum_chat)
            .where(
                Conversation.user_id == current_user.user_id,
                Conversation.sum_chat.isnot(None),
            )
            .order_by(Conversation.last_message_summarized_at.desc())
            .limit(1)
        )
        summary_result = await db.execute(summary_stmt)
        latest_summary = summary_result.scalar_one_or_none()
        if latest_summary:
            conversation_summary = latest_summary
    elif conversation and conversation.sum_chat:
        conversation_summary = conversation.sum_chat

    agent_context = AgentContext(
        user=current_user,
        session=db,
        conversation_summary=conversation_summary,
        diseases=diseases,
        allergies=allergies,
        has_eaten_today=has_eaten_today,
    )

    mode = (request.mode or "clarify").lower()
    ai_response_payload: str
    display_text: str
    needs_tool_call_flag = False

    def _normalize_agent_output(raw_text: str) -> tuple[str, str]:
        """ensure frontend always receives valid JSON payload"""
        safe_text = (raw_text or "").strip()
        if not safe_text:
            safe_text = "죄송해요, 답변을 만들지 못했어요."
        try:
            json.loads(safe_text)
            return safe_text, safe_text
        except json.JSONDecodeError:
            fallback = {
                "response_id": f"fallback-{uuid.uuid4()}",
                "action_type": "TEXT_ONLY",
                "message": safe_text,
                "suggestions": ["다시 시도할래", "다른 질문 할게"],
                "data": None,
            }
            return json.dumps(fallback, ensure_ascii=False), safe_text

    async def _build_recipe_fallback_response() -> tuple[str, str] | None:
        try:
            if len(request.message.strip()) < 4:
                fallback_payload = {
                    "response_id": f"clarify-{uuid.uuid4()}",
                    "action_type": "TEXT_ONLY",
                    "message": (
                        "어떤 레시피가 궁금하신가요? 식재료나 끼니를 알려주시면 도와드릴게요.\n"
                        "추천을 원하시면 '네' 또는 '응'이라고 답해주세요."
                    ),
                    "suggestions": ["닭가슴살 요리 알려줘", "아침 메뉴 추천해줘"],
                    "data": None,
                }
                return json.dumps(fallback_payload, ensure_ascii=False), fallback_payload["message"]

            recipe_service = get_recipe_recommendation_service()
            fallback = await recipe_service.get_recipe_recommendations(
                user=current_user,
                user_request=request.message,
                diseases=diseases,
                allergies=allergies,
                has_eaten_today=has_eaten_today,
            )
            response_payload = {
                "response_id": f"fallback-{uuid.uuid4()}",
                "action_type": "RECOMMENDATION_RESULT",
                "message": fallback.get("user_friendly_message") or "레시피를 찾아봤어요!",
                "data": {
                    "recipes": fallback.get("recommendations"),
                    "health_warning": fallback.get("health_warning"),
                    "inferred_preference": fallback.get("inferred_preference"),
                    "user_friendly_message": fallback.get("user_friendly_message"),
                },
                "suggestions": ["재료 확인해줘", "다른 메뉴 추천해줘"],
            }
            return json.dumps(response_payload, ensure_ascii=False), response_payload["message"]
        except Exception as exc:  # pragma: no cover
            print(f"⚠️ 레시피 폴백 생성 실패: {exc}")
            return None

    if mode == "clarify":
        force_tool_call, force_tool_block = _evaluate_recipe_intent_flags(request.message)
        clarify_payload = await _generate_clarify_payload(conversation_summary, request.message)

        if force_tool_block:
            clarify_payload["needs_tool_call"] = False
            message_text = clarify_payload.get("message", "")
            if CLARIFY_CONFIRMATION_MESSAGE in message_text:
                clarify_payload["message"] = "알겠습니다. 다른 요청이 있으면 말씀해주세요!"
        elif force_tool_call:
            clarify_payload["needs_tool_call"] = True
            clarify_payload["message"] = CLARIFY_CONFIRMATION_MESSAGE

        needs_tool_call_flag = bool(clarify_payload.get("needs_tool_call"))
        ai_response_payload = json.dumps(clarify_payload, ensure_ascii=False)
        display_text = clarify_payload.get("message", "")
    else:
        agent_factory = get_langchain_agent_factory()
        agent_executor = await agent_factory.create_executor(context=agent_context)

        ai_response = await agent_executor.ainvoke({"input": request.message})
        ai_response_text = ai_response.get("output", "죄송해요, 답변을 만들지 못했어요.")

        fallback_override = None
        if "iteration limit" in ai_response_text.lower():
            fallback_override = await _build_recipe_fallback_response()

        if fallback_override:
            ai_response_payload, display_text = fallback_override
        else:
            ai_response_payload, display_text = _normalize_agent_output(ai_response_text)

    if is_new_conversation:
        conversation = Conversation(
            session_id=request.session_id,
            user_id=current_user.user_id,
            all_chat="",
            sum_chat=conversation_summary,
            last_message_summarized_at=datetime.utcnow(),
        )
        db.add(conversation)

    new_turn = f"Human: {request.message}\nAI: {display_text}\n\n"
    conversation.all_chat = (conversation.all_chat or "") + new_turn
    conversation.last_message_timestamp = datetime.utcnow()

    db.add_all(
        [
            ChatHistory(
                user_id=current_user.user_id,
                session_id=request.session_id,
                message_type="human",
                content=request.message,
            ),
            ChatHistory(
                user_id=current_user.user_id,
                session_id=request.session_id,
                message_type="ai",
                content=display_text,
            ),
        ]
    )

    await db.commit()

    if not redis_client:
        background_tasks.add_task(
            chat_service.summarize_conversation_if_needed, request.session_id
        )

    return ChatMessageResponse(
        session_id=request.session_id,
        response=ai_response_payload,
        needs_tool_call=needs_tool_call_flag,
    )
