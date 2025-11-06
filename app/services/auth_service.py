"""인증 관련 서비스 로직"""
from datetime import date, datetime

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserHealthInfo

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


async def get_user_by_user_id(session: AsyncSession, user_id: str) -> User | None:
    """user_id로 사용자 조회"""
    result = await session.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, id: int) -> User | None:
    """ID로 사용자 조회"""
    result = await session.execute(select(User).where(User.id == id))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    user_id: str,
    username: str,
    nickname: str,
    password: str,
    gender: str,
    birth_date: date,
    email: str | None = None,
) -> User:
    """새 사용자 생성"""
    # 중복 확인
    existing_user = await get_user_by_user_id(session, user_id)
    if existing_user:
        raise ValueError("이미 존재하는 사용자 ID입니다.")

    # 비밀번호 해싱
    hashed_password = hash_password(password)

    # 사용자 생성
    user = User(
        user_id=user_id,
        username=username,
        nickname=nickname,
        password_hash=hashed_password,
        gender=gender,
        birth_date=birth_date,
        email=email,
    )

    session.add(user)
    await session.flush()  # ID 생성을 위해 flush

    return user


async def create_user_health_info(
    session: AsyncSession,
    user_id: int,
    goal: str,
    body_type: str,
    activity_level: str,
    recommended_calories: float,
    has_allergy: bool = False,
    allergy_info: str | None = None,
    medical_condition: str | None = None,
    allergies: list[str] | None = None,
    diseases: list[str] | None = None,
) -> UserHealthInfo:
    """사용자 건강 정보 생성"""
    health_info = UserHealthInfo(
        user_id=user_id,
        goal=goal,
        body_type=body_type,
        activity_level=activity_level,
        recommended_calories=recommended_calories,
        has_allergy=has_allergy,
        allergy_info=allergy_info,
        medical_condition=medical_condition,
        allergies={"items": allergies} if allergies else None,
        diseases={"items": diseases} if diseases else None,
    )

    session.add(health_info)
    return health_info


async def authenticate_user(session: AsyncSession, user_id: str, password: str) -> User | None:
    """사용자 인증 (로그인)"""
    user = await get_user_by_user_id(session, user_id)
    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user

