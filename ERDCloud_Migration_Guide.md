# ERDCloud 스키마 마이그레이션 가이드

## 📋 개요

이 문서는 기존 데이터베이스를 ERDCloud 스키마로 마이그레이션하는 방법을 설명합니다.

## 🎯 마이그레이션 전략

### 유지되는 테이블
- ✅ `users` - 현재 구조 유지 (user_id: VARCHAR(50))
- ✅ `food_nutrients` - 절대 수정 금지

### 새로 추가되는 ERDCloud 테이블
1. `Food` - 음식 기본 정보
2. `Nutrient` - 음식별 영양소 정보  
3. `UserFoodHistory` - 사용자 음식 섭취 기록
4. `health_score` - 음식 점수 계산
5. `HealthReport` - 건강 리포트
6. `UserPreferences` - 사용자 선호도
7. `disease_allergy_profile` - 질병/알레르기 프로필

### 기존 테이블 (호환성 유지)
- `user_health_info`
- `meal_records` (UserFoodHistory와 병행 사용)
- `daily_scores`
- `food_analyses`
- `chat_messages`
- `meal_recommendations`

## 🚀 마이그레이션 단계

### 1단계: ERDCloud 스키마 테이블 생성

MySQL 워크벤치나 CLI에서 실행:

```bash
# MySQL CLI
mysql -u your_user -p your_database < erdcloud_schema.sql

# 또는 워크벤치에서 erdcloud_schema.sql 파일 실행
```

### 2단계: 테이블 생성 확인

```sql
-- 생성된 테이블 확인
SHOW TABLES;

-- 각 테이블 구조 확인
DESCRIBE Food;
DESCRIBE Nutrient;
DESCRIBE UserFoodHistory;
DESCRIBE health_score;
DESCRIBE HealthReport;
DESCRIBE UserPreferences;
DESCRIBE disease_allergy_profile;
```

### 3단계: 외래 키 제약조건 확인

```sql
-- 외래 키 확인
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM
    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE
    TABLE_SCHEMA = 'your_database_name'
    AND REFERENCED_TABLE_NAME IS NOT NULL;
```

## 📊 테이블 관계도

```
users (user_id: VARCHAR)
  ├─→ UserFoodHistory (user_id)
  │     └─→ health_score (history_id, user_id, food_id)
  ├─→ HealthReport (user_id)
  ├─→ UserPreferences (user_id)
  └─→ disease_allergy_profile (user_id)

Food (food_id: VARCHAR)
  ├─→ Nutrient (food_id)
  └─→ UserFoodHistory (food_id)
```

## 🔄 데이터 마이그레이션 (선택사항)

기존 `meal_records` 데이터를 `UserFoodHistory`로 마이그레이션하려면:

```sql
-- meal_records → UserFoodHistory 마이그레이션 예시
-- 주의: food_id 타입이 다르므로 매핑 필요
INSERT INTO UserFoodHistory (user_id, food_id, consumed_at, portion_size_g, food_name)
SELECT 
    mr.user_id,
    CAST(mr.food_id AS CHAR(200)),  -- INT → VARCHAR 변환
    mr.meal_time,
    mr.portion * 100,  -- 1인분 → 그램 변환 (가정)
    'Unknown'  -- food_name은 별도로 조인 필요
FROM meal_records mr
WHERE mr.food_id IS NOT NULL;
```

## ⚠️ 주의사항

### 1. food_id 타입 차이
- **기존 `meal_records`**: `food_id` INT
- **ERDCloud `Food`**: `food_id` VARCHAR(200)
- **해결**: 데이터 매핑 테이블 생성 또는 새로운 데이터 사용

### 2. user_id 일관성
- 모든 테이블에서 `user_id`는 `VARCHAR(50)`로 통일
- `users.user_id`를 참조

### 3. 외래 키 제약조건
- `ON DELETE CASCADE`: 부모 레코드 삭제 시 자식 레코드도 삭제
- `ON UPDATE CASCADE`: 부모 레코드 업데이트 시 자식 레코드도 업데이트

### 4. food_nutrients 테이블
- **절대 수정 금지**
- Alembic이 자동으로 무시하도록 설정됨

## 🧪 테스트

### 1. 테이블 생성 테스트

```sql
-- Food 테이블 테스트
INSERT INTO Food (food_id, food_name, category) 
VALUES ('TEST001', '테스트 음식', '테스트');

-- Nutrient 테이블 테스트
INSERT INTO Nutrient (food_id, kcal, protein, carb, fat)
VALUES ('TEST001', 100, 10, 20, 5);

-- UserFoodHistory 테스트 (user_id는 실제 존재하는 값 사용)
INSERT INTO UserFoodHistory (user_id, food_id, food_name, consumed_at)
VALUES ('hyuk', 'TEST001', '테스트 음식', NOW());

-- 테스트 데이터 삭제 (역순으로)
DELETE FROM health_score WHERE food_id = 'TEST001';
DELETE FROM UserFoodHistory WHERE food_id = 'TEST001';
DELETE FROM Nutrient WHERE food_id = 'TEST001';
DELETE FROM Food WHERE food_id = 'TEST001';
```

### 2. 외래 키 제약조건 테스트

```sql
-- 존재하지 않는 user_id로 삽입 시도 (실패해야 함)
INSERT INTO UserFoodHistory (user_id, food_id, food_name)
VALUES ('nonexistent_user', 'TEST001', 'Test');
-- ERROR: Cannot add or update a child row: a foreign key constraint fails

-- 존재하지 않는 food_id로 삽입 시도 (실패해야 함)
INSERT INTO UserFoodHistory (user_id, food_id, food_name)
VALUES ('hyuk', 'NONEXISTENT', 'Test');
-- ERROR: Cannot add or update a child row: a foreign key constraint fails
```

## 🔧 문제 해결

### 외래 키 제약조건 오류

```sql
-- 외래 키 제약조건 일시 비활성화 (주의해서 사용)
SET FOREIGN_KEY_CHECKS=0;

-- 작업 수행...

-- 외래 키 제약조건 다시 활성화
SET FOREIGN_KEY_CHECKS=1;
```

### 테이블 삭제 (필요시)

```sql
-- 역순으로 삭제 (외래 키 때문)
DROP TABLE IF EXISTS health_score;
DROP TABLE IF EXISTS UserFoodHistory;
DROP TABLE IF EXISTS Nutrient;
DROP TABLE IF EXISTS Food;
DROP TABLE IF EXISTS HealthReport;
DROP TABLE IF EXISTS UserPreferences;
DROP TABLE IF EXISTS disease_allergy_profile;
```

## 📝 다음 단계

1. ✅ ERDCloud 스키마 테이블 생성 완료
2. ⏭️ 백엔드 서비스 코드 작성 (Food, Nutrient 조회 API)
3. ⏭️ 프론트엔드 연동
4. ⏭️ 데이터 마이그레이션 (필요시)

## 📞 문의

문제가 발생하면 다음을 확인하세요:
1. MySQL 버전 (8.0+ 권장)
2. 문자셋 (utf8mb4)
3. 외래 키 제약조건 활성화 여부
4. 사용자 권한 (CREATE, ALTER, REFERENCES)

