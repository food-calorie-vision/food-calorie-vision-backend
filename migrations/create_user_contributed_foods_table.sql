-- 사용자 기여 음식 테이블 생성
-- 작성일: 2025-11-21
-- 목적: 사용자가 추가한 음식을 공식 DB와 분리하여 관리

CREATE TABLE IF NOT EXISTS user_contributed_foods (
    -- 기본 정보
    food_id VARCHAR(200) PRIMARY KEY COMMENT '음식 ID (USER_{user_id}_{timestamp})',
    user_id BIGINT NOT NULL COMMENT '기여한 사용자 ID',
    
    -- 음식 정보
    food_name VARCHAR(200) NOT NULL COMMENT '음식 이름',
    nutrient_name VARCHAR(255) NULL COMMENT '영양소 DB 형식 이름',
    food_class1 VARCHAR(255) NULL COMMENT '대분류',
    food_class2 VARCHAR(255) NULL COMMENT '중분류/재료',
    representative_food_name VARCHAR(200) NULL COMMENT '대표 음식명',
    
    -- 재료 정보
    ingredients VARCHAR(500) NULL COMMENT '재료 목록 (JSON 또는 콤마 구분)',
    
    -- 기준량
    unit VARCHAR(50) NULL COMMENT '단위',
    reference_value FLOAT NULL COMMENT '영양성분함량기준량 (g)',
    
    -- 주요 영양소
    protein FLOAT NULL COMMENT '단백질 (g)',
    carb FLOAT NULL COMMENT '탄수화물 (g)',
    fat FLOAT NULL COMMENT '지방 (g)',
    fiber FLOAT NULL COMMENT '식이섬유 (g)',
    
    -- 비타민
    vitamin_a FLOAT NULL COMMENT '비타민 A (μg)',
    vitamin_c FLOAT NULL COMMENT '비타민 C (mg)',
    
    -- 미네랄
    calcium FLOAT NULL COMMENT '칼슘 (mg)',
    iron FLOAT NULL COMMENT '철분 (mg)',
    potassium FLOAT NULL COMMENT '칼륨 (mg)',
    magnesium FLOAT NULL COMMENT '마그네슘 (mg)',
    
    -- 제한 영양소
    saturated_fat FLOAT NULL COMMENT '포화지방 (g)',
    added_sugar FLOAT NULL COMMENT '첨가당 (g)',
    sodium FLOAT NULL COMMENT '나트륨 (mg)',
    
    -- 관심 영양소
    cholesterol FLOAT NULL COMMENT '콜레스테롤 (mg)',
    trans_fat FLOAT NULL COMMENT '트랜스지방 (g)',
    
    -- 메타데이터
    usage_count INT NOT NULL DEFAULT 1 COMMENT '사용 횟수',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
    
    -- 승인 상태 (향후 관리자 승인 기능용)
    is_approved BOOLEAN NOT NULL DEFAULT FALSE COMMENT '관리자 승인 여부',
    approved_at DATETIME NULL COMMENT '승인일시',
    
    -- 인덱스
    INDEX idx_user_id (user_id),
    INDEX idx_nutrient_name (nutrient_name),
    INDEX idx_food_class1 (food_class1),
    INDEX idx_usage_count (usage_count),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='사용자 기여 음식 테이블';

-- 사용 예시:
-- 1. 새 음식 추가
-- INSERT INTO user_contributed_foods (food_id, user_id, food_name, nutrient_name, food_class1, protein, carb, fat, sodium)
-- VALUES ('USER_1_1732185600', 1, '기본 그린 샐러드', '샐러드_그린', '샐러드류', 5.2, 12.3, 8.1, 320);

-- 2. 사용 횟수 증가
-- UPDATE user_contributed_foods SET usage_count = usage_count + 1 WHERE food_id = 'USER_1_1732185600';

-- 3. 인기 음식 조회 (사용 횟수 5회 이상)
-- SELECT * FROM user_contributed_foods WHERE usage_count >= 5 ORDER BY usage_count DESC;

-- 4. 승인 대기 음식 조회
-- SELECT * FROM user_contributed_foods WHERE is_approved = FALSE AND usage_count >= 3 ORDER BY usage_count DESC;

