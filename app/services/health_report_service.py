"""건강 리포트 서비스 - HealthReport 테이블"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HealthReport


async def create_health_report(
    session: AsyncSession,
    user_id: int,
    period_type: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    summary_json: Optional[Dict[str, Any]] = None,
) -> HealthReport:
    """
    건강 리포트 생성
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        period_type: 기간 유형 ('daily', 'weekly', 'monthly')
        start_date: 시작 날짜
        end_date: 종료 날짜
        summary_json: 리포트 요약 데이터 (JSON)
    
    Returns:
        생성된 HealthReport 객체
    """
    report = HealthReport(
        user_id=user_id,
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
        summary_json=summary_json,
        generated_at=datetime.now(),
    )
    
    session.add(report)
    await session.flush()
    
    return report


async def get_health_report_by_id(
    session: AsyncSession,
    report_id: int,
) -> Optional[HealthReport]:
    """
    report_id로 건강 리포트 조회
    
    Args:
        session: DB 세션
        report_id: 리포트 ID
    
    Returns:
        HealthReport 객체 또는 None
    """
    result = await session.execute(
        select(HealthReport).where(HealthReport.report_id == report_id)
    )
    return result.scalar_one_or_none()


async def get_user_health_reports(
    session: AsyncSession,
    user_id: int,
    period_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[HealthReport]:
    """
    사용자의 건강 리포트 목록 조회
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        period_type: 기간 유형 필터 ('daily', 'weekly', 'monthly')
        limit: 최대 결과 개수
        offset: 결과 오프셋
    
    Returns:
        HealthReport 리스트
    """
    query = select(HealthReport).where(HealthReport.user_id == user_id)
    
    if period_type:
        query = query.where(HealthReport.period_type == period_type)
    
    query = query.order_by(HealthReport.generated_at.desc()).limit(limit).offset(offset)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_latest_report_by_period(
    session: AsyncSession,
    user_id: int,
    period_type: str,
) -> Optional[HealthReport]:
    """
    특정 기간 유형의 최신 리포트 조회
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        period_type: 기간 유형
    
    Returns:
        최신 HealthReport 객체 또는 None
    """
    query = (
        select(HealthReport)
        .where(
            and_(
                HealthReport.user_id == user_id,
                HealthReport.period_type == period_type,
            )
        )
        .order_by(HealthReport.generated_at.desc())
        .limit(1)
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_reports_by_date_range(
    session: AsyncSession,
    user_id: int,
    start_date: date,
    end_date: date,
) -> List[HealthReport]:
    """
    날짜 범위로 건강 리포트 조회
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        start_date: 시작 날짜
        end_date: 종료 날짜
    
    Returns:
        해당 기간의 HealthReport 리스트
    """
    query = select(HealthReport).where(
        and_(
            HealthReport.user_id == user_id,
            HealthReport.start_date >= start_date,
            HealthReport.end_date <= end_date,
        )
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_health_report(
    session: AsyncSession,
    report_id: int,
    summary_json: Optional[Dict[str, Any]] = None,
) -> Optional[HealthReport]:
    """
    건강 리포트 수정 (주로 summary_json 업데이트)
    
    Args:
        session: DB 세션
        report_id: 리포트 ID
        summary_json: 수정할 요약 데이터
    
    Returns:
        수정된 HealthReport 객체 또는 None
    """
    report = await get_health_report_by_id(session, report_id)
    if not report:
        return None
    
    if summary_json is not None:
        report.summary_json = summary_json
    
    await session.flush()
    return report


async def delete_health_report(
    session: AsyncSession,
    report_id: int,
) -> bool:
    """
    건강 리포트 삭제
    
    Args:
        session: DB 세션
        report_id: 리포트 ID
    
    Returns:
        삭제 성공 여부
    """
    report = await get_health_report_by_id(session, report_id)
    if not report:
        return False
    
    await session.delete(report)
    await session.flush()
    return True


async def generate_daily_report_summary(
    total_kcal: int,
    meal_count: int,
    avg_score: float,
    top_foods: List[str],
) -> Dict[str, Any]:
    """
    일일 리포트 요약 데이터 생성
    
    Args:
        total_kcal: 총 칼로리
        meal_count: 식사 횟수
        avg_score: 평균 건강 점수
        top_foods: 자주 먹은 음식 목록
    
    Returns:
        요약 데이터 딕셔너리
    """
    return {
        "total_kcal": total_kcal,
        "meal_count": meal_count,
        "avg_score": round(avg_score, 2),
        "top_foods": top_foods,
        "report_type": "daily",
    }


async def generate_weekly_report_summary(
    total_kcal: int,
    daily_avg_kcal: float,
    meal_count: int,
    avg_score: float,
    best_day: str,
    worst_day: str,
) -> Dict[str, Any]:
    """
    주간 리포트 요약 데이터 생성
    
    Args:
        total_kcal: 총 칼로리
        daily_avg_kcal: 일일 평균 칼로리
        meal_count: 식사 횟수
        avg_score: 평균 건강 점수
        best_day: 가장 건강했던 날
        worst_day: 개선이 필요한 날
    
    Returns:
        요약 데이터 딕셔너리
    """
    return {
        "total_kcal": total_kcal,
        "daily_avg_kcal": round(daily_avg_kcal, 2),
        "meal_count": meal_count,
        "avg_score": round(avg_score, 2),
        "best_day": best_day,
        "worst_day": worst_day,
        "report_type": "weekly",
    }


async def generate_monthly_report_summary(
    total_kcal: int,
    daily_avg_kcal: float,
    meal_count: int,
    avg_score: float,
    improvement_areas: List[str],
    achievements: List[str],
) -> Dict[str, Any]:
    """
    월간 리포트 요약 데이터 생성
    
    Args:
        total_kcal: 총 칼로리
        daily_avg_kcal: 일일 평균 칼로리
        meal_count: 식사 횟수
        avg_score: 평균 건강 점수
        improvement_areas: 개선이 필요한 영역
        achievements: 달성한 목표
    
    Returns:
        요약 데이터 딕셔너리
    """
    return {
        "total_kcal": total_kcal,
        "daily_avg_kcal": round(daily_avg_kcal, 2),
        "meal_count": meal_count,
        "avg_score": round(avg_score, 2),
        "improvement_areas": improvement_areas,
        "achievements": achievements,
        "report_type": "monthly",
    }

