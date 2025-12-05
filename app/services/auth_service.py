"""인증 관련 서비스 로직 - ERDCloud 스키마 기반"""
from datetime import date

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, DiseaseAllergyProfile

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    # bcrypt는 72바이트 제한이 있으므로 잘라줌
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes.decode('utf-8'))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    # bcrypt는 72바이트 제한이 있으므로 잘라줌
    password_bytes = plain_password.encode('utf-8')[:72]
    return pwd_context.verify(password_bytes.decode('utf-8'), hashed_password)


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """user_id(BIGINT)로 사용자 조회"""
    result = await session.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """이메일로 사용자 조회"""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    """username으로 사용자 조회"""
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    username: str,
    password: str,
    nickname: str | None = None,
    gender: str | None = None,
    age: int | None = None,
    weight: float | None = None,
    height: float | None = None,  # ✅ 키(height) 파라미터 추가
    health_goal: str = "maintain",
    allergies: str | None = None,
    diseases: str | None = None,
) -> User:
    """
    새 사용자 생성 (user_id는 자동생성)
    
    Args:
        session: DB 세션
        email: 이메일 (필수, 고유)
        username: 사용자명 (필수, 고유)
        password: 비밀번호
        nickname: 닉네임
        gender: 성별 ('M', 'F', 'Other')
        age: 나이
        weight: 체중 (kg)
        height: 키 (cm)
        health_goal: 건강 목표 ('gain', 'maintain', 'loss')
        allergies: 알레르기 정보 (콤마로 구분된 문자열)
        diseases: 기저질환 정보 (콤마로 구분된 문자열)
    
    Returns:
        생성된 User 객체
    """
    # 이메일 중복 확인
    existing_user = await get_user_by_email(session, email)
    if existing_user:
        raise ValueError("이미 존재하는 이메일입니다.")
    
    # username 중복 확인
    existing_user = await get_user_by_username(session, username)
    if existing_user:
        raise ValueError("이미 존재하는 사용자명입니다.")

    # 비밀번호 해싱
    hashed_password = hash_password(password)

    # 사용자 생성 (user_id는 DB에서 자동생성)
    user = User(
        email=email,
        username=username,
        password=hashed_password,
        nickname=nickname or username,
        gender=gender,
        age=age,
        weight=weight,
        height=height,  # ✅ 키(height) 추가
        health_goal=health_goal,
    )

    session.add(user)
    await session.flush()  # user_id 생성을 위해 flush

    user_id = user.user_id

    # 알레르기 정보 처리
    if allergies:
        allergy_list = [a.strip() for a in allergies.split(',') if a.strip()]
        for allergy_name in allergy_list:
            profile = DiseaseAllergyProfile(user_id=user_id, allergy_name=allergy_name)
            session.add(profile)
            
    # 질환 정보 처리 (알레르기와 동일한 방식)
    if diseases:
        disease_list = [d.strip() for d in diseases.split(',') if d.strip()]
        for disease_name in disease_list:
            profile = DiseaseAllergyProfile(user_id=user_id, disease_name=disease_name)
            session.add(profile)

    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    """
    사용자 인증 (이메일 로그인)
    
    Args:
        session: DB 세션
        email: 이메일
        password: 비밀번호
    
    Returns:
        인증 성공 시 User 객체, 실패 시 None
    """
    user = await get_user_by_email(session, email)
    if not user:
        return None

    if not verify_password(password, user.password):
        return None

    return user
