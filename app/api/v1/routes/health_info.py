"""건강 정보 관리 API"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.api.v1.schemas.health_info import (
    HealthInfoResponse,
    HealthInfoUpdateRequest,
    HealthInfoUpdateResponse,
)
from app.services import health_service
from app.utils.session import get_current_user_id

router = APIRouter()


@router.get("/me", response_model=HealthInfoResponse)
async def get_my_health_info(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> HealthInfoResponse:
    """
    현재 로그인한 사용자의 건강 정보 조회
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    health_info = await health_service.get_user_health_info(session, user_id)
    
    if not health_info:
        raise HTTPException(status_code=404, detail="건강 정보를 찾을 수 없습니다.")
    
    return HealthInfoResponse.model_validate(health_info)


@router.put("/me", response_model=HealthInfoUpdateResponse)
async def update_my_health_info(
    update_data: HealthInfoUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> HealthInfoUpdateResponse:
    """
    현재 로그인한 사용자의 건강 정보 수정
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    health_info = await health_service.update_user_health_info(
        session=session,
        user_id=user_id,
        health_goal=update_data.health_goal,
        body_type=update_data.body_type,
        has_allergy=update_data.has_allergy,
        allergy_info=update_data.allergy_info,
        medical_condition=update_data.medical_condition,
    )
    
    if not health_info:
        raise HTTPException(status_code=404, detail="건강 정보를 찾을 수 없습니다.")
    
    return HealthInfoUpdateResponse(
        success=True,
        message="건강 정보가 수정되었습니다.",
        data=HealthInfoResponse.model_validate(health_info),
    )

