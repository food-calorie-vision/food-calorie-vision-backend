-- 추천 식단 전용 테이블 생성 마이그레이션
-- 실행일: 2024-11-19
-- 설명: DietPlan, DietPlanMeal 테이블 생성

-- 1. DietPlan 테이블: 추천 식단 메타데이터
CREATE TABLE IF NOT EXISTS `DietPlan` (
    `diet_plan_id` VARCHAR(50) PRIMARY KEY COMMENT '식단 ID (plan_xxx)',
    `user_id` BIGINT NOT NULL COMMENT '사용자 ID',
    
    -- 식단 정보
    `plan_name` VARCHAR(100) NOT NULL COMMENT '식단 이름 (예: 고단백 식단)',
    `description` TEXT NULL COMMENT '식단 설명',
    
    -- 계산된 영양 정보 (추천 당시 기준)
    `bmr` DECIMAL(10, 2) NULL COMMENT '기초대사량 (kcal/day)',
    `tdee` DECIMAL(10, 2) NULL COMMENT '1일 총 에너지 소비량 (kcal/day)',
    `target_calories` DECIMAL(10, 2) NULL COMMENT '목표 칼로리 (kcal/day)',
    `health_goal` ENUM('gain', 'maintain', 'loss') NULL COMMENT '건강 목표',
    
    -- 총 영양소
    `total_calories` DECIMAL(10, 2) NULL COMMENT '식단 총 칼로리',
    `total_protein` DECIMAL(10, 2) NULL COMMENT '식단 총 단백질 (g)',
    `total_carb` DECIMAL(10, 2) NULL COMMENT '식단 총 탄수화물 (g)',
    `total_fat` DECIMAL(10, 2) NULL COMMENT '식단 총 지방 (g)',
    
    -- 메타데이터
    `gpt_response` TEXT NULL COMMENT 'GPT 원문 응답',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '현재 따르고 있는 식단 여부',
    
    -- 외래키
    FOREIGN KEY (`user_id`) REFERENCES `User`(`user_id`) ON DELETE CASCADE,
    
    -- 인덱스
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='추천 식단 메타데이터';


-- 2. DietPlanMeal 테이블: 끼니별 상세 정보
CREATE TABLE IF NOT EXISTS `DietPlanMeal` (
    `meal_id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '끼니 ID',
    `diet_plan_id` VARCHAR(50) NOT NULL COMMENT '식단 ID',
    
    -- 끼니 정보
    `meal_type` ENUM('breakfast', 'lunch', 'dinner', 'snack') NOT NULL COMMENT '끼니 타입',
    `meal_name` VARCHAR(200) NOT NULL COMMENT '끼니 이름 (예: 고단백 식단 - 아침)',
    
    -- 음식 상세
    `food_description` TEXT NULL COMMENT '음식 설명',
    `ingredients` JSON NULL COMMENT '재료 목록 (JSON 배열)',
    
    -- 영양소 (이 끼니의)
    `calories` DECIMAL(10, 2) NULL COMMENT '칼로리 (kcal)',
    `protein` DECIMAL(10, 2) NULL COMMENT '단백질 (g)',
    `carb` DECIMAL(10, 2) NULL COMMENT '탄수화물 (g)',
    `fat` DECIMAL(10, 2) NULL COMMENT '지방 (g)',
    
    -- 실제 섭취 여부
    `consumed` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '섭취 여부',
    `consumed_at` DATETIME NULL COMMENT '섭취 일시',
    
    -- 연결된 UserFoodHistory ID (섭취 시 기록)
    `history_id` BIGINT NULL COMMENT '연결된 섭취 기록 ID',
    
    -- 외래키
    FOREIGN KEY (`diet_plan_id`) REFERENCES `DietPlan`(`diet_plan_id`) ON DELETE CASCADE,
    FOREIGN KEY (`history_id`) REFERENCES `UserFoodHistory`(`history_id`) ON DELETE SET NULL,
    
    -- 인덱스
    INDEX `idx_diet_plan_id` (`diet_plan_id`),
    INDEX `idx_meal_type` (`meal_type`),
    INDEX `idx_consumed` (`consumed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='추천 식단 끼니별 상세';


-- 3. 데이터 확인용 뷰 (선택사항)
CREATE OR REPLACE VIEW `v_diet_plan_summary` AS
SELECT 
    dp.diet_plan_id,
    dp.user_id,
    u.nickname,
    dp.plan_name,
    dp.target_calories,
    dp.health_goal,
    dp.created_at,
    dp.is_active,
    COUNT(dpm.meal_id) AS total_meals,
    SUM(CASE WHEN dpm.consumed = TRUE THEN 1 ELSE 0 END) AS consumed_meals,
    ROUND(SUM(CASE WHEN dpm.consumed = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(dpm.meal_id), 1) AS progress_percent
FROM DietPlan dp
LEFT JOIN DietPlanMeal dpm ON dp.diet_plan_id = dpm.diet_plan_id
LEFT JOIN User u ON dp.user_id = u.user_id
GROUP BY dp.diet_plan_id, dp.user_id, u.nickname, dp.plan_name, dp.target_calories, dp.health_goal, dp.created_at, dp.is_active;


-- 4. 롤백용 SQL (필요 시 사용)
/*
DROP VIEW IF EXISTS `v_diet_plan_summary`;
DROP TABLE IF EXISTS `DietPlanMeal`;
DROP TABLE IF EXISTS `DietPlan`;
*/


