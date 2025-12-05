"""사용자 관련 라우트"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete

from app.api.dependencies import get_current_active_user
from app.api.v1.schemas.users import (
    NutrientInfo, 
    UserHealthInfo, 
    UserIntakeData,
    UserProfileResponse,
    UserProfileUpdateRequest,
    PasswordChangeRequest,
    HealthProfileItem,
    HealthProfileResponse,
    AddHealthProfileRequest,
)
from app.api.v1.schemas.common import ApiResponse
from app.db.models import DiseaseAllergyProfile, User, HealthScore
from app.db.session import get_session
from app.services.auth_service import verify_password, hash_password

router = APIRouter()


@router.get("/me/status", response_model=UserIntakeData)
async def get_user_intake_data(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> UserIntakeData:
    """오늘의 사용자 섭취 현황 조회"""
    today = datetime.now().date()
    user_id = current_user.user_id

    # 1. 목표 칼로리 계산
    bmr, tdee, target_calories = 0, 0, 2000 # 기본값
    if current_user.weight and current_user.age and current_user.gender:
        if current_user.gender == 'M':
            bmr = 10 * float(current_user.weight) + 6.25 * current_user.age - 5 * current_user.age + 5
        else:
            bmr = 10 * float(current_user.weight) + 6.25 * current_user.age - 5 * current_user.age - 161
        
        tdee = bmr * 1.55
        
        if current_user.health_goal == 'loss':
            target_calories = int(tdee * 0.85)
        elif current_user.health_goal == 'gain':
            target_calories = int(tdee * 1.15)
        else:
            target_calories = int(tdee)
    
    # 2. 오늘 섭취한 칼로리 합계
    total_calories_stmt = select(func.sum(HealthScore.kcal)).where(
        and_(
            HealthScore.user_id == user_id,
            func.date(HealthScore.created_at) == today,
        )
    )
    total_calories_result = await session.execute(total_calories_stmt)
    total_calories = total_calories_result.scalar_one_or_none() or 0

    # 3. 주요 영양소 섭취량 (TODO)
    # TODO: meals.py의 /daily-summary 로직과 통합하거나 재사용하여 실제 영양소 값 조회
    
    return UserIntakeData(
        totalCalories=int(total_calories),
        targetCalories=target_calories,
        nutrients=NutrientInfo(
            sodium=0, carbs=0, protein=0, fat=0, sugar=0,
        ),
    )


@router.get("/me/health-info", response_model=UserHealthInfo)
async def get_user_health_info(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> UserHealthInfo:
    """사용자 건강 정보 조회"""
    # 사용자의 질병 및 알레르기 정보 조회
    profile_stmt = select(DiseaseAllergyProfile).where(
        DiseaseAllergyProfile.user_id == current_user.user_id
    )
    profile_result = await session.execute(profile_stmt)
    profiles = profile_result.scalars().all()

    diseases = [p.disease_name for p in profiles if p.disease_name]
    allergies = [p.allergy_name for p in profiles if p.allergy_name]

    # 간단한 BMR 계산 (Mifflin-St Jeor)
    bmr, tdee, target_calories = 0, 0, 2000 # 기본값
    if current_user.weight and current_user.age and current_user.gender:
        if current_user.gender == 'M':
            bmr = 10 * float(current_user.weight) + 6.25 * current_user.age - 5 * current_user.age + 5
        else:
            bmr = 10 * float(current_user.weight) + 6.25 * current_user.age - 5 * current_user.age - 161
        
        tdee = bmr * 1.55  # 중간 활동 기준
        
        if current_user.health_goal == 'loss':
            target_calories = int(tdee * 0.85)
        elif current_user.health_goal == 'gain':
            target_calories = int(tdee * 1.15)
        else:
            target_calories = int(tdee)

    return UserHealthInfo(
        goal=current_user.health_goal or "정보 없음",
        diseases=diseases,
        recommendedCalories=target_calories,
        activityLevel="중간",  # 현재는 하드코딩
        bodyType=current_user.health_goal or "정보 없음", # goal과 동일하게 매핑
        allergies=allergies,
        medicalConditions=[], # 현재 스키마에 없음
    )


# ===== Settings 페이지용 API =====

@router.get("/me/profile", response_model=ApiResponse[UserProfileResponse])
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> ApiResponse[UserProfileResponse]:
    """사용자 프로필 조회 (닉네임, 키, 몸무게 등)"""
    return ApiResponse(
        success=True,
        data=UserProfileResponse(
            nickname=current_user.nickname,
            height=float(current_user.height) if current_user.height else None,
            weight=float(current_user.weight) if current_user.weight else None,
            age=current_user.age,
            gender=current_user.gender,
            health_goal=current_user.health_goal,
        ),
        message="프로필 조회 성공"
    )


@router.patch("/me/profile", response_model=ApiResponse[UserProfileResponse])
async def update_user_profile(
    update_data: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[UserProfileResponse]:
    """사용자 프로필 수정 (닉네임, 키, 몸무게)"""
    try:
        # 변경할 필드만 업데이트
        if update_data.nickname is not None:
            current_user.nickname = update_data.nickname
        if update_data.height is not None:
            current_user.height = update_data.height
        if update_data.weight is not None:
            current_user.weight = update_data.weight
        
        current_user.updated_at = datetime.now()
        
        await session.commit()
        await session.refresh(current_user)
        
        return ApiResponse(
            success=True,
            data=UserProfileResponse(
                nickname=current_user.nickname,
                height=float(current_user.height) if current_user.height else None,
                weight=float(current_user.weight) if current_user.weight else None,
                age=current_user.age,
                gender=current_user.gender,
                health_goal=current_user.health_goal,
            ),
            message="프로필이 수정되었습니다."
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프로필 수정 중 오류 발생: {str(e)}"
        )


@router.post("/me/change-password", response_model=ApiResponse[dict])
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    """비밀번호 변경"""
    # 현재 비밀번호 확인
    if not verify_password(password_data.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다."
        )
    
    try:
        # 새 비밀번호 해싱 및 저장
        current_user.password = hash_password(password_data.new_password)
        current_user.updated_at = datetime.now()
        
        await session.commit()
        
        return ApiResponse(
            success=True,
            data={"changed": True},
            message="비밀번호가 변경되었습니다."
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"비밀번호 변경 중 오류 발생: {str(e)}"
        )


@router.get("/me/health-profile", response_model=ApiResponse[HealthProfileResponse])
async def get_health_profile(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[HealthProfileResponse]:
    """알러지/질환 목록 조회"""
    stmt = select(DiseaseAllergyProfile).where(
        DiseaseAllergyProfile.user_id == current_user.user_id
    )
    result = await session.execute(stmt)
    profiles = result.scalars().all()
    
    allergies = []
    diseases = []
    
    for p in profiles:
        if p.allergy_name:
            allergies.append(HealthProfileItem(
                profile_id=p.profile_id,
                name=p.allergy_name,
                type="allergy"
            ))
        if p.disease_name:
            diseases.append(HealthProfileItem(
                profile_id=p.profile_id,
                name=p.disease_name,
                type="disease"
            ))
    
    return ApiResponse(
        success=True,
        data=HealthProfileResponse(allergies=allergies, diseases=diseases),
        message="건강 프로필 조회 성공"
    )


@router.post("/me/health-profile", response_model=ApiResponse[HealthProfileItem])
async def add_health_profile(
    add_data: AddHealthProfileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[HealthProfileItem]:
    """알러지/질환 추가"""
    if add_data.type not in ["allergy", "disease"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="type은 'allergy' 또는 'disease'여야 합니다."
        )
    
    try:
        # 중복 체크
        if add_data.type == "allergy":
            existing_stmt = select(DiseaseAllergyProfile).where(
                and_(
                    DiseaseAllergyProfile.user_id == current_user.user_id,
                    DiseaseAllergyProfile.allergy_name == add_data.name
                )
            )
        else:
            existing_stmt = select(DiseaseAllergyProfile).where(
                and_(
                    DiseaseAllergyProfile.user_id == current_user.user_id,
                    DiseaseAllergyProfile.disease_name == add_data.name
                )
            )
        
        existing_result = await session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"이미 등록된 {'알러지' if add_data.type == 'allergy' else '질환'}입니다."
            )
        
        # 새 항목 추가
        new_profile = DiseaseAllergyProfile(
            user_id=current_user.user_id,
            allergy_name=add_data.name if add_data.type == "allergy" else None,
            disease_name=add_data.name if add_data.type == "disease" else None,
        )
        session.add(new_profile)
        await session.flush()
        await session.commit()
        
        return ApiResponse(
            success=True,
            data=HealthProfileItem(
                profile_id=new_profile.profile_id,
                name=add_data.name,
                type=add_data.type
            ),
            message=f"{'알러지' if add_data.type == 'allergy' else '질환'}가 추가되었습니다."
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"건강 프로필 추가 중 오류 발생: {str(e)}"
        )


@router.delete("/me/health-profile/{profile_id}", response_model=ApiResponse[dict])
async def delete_health_profile(
    profile_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    """알러지/질환 삭제"""
    try:
        # 해당 프로필이 현재 사용자의 것인지 확인
        stmt = select(DiseaseAllergyProfile).where(
            and_(
                DiseaseAllergyProfile.profile_id == profile_id,
                DiseaseAllergyProfile.user_id == current_user.user_id
            )
        )
        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 프로필을 찾을 수 없습니다."
            )
        
        await session.delete(profile)
        await session.commit()
        
        return ApiResponse(
            success=True,
            data={"deleted": True, "profile_id": profile_id},
            message="삭제되었습니다."
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"삭제 중 오류 발생: {str(e)}"
        )

