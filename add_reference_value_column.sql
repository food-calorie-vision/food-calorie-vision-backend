-- food_nutrients 테이블에 reference_value 컬럼 추가
-- 영양성분함량기준 (g) - 기본값 100g

ALTER TABLE food_nutrients 
ADD COLUMN reference_value FLOAT DEFAULT 100.0 COMMENT '영양성분함량기준 (g)';

-- 기존 데이터에 100.0 설정 (원본 데이터가 100g 기준이므로)
UPDATE food_nutrients 
SET reference_value = 100.0 
WHERE reference_value IS NULL;

-- 확인
SELECT food_id, nutrient_name, reference_value, unit, protein, carb, fat
FROM food_nutrients
LIMIT 5;

