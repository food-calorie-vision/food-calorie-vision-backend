"""고객센터 API (공지사항, 문의하기)"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.api.v1.schemas.customer_service import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    AnnouncementListResponse,
    InquiryCreate,
    InquiryUpdate,
    InquiryResponse,
    InquiryListResponse,
    InquiryStatusResponse,
)
from app.db.models import Announcement, Inquiry

router = APIRouter(prefix="/customer-service", tags=["customer-service"])


# ============================================================================
# Announcement (공지사항) APIs
# ============================================================================

@router.get("/announcements", response_model=AnnouncementListResponse)
async def get_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(True, description="활성 공지사항만 조회"),
    db: AsyncSession = Depends(get_session),
):
    """공지사항 목록 조회"""
    # 쿼리 생성
    query = select(Announcement)
    
    if active_only:
        query = query.where(Announcement.is_active == True)
    
    query = query.order_by(desc(Announcement.created_at))
    
    # 전체 개수 조회
    count_query = select(func.count()).select_from(Announcement)
    if active_only:
        count_query = count_query.where(Announcement.is_active == True)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # 페이지네이션 적용
    query = query.offset(skip).limit(limit)
    
    # 실행
    result = await db.execute(query)
    announcements = result.scalars().all()
    
    return AnnouncementListResponse(
        total=total,
        announcements=[AnnouncementResponse.model_validate(a) for a in announcements]
    )


@router.get("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_session),
):
    """공지사항 상세 조회 (조회수 증가)"""
    # 공지사항 조회
    query = select(Announcement).where(Announcement.announcement_id == announcement_id)
    result = await db.execute(query)
    announcement = result.scalar_one_or_none()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")
    
    # 조회수 증가
    update_query = (
        update(Announcement)
        .where(Announcement.announcement_id == announcement_id)
        .values(view_count=Announcement.view_count + 1)
    )
    await db.execute(update_query)
    await db.commit()
    
    # 업데이트된 정보 다시 조회
    await db.refresh(announcement)
    
    return AnnouncementResponse.model_validate(announcement)


@router.post("/announcements", response_model=AnnouncementResponse, status_code=201)
async def create_announcement(
    announcement: AnnouncementCreate,
    db: AsyncSession = Depends(get_session),
):
    """공지사항 생성 (관리자용)"""
    new_announcement = Announcement(
        title=announcement.title,
        content=announcement.content,
        is_active=announcement.is_active,
    )
    
    db.add(new_announcement)
    await db.commit()
    await db.refresh(new_announcement)
    
    return AnnouncementResponse.model_validate(new_announcement)


@router.put("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: int,
    announcement_update: AnnouncementUpdate,
    db: AsyncSession = Depends(get_session),
):
    """공지사항 수정 (관리자용)"""
    query = select(Announcement).where(Announcement.announcement_id == announcement_id)
    result = await db.execute(query)
    announcement = result.scalar_one_or_none()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")
    
    # 수정할 필드만 업데이트
    update_data = announcement_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(announcement, key, value)
    
    await db.commit()
    await db.refresh(announcement)
    
    return AnnouncementResponse.model_validate(announcement)


@router.delete("/announcements/{announcement_id}", status_code=204)
async def delete_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_session),
):
    """공지사항 삭제 (관리자용)"""
    query = select(Announcement).where(Announcement.announcement_id == announcement_id)
    result = await db.execute(query)
    announcement = result.scalar_one_or_none()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")
    
    await db.delete(announcement)
    await db.commit()
    
    return None


# ============================================================================
# Inquiry (문의하기) APIs
# ============================================================================

@router.post("/inquiries", response_model=InquiryResponse, status_code=201)
async def create_inquiry(
    inquiry: InquiryCreate,
    db: AsyncSession = Depends(get_session),
):
    """문의하기 생성"""
    new_inquiry = Inquiry(
        user_id=inquiry.user_id,
        nickname=inquiry.nickname,
        email=inquiry.email,
        inquiry_type=inquiry.inquiry_type,
        subject=inquiry.subject,
        content=inquiry.content,
        status='pending',
    )
    
    db.add(new_inquiry)
    await db.commit()
    await db.refresh(new_inquiry)
    
    return InquiryResponse.model_validate(new_inquiry)


@router.get("/inquiries", response_model=InquiryListResponse)
async def get_inquiries(
    user_id: Optional[int] = Query(None, description="특정 사용자의 문의만 조회"),
    email: Optional[str] = Query(None, description="이메일로 문의 조회"),
    status: Optional[str] = Query(None, description="상태별 필터링"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    """문의하기 목록 조회"""
    query = select(Inquiry)
    
    # 필터 적용
    if user_id:
        query = query.where(Inquiry.user_id == user_id)
    if email:
        query = query.where(Inquiry.email == email)
    if status:
        query = query.where(Inquiry.status == status)
    
    query = query.order_by(desc(Inquiry.created_at))
    
    # 전체 개수 조회
    count_query = select(func.count()).select_from(Inquiry)
    if user_id:
        count_query = count_query.where(Inquiry.user_id == user_id)
    if email:
        count_query = count_query.where(Inquiry.email == email)
    if status:
        count_query = count_query.where(Inquiry.status == status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # 페이지네이션 적용
    query = query.offset(skip).limit(limit)
    
    # 실행
    result = await db.execute(query)
    inquiries = result.scalars().all()
    
    return InquiryListResponse(
        total=total,
        inquiries=[InquiryResponse.model_validate(i) for i in inquiries]
    )


@router.get("/inquiries/{inquiry_id}", response_model=InquiryResponse)
async def get_inquiry(
    inquiry_id: int,
    db: AsyncSession = Depends(get_session),
):
    """문의하기 상세 조회"""
    query = select(Inquiry).where(Inquiry.inquiry_id == inquiry_id)
    result = await db.execute(query)
    inquiry = result.scalar_one_or_none()
    
    if not inquiry:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다.")
    
    return InquiryResponse.model_validate(inquiry)


@router.put("/inquiries/{inquiry_id}", response_model=InquiryResponse)
async def update_inquiry(
    inquiry_id: int,
    inquiry_update: InquiryUpdate,
    db: AsyncSession = Depends(get_session),
):
    """문의하기 답변 (관리자용)"""
    query = select(Inquiry).where(Inquiry.inquiry_id == inquiry_id)
    result = await db.execute(query)
    inquiry = result.scalar_one_or_none()
    
    if not inquiry:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다.")
    
    # 수정할 필드만 업데이트
    update_data = inquiry_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(inquiry, key, value)
    
    # 답변 완료 시 responded_at 업데이트
    if inquiry_update.status == 'completed' and inquiry_update.response:
        from datetime import datetime
        inquiry.responded_at = datetime.now()
    
    await db.commit()
    await db.refresh(inquiry)
    
    return InquiryResponse.model_validate(inquiry)


@router.get("/inquiries/my/{user_id}", response_model=list[InquiryStatusResponse])
async def get_my_inquiries(
    user_id: int,
    db: AsyncSession = Depends(get_session),
):
    """내 문의 이력 조회 (간단 버전)"""
    query = (
        select(Inquiry)
        .where(Inquiry.user_id == user_id)
        .order_by(desc(Inquiry.created_at))
    )
    
    result = await db.execute(query)
    inquiries = result.scalars().all()
    
    return [InquiryStatusResponse.model_validate(i) for i in inquiries]

