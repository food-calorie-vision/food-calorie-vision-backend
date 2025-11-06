"""점수 계산 관련 서비스"""
from typing import Optional
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import DailyScore
from app.services import meal_service, health_service


def calculate_calorie_score(actual: float, target: float) -> float:
    """칼로리 점수 계산 (40점 만점)"""
    if target == 0:
        return 0
    
    ratio = actual / target
    
    # 목표의 80-120% 범위가 최고 점수
    if 0.8 <= ratio <= 1.2:
        return 40
    elif ratio < 0.8:
        # 부족한 경우: 50%까지 선형 감소
        return max(0, 40 * (ratio / 0.8))
    else:
        # 초과한 경우: 150%까지 선형 감소
        return max(0, 40 * (1 - (ratio - 1.2) / 0.3))


def calculate_balance_score(protein: float, carbs: float, fat: float) -> float:
    """영양소 균형 점수 계산 (30점 만점)"""
    total = protein + carbs + fat
    
    if total == 0:
        return 0
    
    # 이상적인 비율: 단백질 20-30%, 탄수화물 45-65%, 지방 20-35%
    protein_ratio = protein / total
    carbs_ratio = carbs / total
    fat_ratio = fat / total
    
    score = 30
    
    # 단백질 비율 체크
    if not (0.15 <= protein_ratio <= 0.35):
        score -= 10
    
    # 탄수화물 비율 체크
    if not (0.40 <= carbs_ratio <= 0.70):
        score -= 10
    
    # 지방 비율 체크
    if not (0.15 <= fat_ratio <= 0.40):
        score -= 10
    
    return max(0, score)


def calculate_meal_frequency_score(meal_count: int) -> float:
    """식사 횟수 점수 계산 (20점 만점)"""
    # 3끼가 이상적
    if meal_count == 3:
        return 20
    elif meal_count == 2:
        return 15
    elif meal_count == 4:
        return 18
    elif meal_count == 1:
        return 10
    elif meal_count >= 5:
        return 12
    else:
        return 0


def calculate_consistency_score(recent_days: int) -> float:
    """꾸준함 점수 계산 (10점 만점)"""
    # 최근 7일 중 기록한 날 수
    if recent_days >= 7:
        return 10
    else:
        return recent_days * 1.4  # 7일 기준으로 비례


async def calculate_daily_score(
    session: AsyncSession,
    user_id: str,
    target_date: date,
) -> dict:
    """일일 점수 계산"""
    # 해당 날짜의 식사 요약 정보
    summary = await meal_service.get_daily_summary(
        session=session,
        user_id=user_id,
        target_date=target_date,
    )
    
    # 사용자의 권장 칼로리
    health_info = await health_service.get_user_health_info(session, user_id)
    target_calories = health_info.recommended_calories if health_info else 2000
    
    # 1. 칼로리 점수 (40점)
    calorie_score = calculate_calorie_score(
        summary["total_calories"],
        target_calories
    )
    
    # 2. 영양소 균형 점수 (30점)
    balance_score = calculate_balance_score(
        summary["total_protein"],
        summary["total_carbs"],
        summary["total_fat"]
    )
    
    # 3. 식사 횟수 점수 (20점)
    frequency_score = calculate_meal_frequency_score(summary["meal_count"])
    
    # 4. 꾸준함 점수 (10점) - 간단하게 기록 여부로
    consistency_score = 10 if summary["meal_count"] > 0 else 0
    
    # 총점
    total_score = round(calorie_score + balance_score + frequency_score + consistency_score)
    
    # 피드백 생성
    feedback = generate_feedback(total_score, summary, target_calories)
    improvement = generate_improvement(summary, target_calories, health_info)
    
    return {
        "date": target_date,
        "total_score": total_score,
        "calorie_score": round(calorie_score, 1),
        "balance_score": round(balance_score, 1),
        "frequency_score": round(frequency_score, 1),
        "consistency_score": round(consistency_score, 1),
        "feedback": feedback,
        "improvement": improvement,
        "meal_count": summary["meal_count"],
        "total_calories": summary["total_calories"],
        "target_calories": target_calories,
    }


