"""건강 점수 서비스 - health_score 테이블"""
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HealthScore, UserFoodHistory


async def create_health_score(
    session: AsyncSession,
    history_id: int,
    user_id: int,
    food_id: str,
    reference_value: Optional[int] = None,
    kcal: Optional[int] = None,
    positive_score: Optional[int] = None,
    negative_score: Optional[int] = None,
    final_score: Optional[int] = None,
    food_grade: Optional[str] = None,
    calc_method: Optional[str] = None,
) -> HealthScore:
    """
    건강 점수 생성
    
    Args:
        session: DB 세션
        history_id: 음식 섭취 기록 ID
        user_id: 사용자 ID
        food_id: 음식 ID
        reference_value: 영양성분함량기준량
        kcal: 칼로리
        positive_score: 권장영양소 점수 (SUM(권장영양소 9가지의 %값) / 9)
        negative_score: 제한영양소 점수 (SUM(제한영양소 3가지의 %값) / 3)
        final_score: 최종점수 (권장영양소점수 - 제한영양소점수)
        food_grade: 음식 등급 (90점 이상: 우수, 75-89: 좋음, 50-74: 보통, 25-49: 개선필요, 24 이하: 부족)
        calc_method: 계산 방식 (한국식 점수 계산식)
    
    Returns:
        생성된 HealthScore 객체
    """
    score = HealthScore(
        history_id=history_id,
        user_id=user_id,
        food_id=food_id,
        reference_value=reference_value,
        kcal=kcal,
        positive_score=positive_score,
        negative_score=negative_score,
        final_score=final_score,
        food_grade=food_grade,
        calc_method=calc_method,
    )
    
    session.add(score)
    await session.flush()
    
    return score


async def get_health_score_by_history_id(
    session: AsyncSession,
    history_id: int,
) -> Optional[HealthScore]:
    """
    history_id로 건강 점수 조회
    
    Args:
        session: DB 세션
        history_id: 음식 섭취 기록 ID
    
    Returns:
        HealthScore 객체 또는 None
    """
    result = await session.execute(
        select(HealthScore).where(HealthScore.history_id == history_id)
    )
    return result.scalar_one_or_none()


