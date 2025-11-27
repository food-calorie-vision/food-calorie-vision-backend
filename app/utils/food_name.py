"""음식명 처리 유틸리티 함수"""


def extract_display_name(food_name: str) -> str:
    """
    음식명에서 표시용 이름 추출
    
    "국수_잔치국수" -> "잔치국수"
    "피자_페퍼로니" -> "페퍼로니"
    "김치찌개" -> "김치찌개" (언더스코어 없으면 그대로)
    
    Args:
        food_name: 원본 음식명 (예: "국수_잔치국수")
        
    Returns:
        표시용 음식명 (예: "잔치국수")
    """
    if not food_name:
        return food_name
    
    # 언더스코어가 있으면 뒤 부분만 반환
    if "_" in food_name:
        parts = food_name.split("_", 1)  # 첫 번째 언더스코어만 분리
        if len(parts) > 1 and parts[1]:  # 뒤 부분이 있으면
            return parts[1]
    
    # 언더스코어가 없으면 원본 반환
    return food_name

