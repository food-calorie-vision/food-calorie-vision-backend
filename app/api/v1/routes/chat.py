"""챗봇 관련 라우트"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.v1.schemas.chat import ChatData, ChatRequest
from app.api.v1.schemas.common import ApiResponse

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
async def chat(request: ChatRequest) -> ApiResponse[ChatData]:
    """챗봇 메시지 처리 (메모리 기반 스텁)"""
    # TODO: 실제 LLM 모델로 대체
    response_message = _generate_chat_response(request.message, request.selected_meal)

    return ApiResponse(
        success=True,
        data=ChatData(
            message=response_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

