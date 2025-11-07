-- ERDCloud 스키마 적용 SQL
-- food_nutrients 테이블은 절대 수정하지 않습니다
-- users 테이블의 user_id는 VARCHAR(50)이므로 외래 키도 VARCHAR(50)로 설정

-- 데이터베이스 선택 (실제 데이터베이스 이름으로 변경하세요)
USE your_database_name;

-- 1. Food 테이블 생성
CREATE TABLE IF NOT EXISTS `Food` (
    `food_id` VARCHAR(200) NOT NULL,
    `image_ref` VARCHAR(255) NULL,
    `category` VARCHAR(100) NULL,
    `food_class_1` VARCHAR(100) NULL COMMENT '식품大분류명 (e.g. 밥류, 빵 및 과자류, 면 및 만두류, 국 및 탕류, 찌개 및 전골류, 찜류, 구이류, 전/적 및 부침류, 볶음류, 조림류, 튀김류, 나물.숙채류, 생채/무침류, 젓갈류, 장아찌/절임, 유제품류 및 빙과류, 음료 및 차류, 죽 및 스프류, 김치류, 장아찌/절임류, 수/조/어/육류, 곡류/ 서류 제품, 장류/양념류)',
    `food_class_2` VARCHAR(100) NULL COMMENT '식품중분류 -> 음식 명칭',
    `food_name` VARCHAR(200) NULL,
    PRIMARY KEY (`food_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2. Nutrient 테이블 생성 (주석: food_nutrients 테이블이 이미 존재하므로 생성하지 않음)
-- CREATE TABLE IF NOT EXISTS `Nutrient` (
--     `food_id` VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
--     `nutrient_name` VARCHAR(100) NULL,
--     `food_class1` VARCHAR(100) NULL COMMENT '식품大분류명',
--     `food_class2` VARCHAR(100) NULL,
--     `unit` VARCHAR(20) NULL,
--     `kcal` INT NULL,
--     `protein` INT NULL COMMENT '권장영양소_단백질',
--     `Fiber` INT NULL COMMENT '권장영양소_식이섬유',
--     `vitamin_a` INT NULL COMMENT '권장영양소_비타민A',
--     `vitamin_c` INT NULL COMMENT '권장영양소_Vitamin_C',
--     `vitamin_e` INT NULL COMMENT '권장영양소_Vitamin_E',
--     `calcium` INT NULL COMMENT '권장영양소_칼슘',
--     `iron` INT NULL COMMENT '권장영양소_철분',
--     `potassium` INT NULL COMMENT '권장영양소_칼륨',
--     `magnessium` INT NULL COMMENT '권장영양소_마그네슘',
--     `saturated_fat` INT NULL COMMENT '제한영양소_포화지방',
--     `added_sugar` INT NULL COMMENT '제한영양소_첨가당',
--     `sodium` INT NULL COMMENT '제한영양소_나트륨',
--     `cholesterol` INT NULL COMMENT '관심영양소_콜레스테롤',
--     `trans_Fat` INT NULL COMMENT '관심영양소_트렌스지방',
--     `fat` INT NULL,
--     `carb` INT NULL,
--     PRIMARY KEY (`food_id`),
--     CONSTRAINT `FK_Food_TO_Nutrient` FOREIGN KEY (`food_id`) REFERENCES `Food` (`food_id`) ON DELETE CASCADE ON UPDATE CASCADE
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3. UserFoodHistory 테이블 생성 (user_id를 VARCHAR(50)로 변경)
CREATE TABLE IF NOT EXISTS `UserFoodHistory` (
    `history_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `food_id` VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `consumed_at` DATETIME NULL,
    `portion_size_g` DECIMAL(10,2) NULL,
    `Field` VARCHAR(255) NULL,
    `food_name` VARCHAR(200) NOT NULL,
    PRIMARY KEY (`history_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_food_id` (`food_id`),
    CONSTRAINT `FK_User_TO_UserFoodHistory` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `FK_Food_TO_UserFoodHistory` FOREIGN KEY (`food_id`) REFERENCES `Food` (`food_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 4. health_score 테이블 생성 (user_id를 VARCHAR(50)로 변경)
CREATE TABLE IF NOT EXISTS `health_score` (
    `history_id` BIGINT NOT NULL,
    `user_id` VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `food_id` VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `reference_value` INT NULL COMMENT '영양성분함량기준량',
    `kcal` INT NULL,
    `positive_score` INT NULL COMMENT 'SUM(권장영양소 9가지의 %값) / 9',
    `negative_score` INT NULL COMMENT 'SUM(제한영양소 3가지의 %값) / 3',
    `final_score` INT NULL COMMENT '최종점수 = 권장영양소점수 - 제한영양소점수',
    `food_grade` VARCHAR(100) NULL COMMENT '90점 이상: 우수한 영양식품, 75-89점: 좋은 영양식품, 50-74점: 보통 영양식품, 25-49점: 영양개선 필요, 24점 이하: 영양소 부족',
    `calc_method` VARCHAR(100) NULL COMMENT '한국식 점수 계산식 : 한국영양점수 = (단백질 + 섬유질 + 칼슘 + 철분) - (나트륨 + 당분 + 포화지방)',
    PRIMARY KEY (`history_id`, `user_id`, `food_id`),
    CONSTRAINT `FK_UserFoodHistory_TO_health_score` FOREIGN KEY (`history_id`) REFERENCES `UserFoodHistory` (`history_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 5. HealthReport 테이블 생성 (user_id를 VARCHAR(50)로 변경)
CREATE TABLE IF NOT EXISTS `HealthReport` (
    `report_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `period_type` ENUM('daily', 'weekly', 'monthly') NULL,
    `start_date` DATE NULL,
    `end_date` DATE NULL,
    `summary_json` JSON NULL,
    `generated_at` TIMESTAMP NULL,
    PRIMARY KEY (`report_id`),
    INDEX `idx_user_id` (`user_id`),
    CONSTRAINT `FK_User_TO_HealthReport` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 6. UserPreferences 테이블 생성 (user_id를 VARCHAR(50)로 변경)
CREATE TABLE IF NOT EXISTS `UserPreferences` (
    `pref_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `preference_type` VARCHAR(100) NULL,
    `preference_value` VARCHAR(255) NULL,
    `updated_at` TIMESTAMP NULL,
    PRIMARY KEY (`pref_id`),
    INDEX `idx_user_id` (`user_id`),
    CONSTRAINT `FK_User_TO_UserPreferences` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 7. disease_allergy_profile 테이블 생성 (user_id를 VARCHAR(50)로 변경)
CREATE TABLE IF NOT EXISTS `disease_allergy_profile` (
    `profile_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `allergy_name` VARCHAR(100) NULL,
    `disease_name` VARCHAR(100) NULL,
    PRIMARY KEY (`profile_id`),
    INDEX `idx_user_id` (`user_id`),
    CONSTRAINT `FK_User_TO_disease_allergy_profile` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 완료 메시지
SELECT 'ERDCloud 스키마 테이블 생성 완료!' AS message;
SELECT '주의: user_id는 VARCHAR(50)으로 설정되었습니다 (users 테이블과 일치)' AS note;
