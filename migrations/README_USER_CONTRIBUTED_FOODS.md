# 사용자 기여 음식 테이블 마이그레이션

## 개요

사용자가 추가한 음식을 공식 `food_nutrients` DB와 분리하여 관리하는 `user_contributed_foods` 테이블을 생성합니다.

---

## 실행 방법

### 1. MySQL 접속

```bash
mysql -u root -p food_calorie_db
```

### 2. SQL 파일 실행

```sql
source migrations/create_user_contributed_foods_table.sql;
```

또는

```bash
mysql -u root -p food_calorie_db < migrations/create_user_contributed_foods_table.sql
```

---

## 테이블 구조

### 주요 컬럼:

- `food_id` (PK): `USER_{user_id}_{timestamp}` 형식
- `user_id`: 기여한 사용자 ID
- `food_name`: 음식 이름
- `usage_count`: 사용 횟수 (자동 증가)
- 영양소 정보 (NRF9.3 기준)

### 인덱스:

- `idx_user_id`: 사용자별 음식 조회
- `idx_nutrient_name`: 음식명 검색
- `idx_usage_count`: 인기 음식 조회

---

## 확인

```sql
-- 테이블 생성 확인
SHOW TABLES LIKE 'user_contributed_foods';

-- 구조 확인
DESC user_contributed_foods;

-- 인덱스 확인
SHOW INDEX FROM user_contributed_foods;
```

---

## 롤백

```sql
DROP TABLE IF EXISTS user_contributed_foods;
```

---

## 관련 문서

- [USER_CONTRIBUTED_FOODS_GUIDE.md](../USER_CONTRIBUTED_FOODS_GUIDE.md) - 전체 시스템 가이드
- [FOOD_MATCHING_IMPROVEMENT_REPORT.md](../FOOD_MATCHING_IMPROVEMENT_REPORT.md) - 매칭 로직 개선 보고서

