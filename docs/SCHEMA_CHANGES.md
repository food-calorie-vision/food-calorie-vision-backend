# 데이터베이스 스키마 변경 사항

## 📅 변경 일자: 2025-11-07

## 🎯 변경 목적
ERDCloud에서 설계한 표준 스키마를 프로젝트에 통합하여 팀 전체가 동일한 데이터베이스 구조를 사용하도록 함.

## 📊 변경 내용

### 1. 새로 추가된 테이블 (ERDCloud 스키마)

#### `Food` 테이블
```sql
CREATE TABLE `Food` (
    `food_id` VARCHAR(200) PRIMARY KEY,
    `image_ref` VARCHAR(255),
    `category` VARCHAR(100),
    `food_class_1` VARCHAR(100),  -- 식품 대분류
    `food_class_2` VARCHAR(100),  -- 식품 중분류
    `food_name` VARCHAR(200)
);
```
**용도**: 음식 기본 정보 저장

#### `Nutrient` 테이블
```sql
CREATE TABLE `Nutrient` (
    `food_id` VARCHAR(200) PRIMARY KEY,
    `kcal` INT,
    `protein` INT,      -- 권장영양소
    `Fiber` INT,        -- 권장영양소
    `vitamin_a` INT,    -- 권장영양소
    `vitamin_c` INT,    -- 권장영양소
    `vitamin_e` INT,    -- 권장영양소
    `calcium` INT,      -- 권장영양소
    `iron` INT,         -- 권장영양소
    `potassium` INT,    -- 권장영양소
    `magnessium` INT,   -- 권장영양소
    `saturated_fat` INT,  -- 제한영양소
    `added_sugar` INT,    -- 제한영양소
    `sodium` INT,         -- 제한영양소
    `cholesterol` INT,    -- 관심영양소
    `trans_Fat` INT,      -- 관심영양소
    `fat` INT,
    `carb` INT,
    FOREIGN KEY (`food_id`) REFERENCES `Food` (`food_id`)
);
```
**용도**: 음식별 상세 영양소 정보

#### `UserFoodHistory` 테이블
```sql
CREATE TABLE `UserFoodHistory` (
    `history_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` VARCHAR(50) NOT NULL,
    `food_id` VARCHAR(200) NOT NULL,
    `consumed_at` DATETIME,
    `portion_size_g` DECIMAL(10,2),
    `food_name` VARCHAR(200) NOT NULL,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
    FOREIGN KEY (`food_id`) REFERENCES `Food` (`food_id`)
);
```
**용도**: 사용자의 음식 섭취 기록 (meal_records의 ERDCloud 버전)

#### `health_score` 테이블
```sql
CREATE TABLE `health_score` (
    `history_id` BIGINT,
    `user_id` VARCHAR(50),
    `food_id` VARCHAR(200),
    `reference_value` INT,      -- 영양성분함량기준량
    `kcal` INT,
    `positive_score` INT,       -- 권장영양소 점수
    `negative_score` INT,       -- 제한영양소 점수
    `final_score` INT,          -- 최종 점수
    `food_grade` VARCHAR(100),  -- 영양 등급
    `calc_method` VARCHAR(100), -- 계산 방식
    PRIMARY KEY (`history_id`, `user_id`, `food_id`)
);
```
**용도**: 섭취한 음식의 영양 점수 계산 및 저장

#### `HealthReport` 테이블
```sql
CREATE TABLE `HealthReport` (
    `report_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` VARCHAR(50) NOT NULL,
    `period_type` ENUM('daily', 'weekly', 'monthly'),
    `start_date` DATE,
    `end_date` DATE,
    `summary_json` JSON,
    `generated_at` TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
);
```
**용도**: 일/주/월별 건강 리포트 생성 및 저장

#### `UserPreferences` 테이블
```sql
CREATE TABLE `UserPreferences` (
    `pref_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` VARCHAR(50) NOT NULL,
    `preference_type` VARCHAR(100),
    `preference_value` VARCHAR(255),
    `updated_at` TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
);
```
**용도**: 사용자 선호도 설정 저장

#### `disease_allergy_profile` 테이블
```sql
CREATE TABLE `disease_allergy_profile` (
    `profile_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` VARCHAR(50) NOT NULL,
    `allergy_name` VARCHAR(100),
    `disease_name` VARCHAR(100),
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
);
```
**용도**: 사용자의 질병 및 알레르기 정보 저장

