"""챗봇 관련 라우트"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.api.v1.schemas.chat import ChatData, ChatRequest
from app.api.v1.schemas.common import ApiResponse
from app.services import chat_service
from app.utils.session import get_current_user_id

router = APIRouter()


def _generate_chat_response(message: str, selected_meal: dict | None) -> str:
    """챗봇 응답 생성 (목 구현)"""
    # TODO: 실제 LLM 모델로 대체
    input_lower = message.lower()

    if "칼로리" in input_lower or "영양" in input_lower:
        if selected_meal and selected_meal.get("calories") and selected_meal.get("nutrients"):
            nutrients = selected_meal["nutrients"]
            return (
                f"{selected_meal['name']}의 칼로리는 {selected_meal['calories']}kcal입니다. "
                f"주요 영양소는 단백질 {nutrients['protein']}g, 탄수화물 {nutrients['carbs']}g, "
                f"지방 {nutrients['fat']}g, 나트륨 {nutrients['sodium']}mg 입니다."
            )
        return "선택된 음식에 대한 칼로리 및 영양 정보가 없습니다."

    if "만드는 법" in input_lower or "레시피" in input_lower:
        meal_name = selected_meal.get("name") if selected_meal else "이 음식"
        return f"{meal_name}의 레시피는 '레시피 검색' 페이지에서 찾아보실 수 있습니다."

    if "사진" in input_lower or "이미지" in input_lower:
        return "사진을 보내주시면 AI가 분석하여 답변해 드릴 수 있습니다."

    if "안녕" in input_lower or "hello" in input_lower or "hi" in input_lower:
        return "안녕하세요! 음식과 영양에 대해 무엇이든 물어보세요."

    meal_name = selected_meal.get("name") if selected_meal else "음식"
    return f"선택하신 {meal_name}에 대해 더 자세히 알려드릴 수 있습니다. 무엇이 궁금하신가요?"


@router.post("/chat", response_model=ApiResponse[ChatData])
async def chat(
    chat_request: ChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ChatData]:
    """챗봇 메시지 처리 및 DB 저장"""
    user_id = get_current_user_id(request)
    
    # 로그인된 사용자만 대화 저장
    if user_id:
        # 사용자 메시지 저장
        await chat_service.create_chat_message(
            session=session,
            user_id=user_id,
            role="user",
            content=chat_request.message,
        )
    
    # 챗봇 응답 생성
    response_message = _generate_chat_response(chat_request.message, chat_request.selected_meal)
    
    # 로그인된 사용자만 챗봇 응답 저장
    if user_id:
        await chat_service.create_chat_message(
            session=session,
            user_id=user_id,
            role="assistant",
            content=response_message,
        )

    return ApiResponse(
        success=True,
        data=ChatData(
            message=response_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )


@router.get("/chat/history", response_model=ApiResponse[list])
async def get_chat_history(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list]:
    """챗봇 대화 기록 조회"""
    user_id = get_current_user_id(request)
    
    if not user_id:
        return ApiResponse(
            success=False,
            error="로그인이 필요합니다.",
        )
    
    messages = await chat_service.get_user_chat_history(
        session=session,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )
    
    history = [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        }
        for msg in messages
    ]
    
    return ApiResponse(
        success=True,
        data=history,
    )

