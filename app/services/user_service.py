"""사용자 관련 비즈니스 로직"""
from app.db.models import User

def calculate_daily_calories(user: User) -> int:
    """
    사용자 정보를 기반으로 일일 목표 칼로리(TDEE 기반)를 계산합니다.
    
    공식: Mifflin-St Jeor Equation
    1. BMR (기초대사량) 계산
    2. TDEE (활동대사량) = BMR * 1.55 (중간 활동 기준)
    3. 건강 목표(health_goal)에 따른 가감
       - loss: -15%
       - gain: +15%
       - maintain: 유지
    
    Args:
        user: User 모델 객체 (weight, height, age, gender, health_goal 필요)
        
    Returns:
        int: 일일 목표 칼로리 (kcal)
    """
    # 기본값
    target_calories = 2000
    
    # 필수 정보가 없으면 기본값 반환
    if not (user.weight and user.age and user.gender):
        return target_calories
        
    try:
        weight = float(user.weight)
        age = user.age
        # height가 없으면 한국인 평균 키 사용 (남 173, 여 161 - 근사치)
        height = float(user.height) if hasattr(user, 'height') and user.height else (173.0 if user.gender == 'M' else 161.0)
        
        # 1. BMR 계산
        if user.gender == 'M':
            # 남자: 10W + 6.25H - 5A + 5
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            # 여자: 10W + 6.25H - 5A - 161
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
            
        # 2. TDEE 계산 (활동 계수 1.55 가정)
        tdee = bmr * 1.55
        
        # 3. 건강 목표 반영
        if user.health_goal == 'loss':
            target_calories = int(tdee * 0.85)  # 15% 감소
        elif user.health_goal == 'gain':
            target_calories = int(tdee * 1.15)  # 15% 증가
        else:
            target_calories = int(tdee)
            
        return target_calories
        
    except Exception as e:
        print(f"⚠️ 칼로리 계산 중 오류 발생: {e}")
        return 2000  # 오류 시 기본값
