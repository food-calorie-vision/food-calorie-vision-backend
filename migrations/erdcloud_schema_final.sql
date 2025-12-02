-- ============================================================================
-- ERDCloud 스키마 완전 재구성 (BIGINT user_id, AUTO_INCREMENT 포함)
-- ============================================================================
-- 
-- 주의사항:
-- 1. User 테이블: user_id는 BIGINT AUTO_INCREMENT
-- 2. Food 테이블: food_id는 VARCHAR(200) (food_nutrients와 호환)
-- 3. Nutrient 테이블은 생성하지 않음 (food_nutrients 사용)
-- 4. 모든 외래 키는 CASCADE 설정
-- 
-- ============================================================================

-- 데이터베이스 선택
USE tempdb;

-- ============================================================================
-- 1단계: 외래 키 체크 비활성화 및 기존 테이블 삭제
-- ============================================================================

SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS `health_score`;
DROP TABLE IF EXISTS `UserFoodHistory`;
DROP TABLE IF EXISTS `HealthReport`;
DROP TABLE IF EXISTS `UserPreferences`;
DROP TABLE IF EXISTS `disease_allergy_profile`;
DROP TABLE IF EXISTS `Food`;
DROP TABLE IF EXISTS `User`;

SET FOREIGN_KEY_CHECKS=1;

-- ============================================================================
-- 2단계: 테이블 생성 (PRIMARY KEY 포함)
-- ============================================================================

-- User 테이블 (user_id: BIGINT AUTO_INCREMENT)
CREATE TABLE `User` (
    `user_id` BIGINT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL,
    `email` VARCHAR(100) NOT NULL,
    `password` VARCHAR(255) NOT NULL,
    `gender` ENUM('M', 'F') NULL,
    `age` INT NULL,
    `weight` DECIMAL(5,2) NULL,
    `health_goal` ENUM('gain', 'maintain', 'loss') NOT NULL DEFAULT 'maintain',
    `nickname` VARCHAR(50) NULL,
    `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`),
    UNIQUE KEY `unique_email` (`email`),
    UNIQUE KEY `unique_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Food 테이블
CREATE TABLE `Food` (
    `food_id` VARCHAR(200) NOT NULL,
    `image_ref` VARCHAR(255) NULL,
    `category` VARCHAR(100) NULL,
    `food_class_1` VARCHAR(100) NULL COMMENT '식품大분류명',
    `food_class_2` VARCHAR(100) NULL COMMENT '식품중분류 -> 음식 명칭',
    `food_name` VARCHAR(200) NULL,
    PRIMARY KEY (`food_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- UserFoodHistory 테이블
CREATE TABLE `UserFoodHistory` (
    `history_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `food_id` VARCHAR(200) NOT NULL,
    `consumed_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    `portion_size_g` DECIMAL(10,2) NULL,
    `food_name` VARCHAR(200) NOT NULL,
    PRIMARY KEY (`history_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_food_id` (`food_id`),
    INDEX `idx_consumed_at` (`consumed_at`),
    CONSTRAINT `FK_User_TO_UserFoodHistory` FOREIGN KEY (`user_id`) 
        REFERENCES `User` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `FK_Food_TO_UserFoodHistory` FOREIGN KEY (`food_id`) 
        REFERENCES `Food` (`food_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- health_score 테이블
CREATE TABLE `health_score` (
    `score_id` BIGINT NOT NULL AUTO_INCREMENT,
    `history_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    `food_id` VARCHAR(200) NOT NULL,
    `reference_value` INT NULL COMMENT '영양성분함량기준량',
    `kcal` INT NULL,
    `positive_score` INT NULL COMMENT 'SUM(권장영양소 9가지의 %값) / 9',
    `negative_score` INT NULL COMMENT 'SUM(제한영양소 3가지의 %값) / 3',
    `final_score` INT NULL COMMENT '최종점수 = 권장영양소점수 - 제한영양소점수',
    `food_grade` VARCHAR(100) NULL COMMENT '90점 이상: 우수한 영양식품, 75-89점: 좋은 영양식품, 50-74점: 보통 영양식품, 25-49점: 영양개선 필요, 24점 이하: 영양소 부족',
    `calc_method` VARCHAR(100) NULL COMMENT '한국식 점수 계산식',
    PRIMARY KEY (`score_id`),
    UNIQUE KEY `unique_history` (`history_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_food_id` (`food_id`),
    CONSTRAINT `FK_UserFoodHistory_TO_health_score` FOREIGN KEY (`history_id`) 
        REFERENCES `UserFoodHistory` (`history_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- HealthReport 테이블
CREATE TABLE `HealthReport` (
    `report_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `period_type` ENUM('daily', 'weekly', 'monthly') NULL,
    `start_date` DATE NULL,
    `end_date` DATE NULL,
    `summary_json` JSON NULL,
    `generated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`report_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_period_type` (`period_type`),
    INDEX `idx_generated_at` (`generated_at`),
    CONSTRAINT `FK_User_TO_HealthReport` FOREIGN KEY (`user_id`) 
        REFERENCES `User` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- UserPreferences 테이블
CREATE TABLE `UserPreferences` (
    `pref_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `preference_type` VARCHAR(100) NULL,
    `preference_value` VARCHAR(255) NULL,
    `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`pref_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_preference_type` (`preference_type`),
    CONSTRAINT `FK_User_TO_UserPreferences` FOREIGN KEY (`user_id`) 
        REFERENCES `User` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- disease_allergy_profile 테이블
CREATE TABLE `disease_allergy_profile` (
    `profile_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `allergy_name` VARCHAR(100) NULL,
    `disease_name` VARCHAR(100) NULL,
    `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`profile_id`),
    INDEX `idx_user_id` (`user_id`),
    CONSTRAINT `FK_User_TO_disease_allergy_profile` FOREIGN KEY (`user_id`) 
        REFERENCES `User` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================================
-- 3단계: 완료 확인
-- ============================================================================

-- 생성된 테이블 확인
SHOW TABLES;

-- User 테이블 구조 확인 (AUTO_INCREMENT 확인)
DESCRIBE `User`;

-- 완료 메시지
SELECT '✅ ERDCloud 스키마 생성 완료!' AS status;
SELECT 'User.user_id: BIGINT AUTO_INCREMENT' AS user_id_type;
SELECT 'Food.food_id: VARCHAR(200)' AS food_id_type;
SELECT 'Nutrient 테이블은 생성하지 않음 (food_nutrients 사용)' AS note;