def generate_feedback(score: float, summary: dict, target: float) -> str:
    """점수에 따른 피드백 생성"""
    if score >= 90:
        return "와! 오늘은 정말 균형있게 드셨군요! 곧 원하시는 목표를 이루실 수 있을거에요"
    elif score >= 80:
        return "훌륭해요! 건강한 식습관을 잘 유지하고 계시네요"
    elif score >= 70:
        return "좋은 식습관입니다! 조금만 더 신경쓰면 완벽해질 거예요"
    elif score >= 60:
        return "괜찮은 편이에요. 영양 균형을 조금 더 맞춰보는 건 어떨까요?"
    elif score >= 50:
        return "식사 기록을 꾸준히 하고 있어요. 영양 균형에 조금 더 신경써보세요"
    else:
        return "오늘 식사가 부족하거나 균형이 맞지 않아요. 내일은 더 잘 해보실 수 있어요!"


def generate_improvement(summary: dict, target: float, health_info) -> str:
    """개선점 제안"""
    improvements = []
    
    # 칼로리 관련
    calories = summary["total_calories"]
    if calories < target * 0.8:
        improvements.append("칼로리 섭취가 부족해요. 식사량을 조금 늘려보세요")
    elif calories > target * 1.2:
        improvements.append("칼로리를 조금 초과했어요. 다음 식사는 가볍게 드세요")
    
    # 식사 횟수
    meal_count = summary["meal_count"]
    if meal_count < 2:
        improvements.append("식사를 거르지 않도록 주의하세요")
    elif meal_count > 4:
        improvements.append("간식을 줄이고 세 끼를 규칙적으로 드세요")
    
    # 영양소 균형
    total = summary["total_protein"] + summary["total_carbs"] + summary["total_fat"]
    if total > 0:
        protein_ratio = summary["total_protein"] / total
        if protein_ratio < 0.15:
            improvements.append("단백질 섭취량이 부족해요. 고기나 계란을 추가해보세요")
        elif protein_ratio > 0.35:
            improvements.append("단백질이 과다해요. 채소와 곡물을 더 드세요")
    
    if not improvements:
        improvements.append("완벽한 하루였어요! 내일도 이대로 유지하세요")
    
    return " / ".join(improvements)


async def save_daily_score(
    session: AsyncSession,
    user_id: str,
    target_date: date,
    score_data: dict,
) -> DailyScore:
    """일일 점수 DB 저장"""
    # 기존 점수 확인
    result = await session.execute(
        select(DailyScore).where(
            DailyScore.user_id == user_id,
            DailyScore.score_date == target_date
        )
    )
    existing_score = result.scalar_one_or_none()
    
    if existing_score:
        # 업데이트
        existing_score.total_score = score_data["total_score"]
        existing_score.calorie_score = score_data["calorie_score"]
        existing_score.balance_score = score_data["balance_score"]
        existing_score.frequency_score = score_data["frequency_score"]
        existing_score.consistency_score = score_data["consistency_score"]
        existing_score.feedback = score_data["feedback"]
        existing_score.improvement_suggestion = score_data["improvement"]
        daily_score = existing_score
    else:
        # 새로 생성
        daily_score = DailyScore(
            user_id=user_id,
            score_date=target_date,
            total_score=score_data["total_score"],
            calorie_score=score_data["calorie_score"],
            balance_score=score_data["balance_score"],
            frequency_score=score_data["frequency_score"],
            consistency_score=score_data["consistency_score"],
            feedback=score_data["feedback"],
            improvement_suggestion=score_data["improvement"],
        )
        session.add(daily_score)
    
    await session.commit()
    await session.refresh(daily_score)
    
    return daily_score


async def get_daily_score(
    session: AsyncSession,
    user_id: str,
    target_date: date,
) -> Optional[DailyScore]:
    """일일 점수 조회"""
    result = await session.execute(
        select(DailyScore).where(
            DailyScore.user_id == user_id,
            DailyScore.score_date == target_date
        )
    )
    return result.scalar_one_or_none()

