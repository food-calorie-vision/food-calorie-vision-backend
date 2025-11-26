from pydantic import BaseModel, Field
from typing import Optional

class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., description="클라이언트가 관리하는 대화 세션 ID.")
    message: str = Field(..., description="사용자 메시지 텍스트.")
    mode: str = Field("clarify", description="clarify 또는 execute")
    
class ChatMessageResponse(BaseModel):
    session_id: str = Field(..., description="대화 세션 ID.")
    response: str = Field(..., description="응답 메시지(프론트 파싱용 JSON).")
    needs_tool_call: bool = Field(False, description="추가 도구 실행이 필요한지 여부")
    
class ConversationSummaryRequest(BaseModel):
    session_id: str = Field(..., description="The session ID to be summarized.")

class ConversationSummaryResponse(BaseModel):
    session_id: str = Field(..., description="The session ID that was summarized.")
    summary: str = Field(..., description="The generated summary.")
