-- ============================================================================
-- UserFoodHistory 테이블에 meal_type 컬럼 추가
-- ============================================================================
-- 
-- 목적: 음식 섭취 기록에 식사 유형 (아침/점심/저녁/간식) 구분 추가
-- 작성일: 2025-11-20
-- 
-- ============================================================================

USE tempdb;

-- meal_type 컬럼 추가 (ENUM 타입, 기본값: lunch)
ALTER TABLE `UserFoodHistory`
ADD COLUMN `meal_type` ENUM('breakfast', 'lunch', 'dinner', 'snack') NOT NULL DEFAULT 'lunch' COMMENT '식사 유형 (아침/점심/저녁/간식)'
AFTER `food_name`;

-- 인덱스 추가 (meal_type으로 조회 최적화)
CREATE INDEX `idx_meal_type` ON `UserFoodHistory` (`meal_type`);

-- 복합 인덱스 추가 (사용자별 날짜별 식사 유형 조회 최적화)
CREATE INDEX `idx_user_consumed_meal` ON `UserFoodHistory` (`user_id`, `consumed_at`, `meal_type`);

-- 변경사항 확인
DESCRIBE `UserFoodHistory`;

-- 완료 메시지
SELECT '✅ UserFoodHistory 테이블에 meal_type 컬럼 추가 완료!' AS status;
SELECT 'meal_type: ENUM(breakfast, lunch, dinner, snack) NOT NULL DEFAULT lunch' AS column_info;