### 2. 유지되는 기존 테이블

#### `users` ✅
- 구조 변경 없음
- `user_id`: VARCHAR(50) 유지
- 모든 기능 정상 작동

#### `user_health_info` ✅
- 구조 변경 없음
- 기존 회원가입/로그인 기능과 연동

#### `meal_records` ✅
- 구조 변경 없음
- `UserFoodHistory`와 병행 사용 가능
- 기존 데이터 보존

#### `daily_scores` ✅
- 구조 변경 없음
- 점수 계산 기능 정상 작동

#### `food_analyses` ✅
- 구조 변경 없음
- 이미지 분석 결과 저장

#### `chat_messages` ✅
- 구조 변경 없음
- 챗봇 대화 기록

#### `meal_recommendations` ✅
- 구조 변경 없음
- 식단 추천 기능

#### `food_nutrients` ⚠️
- **절대 수정 금지**
- Alembic이 자동으로 무시
- 팀원이 관리하는 테이블

## 🔄 마이그레이션 방법

### 방법 1: SQL 파일 실행 (권장)
```bash
mysql -u user -p database < erdcloud_schema.sql
```

### 방법 2: MySQL 워크벤치
1. `erdcloud_schema.sql` 파일 열기
2. 실행 버튼 클릭
3. 결과 확인

## 📝 코드 변경 사항

### 1. `app/db/models.py`
- 7개의 새로운 모델 클래스 추가
- 기존 모델 유지 (호환성)
- 타입 힌트 및 주석 추가

### 2. `app/db/__init__.py`
- 새로운 모델 export 추가
- 기존 import 유지

### 3. `alembic/env.py`
- `include_object` 함수 업데이트
- ERDCloud 테이블 자동 마이그레이션 제외
- `food_nutrients` 무시 유지

### 4. 새로운 파일
- `erdcloud_schema.sql`: 테이블 생성 SQL
- `ERDCloud_Migration_Guide.md`: 마이그레이션 가이드
- `SCHEMA_CHANGES.md`: 이 문서

## 🎯 다음 작업

### 백엔드
1. [ ] Food 조회 API 구현
2. [ ] Nutrient 조회 API 구현
3. [ ] UserFoodHistory CRUD API 구현
4. [ ] health_score 계산 로직 구현
5. [ ] HealthReport 생성 API 구현

### 프론트엔드
1. [ ] 음식 검색 기능 (Food 테이블 사용)
2. [ ] 영양소 정보 표시 (Nutrient 테이블 사용)
3. [ ] 식사 기록 UI (UserFoodHistory 사용)
4. [ ] 건강 리포트 페이지 (HealthReport 사용)

### 데이터
1. [ ] Food 테이블 데이터 입력
2. [ ] Nutrient 테이블 데이터 입력
3. [ ] 기존 meal_records → UserFoodHistory 마이그레이션 (선택)

## ⚠️ 주의사항

### 1. food_id 타입 차이
- **기존**: INT
- **ERDCloud**: VARCHAR(200)
- **영향**: 기존 meal_records와 직접 호환 불가
- **해결**: 새로운 데이터부터 ERDCloud 스키마 사용

### 2. 데이터 일관성
- 외래 키 제약조건 활성화
- CASCADE 옵션으로 데이터 무결성 보장

### 3. 성능 고려사항
- VARCHAR 기본 키 사용 시 인덱스 크기 증가
- 필요시 복합 인덱스 추가

## 📊 테이블 관계도

```
users (VARCHAR user_id)
  ├─→ user_health_info
  ├─→ meal_records (기존)
  ├─→ daily_scores
  ├─→ chat_messages
  ├─→ meal_recommendations
  ├─→ UserFoodHistory (신규)
  ├─→ HealthReport (신규)
  ├─→ UserPreferences (신규)
  └─→ disease_allergy_profile (신규)

Food (VARCHAR food_id)
  ├─→ Nutrient
  └─→ UserFoodHistory

UserFoodHistory
  └─→ health_score
```

## 🔍 변경 이력

| 날짜 | 변경 내용 | 작성자 |
|------|-----------|--------|
| 2025-11-07 | ERDCloud 스키마 통합 | AI Assistant |
| 2025-11-07 | 모델 파일 업데이트 | AI Assistant |
| 2025-11-07 | 마이그레이션 가이드 작성 | AI Assistant |

## 📞 문의

스키마 관련 문의사항은 팀 회의에서 논의해주세요.

