-- ============================================================================
-- 고객센터 테이블 스키마 (공지사항 + 문의하기)
-- ============================================================================
-- 
-- 테이블 목록:
-- 1. Announcement - 공지사항
-- 2. Inquiry - 문의하기
-- 
-- ============================================================================

-- 데이터베이스 선택
USE tempdb;

-- ============================================================================
-- 1. Announcement (공지사항) 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS `Announcement` (
    `announcement_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '공지사항 ID',
    `title` VARCHAR(200) NOT NULL COMMENT '공지사항 제목',
    `content` TEXT NOT NULL COMMENT '공지사항 내용',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '작성일',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '활성 여부 (숨김/표시)',
    `view_count` INT NOT NULL DEFAULT 0 COMMENT '조회수',
    PRIMARY KEY (`announcement_id`),
    INDEX `idx_created_at` (`created_at` DESC),
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
COMMENT='공지사항 테이블';

-- ============================================================================
-- 2. Inquiry (문의하기) 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS `Inquiry` (
    `inquiry_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '문의 ID',
    `user_id` BIGINT NOT NULL COMMENT '사용자 ID (필수)',
    `nickname` VARCHAR(50) NOT NULL COMMENT '닉네임 (문의 당시)',
    `email` VARCHAR(100) NOT NULL COMMENT '이메일 (문의 당시)',
    `inquiry_type` VARCHAR(50) NOT NULL COMMENT '문의 유형',
    `subject` VARCHAR(200) NOT NULL COMMENT '문의 제목',
    `content` TEXT NOT NULL COMMENT '문의 내용',
    `status` ENUM('pending', 'in_progress', 'completed') NOT NULL DEFAULT 'pending' COMMENT '답변 상태',
    `response` TEXT NULL COMMENT '답변 내용',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '문의 작성일',
    `responded_at` TIMESTAMP NULL COMMENT '답변 완료일',
    PRIMARY KEY (`inquiry_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at` DESC),
    CONSTRAINT `FK_User_TO_Inquiry` FOREIGN KEY (`user_id`) 
        REFERENCES `User` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
COMMENT='문의하기 테이블 (로그인 필수)';

-- ============================================================================
-- 초기 데이터 삽입 (공지사항 샘플)
-- ============================================================================

INSERT INTO `Announcement` (`title`, `content`, `created_at`, `is_active`) VALUES
('업데이트 안내', 
'안녕하세요, KCalculator입니다.\n\n새로운 기능이 추가되었습니다:\n- AI 기반 음식 인식 정확도 향상\n- 레시피 추천 알고리즘 개선\n- 식단 분석 UI/UX 개선\n\n더욱 발전하는 KCalculator가 되겠습니다.\n감사합니다.', 
'2024-10-24 10:00:00', TRUE),

('서비스 점검 안내', 
'서비스 점검 안내드립니다.\n\n점검 일시: 2024년 10월 15일 (화) 02:00 ~ 06:00\n점검 내용: 서버 성능 개선 및 보안 업데이트\n\n점검 시간 동안 서비스 이용이 일시 중단됩니다.\n이용에 불편을 드려 죄송합니다.', 
'2024-10-15 14:00:00', TRUE),

('이벤트 당첨자 발표', 
'[10월 건강 챌린지] 이벤트 당첨자를 발표합니다! 🎉\n\n당첨자 여러분께는 개별적으로 이메일을 발송해드렸습니다.\n당첨되신 분들 축하드리며, 앞으로도 건강한 식습관을 유지하시길 바랍니다.\n\n감사합니다.', 
'2024-10-03 16:00:00', TRUE),

('앱 UI/UX 개편 안내', 
'KCalculator 앱이 더욱 사용하기 편리하게 개편되었습니다.\n\n주요 변경사항:\n- 메인 화면 재디자인\n- 식사일기 분석 화면 개선\n- 레시피 추천 채팅 기능 추가\n- 더 빠른 로딩 속도\n\n새로워진 KCalculator를 경험해보세요!', 
'2024-09-27 11:00:00', TRUE),

('추석 연휴 고객지원 안내', 
'추석 연휴 기간 고객센터 운영 안내\n\n휴무 기간: 2024년 9월 14일 ~ 9월 18일\n정상 운영: 2024년 9월 19일부터\n\n연휴 기간 중 문의하신 내용은 9월 19일부터 순차적으로 답변드리겠습니다.\n풍성하고 행복한 추석 명절 되시기 바랍니다.', 
'2024-09-13 09:00:00', TRUE);

-- ============================================================================
-- 완료 메시지
-- ============================================================================

SELECT 'Customer Service 테이블이 성공적으로 생성되었습니다!' AS message;
SELECT '공지사항 샘플 데이터가 삽입되었습니다!' AS message;

