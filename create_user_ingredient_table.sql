-- 사용자 식재료 테이블 생성 (Roboflow 분석 결과 저장)

CREATE TABLE IF NOT EXISTS `UserIngredient` (
    `ingredient_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL COMMENT '사용자 ID',
    `ingredient_name` VARCHAR(100) NOT NULL COMMENT '식재료 이름',
    `count` INT NOT NULL DEFAULT 1 COMMENT '수량',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일',
    `is_used` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '사용 여부',
    PRIMARY KEY (`ingredient_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_user_id_is_used` (`user_id`, `is_used`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='사용자 식재료 테이블';


