"""고객센터 스키마 (공지사항, 문의하기)"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Announcement (공지사항) Schemas
# ============================================================================

class AnnouncementBase(BaseModel):
    """공지사항 기본 스키마"""
    title: str = Field(..., max_length=200, description="공지사항 제목")
    content: str = Field(..., description="공지사항 내용")
    is_active: bool = Field(default=True, description="활성 여부")


class AnnouncementCreate(AnnouncementBase):
    """공지사항 생성 스키마"""
    pass


class AnnouncementUpdate(BaseModel):
    """공지사항 수정 스키마"""
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None
    is_active: Optional[bool] = None


class AnnouncementResponse(AnnouncementBase):
    """공지사항 응답 스키마"""
    announcement_id: int
    created_at: datetime
    updated_at: datetime
    view_count: int = 0

    class Config:
        from_attributes = True


class AnnouncementListResponse(BaseModel):
    """공지사항 목록 응답 스키마"""
    total: int
    announcements: list[AnnouncementResponse]


# ============================================================================
# Inquiry (문의하기) Schemas
# ============================================================================

class InquiryBase(BaseModel):
    """문의하기 기본 스키마"""
    nickname: str = Field(..., max_length=50, description="닉네임")
    email: EmailStr = Field(..., description="이메일")
    inquiry_type: str = Field(..., max_length=50, description="문의 유형")
    subject: str = Field(..., max_length=200, description="문의 제목")
    content: str = Field(..., description="문의 내용")


class InquiryCreate(InquiryBase):
    """문의하기 생성 스키마"""
    user_id: int = Field(..., description="사용자 ID (필수)")


class InquiryUpdate(BaseModel):
    """문의하기 수정 스키마 (관리자용)"""
    status: Optional[str] = Field(None, description="답변 상태")
    response: Optional[str] = Field(None, description="답변 내용")


class InquiryResponse(InquiryBase):
    """문의하기 응답 스키마"""
    inquiry_id: int
    user_id: int
    status: str
    response: Optional[str]
    created_at: datetime
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True


class InquiryListResponse(BaseModel):
    """문의하기 목록 응답 스키마"""
    total: int
    inquiries: list[InquiryResponse]


class InquiryStatusResponse(BaseModel):
    """문의 상태 응답"""
    inquiry_id: int
    subject: str
    inquiry_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