async def get_user_health_scores(
    session: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
) -> List[HealthScore]:
    """
    사용자의 건강 점수 목록 조회
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        limit: 최대 결과 개수
        offset: 결과 오프셋
    
    Returns:
        HealthScore 리스트
    """
    query = (
        select(HealthScore)
        .where(HealthScore.user_id == user_id)
        .order_by(HealthScore.history_id.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_health_scores_by_grade(
    session: AsyncSession,
    user_id: int,
    food_grade: str,
) -> List[HealthScore]:
    """
    특정 등급의 건강 점수 조회
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        food_grade: 음식 등급
    
    Returns:
        해당 등급의 HealthScore 리스트
    """
    query = select(HealthScore).where(
        and_(
            HealthScore.user_id == user_id,
            HealthScore.food_grade == food_grade,
        )
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_health_score(
    session: AsyncSession,
    history_id: int,
    reference_value: Optional[int] = None,
    kcal: Optional[int] = None,
    positive_score: Optional[int] = None,
    negative_score: Optional[int] = None,
    final_score: Optional[int] = None,
    food_grade: Optional[str] = None,
) -> Optional[HealthScore]:
    """
    건강 점수 수정
    
    Args:
        session: DB 세션
        history_id: 음식 섭취 기록 ID
        (기타 수정할 필드들)
    
    Returns:
        수정된 HealthScore 객체 또는 None
    """
    score = await get_health_score_by_history_id(session, history_id)
    if not score:
        return None
    
    if reference_value is not None:
        score.reference_value = reference_value
    if kcal is not None:
        score.kcal = kcal
    if positive_score is not None:
        score.positive_score = positive_score
    if negative_score is not None:
        score.negative_score = negative_score
    if final_score is not None:
        score.final_score = final_score
    if food_grade is not None:
        score.food_grade = food_grade
    
    await session.flush()
    return score


async def delete_health_score(
    session: AsyncSession,
    history_id: int,
) -> bool:
    """
    건강 점수 삭제
    
    Args:
        session: DB 세션
        history_id: 음식 섭취 기록 ID
    
    Returns:
        삭제 성공 여부
    """
    score = await get_health_score_by_history_id(session, history_id)
    if not score:
        return False
    
    await session.delete(score)
    await session.flush()
    return True


async def calculate_food_grade(final_score: int) -> str:
    """
    최종 점수를 기반으로 음식 등급 계산
    
    Args:
        final_score: 최종 점수
    
    Returns:
        음식 등급
    """
    if final_score >= 90:
        return "우수한 영양식품"
    elif final_score >= 75:
        return "좋은 영양식품"
    elif final_score >= 50:
        return "보통 영양식품"
    elif final_score >= 25:
        return "영양개선 필요"
    else:
        return "영양소 부족"


async def calculate_nrf93_score(
    protein_g: float,
    fiber_g: float,
    vitamin_a_ug: float,
    vitamin_c_mg: float,
    vitamin_e_mg: float,
    calcium_mg: float,
    iron_mg: float,
    potassium_mg: float,
    magnesium_mg: float,
    saturated_fat_g: float,
    added_sugar_g: float,
    sodium_mg: float,
    reference_value_g: float = 100.0
) -> dict:
    """
    NRF9.3 (Nutrient Rich Food Index) 영양 점수 계산
    
    NRF9.3 = (∑ 권장영양소 % / 9) - (∑ 제한영양소 % / 3)
    
    **권장영양소 9가지:**
    - 단백질, 식이섬유, 비타민A, 비타민C, 비타민E, 칼슘, 철분, 칼륨, 마그네슘
    
    **제한영양소 3가지:**
    - 포화지방, 첨가당, 나트륨
    
    Args:
        protein_g: 단백질 (g)
        fiber_g: 식이섬유 (g)
        vitamin_a_ug: 비타민A (μg RAE)
        vitamin_c_mg: 비타민C (mg)
        vitamin_e_mg: 비타민E (mg α-TE)
        calcium_mg: 칼슘 (mg)
        iron_mg: 철분 (mg)
        potassium_mg: 칼륨 (mg)
        magnesium_mg: 마그네슘 (mg)
        saturated_fat_g: 포화지방 (g)
        added_sugar_g: 첨가당 (g)
        sodium_mg: 나트륨 (mg)
        reference_value_g: 기준량 (g, 기본 100g)
    
    Returns:
        NRF9.3 점수 계산 결과
    """
    # 일일 권장량 (한국인 영양소 섭취기준, 성인 기준)
    DV = {
        'protein': 55.0,  # g
        'fiber': 25.0,  # g
        'vitamin_a': 700.0,  # μg RAE
        'vitamin_c': 100.0,  # mg
        'vitamin_e': 12.0,  # mg α-TE
        'calcium': 700.0,  # mg
        'iron': 10.0,  # mg (남성 기준, 여성은 14mg)
        'potassium': 3500.0,  # mg
        'magnesium': 350.0,  # mg (남성 기준, 여성은 280mg)
        'saturated_fat': 15.0,  # g (총 에너지의 7% 기준)
        'added_sugar': 50.0,  # g (총 에너지의 10% 기준)
        'sodium': 2000.0,  # mg
    }
    
    # 100g 당으로 정규화
    scale = 100.0 / reference_value_g
    
    # 권장영양소 9가지의 일일권장량 대비 % 계산 (최대 100%로 캡)
    positive_nutrients = [
        min((protein_g * scale / DV['protein']) * 100, 100),
        min((fiber_g * scale / DV['fiber']) * 100, 100),
        min((vitamin_a_ug * scale / DV['vitamin_a']) * 100, 100),
        min((vitamin_c_mg * scale / DV['vitamin_c']) * 100, 100),
        min((vitamin_e_mg * scale / DV['vitamin_e']) * 100, 100),
        min((calcium_mg * scale / DV['calcium']) * 100, 100),
        min((iron_mg * scale / DV['iron']) * 100, 100),
        min((potassium_mg * scale / DV['potassium']) * 100, 100),
        min((magnesium_mg * scale / DV['magnesium']) * 100, 100),
    ]
    
    # 제한영양소 3가지의 일일권장량 대비 % 계산 (최대 100%로 캡)
    negative_nutrients = [
        min((saturated_fat_g * scale / DV['saturated_fat']) * 100, 100),
        min((added_sugar_g * scale / DV['added_sugar']) * 100, 100),
        min((sodium_mg * scale / DV['sodium']) * 100, 100),
    ]
    
    # NRF9.3 점수 계산
    positive_score = sum(positive_nutrients) / 9  # 0~100
    negative_score = sum(negative_nutrients) / 3   # 0~100
    raw_score = positive_score - negative_score    # -100~100
    
    # 점수 범위를 0~100으로 정규화
    # -100 → 0점, 0 → 50점, 100 → 100점
    final_score = (raw_score + 100) / 2
    
    # 최종 점수는 0~100 범위로 제한
    final_score = max(0, min(100, final_score))
    
    return {
        "positive_score": round(positive_score, 2),
        "negative_score": round(negative_score, 2),
        "final_score": round(final_score, 2),
        "food_grade": await calculate_food_grade(int(final_score)),
        "calc_method": "NRF9.3 (Nutrient Rich Food Index) - 0~100점 정규화",
        "details": {
            "positive_nutrients": {
                "protein": round(positive_nutrients[0], 1),
                "fiber": round(positive_nutrients[1], 1),
                "vitamin_a": round(positive_nutrients[2], 1),
                "vitamin_c": round(positive_nutrients[3], 1),
                "vitamin_e": round(positive_nutrients[4], 1),
                "calcium": round(positive_nutrients[5], 1),
                "iron": round(positive_nutrients[6], 1),
                "potassium": round(positive_nutrients[7], 1),
                "magnesium": round(positive_nutrients[8], 1),
            },
            "negative_nutrients": {
                "saturated_fat": round(negative_nutrients[0], 1),
                "added_sugar": round(negative_nutrients[1], 1),
                "sodium": round(negative_nutrients[2], 1),
            }
        }
    }


async def calculate_korean_nutrition_score(
    protein: float,
    fiber: float,
    calcium: float,
    iron: float,
    sodium: float,
    sugar: float,
    saturated_fat: float,
) -> dict:
    """
    한국식 영양 점수 계산 (레거시, 하위 호환용)
    
    한국영양점수 = (단백질 + 섬유질 + 칼슘 + 철분) - (나트륨 + 당분 + 포화지방)
    
    Args:
        protein: 단백질 (%)
        fiber: 식이섬유 (%)
        calcium: 칼슘 (%)
        iron: 철분 (%)
        sodium: 나트륨 (%)
        sugar: 당분 (%)
        saturated_fat: 포화지방 (%)
    
    Returns:
        점수 계산 결과 딕셔너리
    """
    positive_score = protein + fiber + calcium + iron
    negative_score = sodium + sugar + saturated_fat
    final_score = positive_score - negative_score
    
    return {
        "positive_score": int(positive_score),
        "negative_score": int(negative_score),
        "final_score": int(final_score),
        "food_grade": await calculate_food_grade(int(final_score)),
        "calc_method": "한국식 점수 계산식: (단백질 + 섬유질 + 칼슘 + 철분) - (나트륨 + 당분 + 포화지방)",
    }

