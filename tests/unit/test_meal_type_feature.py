"""meal_type 기능 단위 테스트"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.db.models import UserFoodHistory
from app.services.food_history_service import create_food_history


class TestMealTypeFeature:
    """meal_type 기능 테스트"""
    
    @pytest.mark.asyncio
    async def test_create_food_history_with_meal_type(self):
        """음식 섭취 기록 생성 시 meal_type이 올바르게 저장되는지 테스트"""
        # Arrange
        mock_session = AsyncMock()
        user_id = 1
        food_id = "test_food_123"
        food_name = "테스트 음식"
        meal_type = "breakfast"
        
        # Act
        history = await create_food_history(
            session=mock_session,
            user_id=user_id,
            food_id=food_id,
            food_name=food_name,
            meal_type=meal_type
        )
        
        # Assert
        assert history.user_id == user_id
        assert history.food_id == food_id
        assert history.food_name == food_name
        assert history.meal_type == meal_type
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_food_history_default_meal_type(self):
        """meal_type 미지정 시 기본값(lunch)이 설정되는지 테스트"""
        # Arrange
        mock_session = AsyncMock()
        user_id = 1
        food_id = "test_food_456"
        food_name = "테스트 음식2"
        
        # Act
        history = await create_food_history(
            session=mock_session,
            user_id=user_id,
            food_id=food_id,
            food_name=food_name
            # meal_type 미지정
        )
        
        # Assert
        assert history.meal_type == "lunch"  # 기본값
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_meal_type_enum_values(self):
        """meal_type이 올바른 ENUM 값만 허용하는지 테스트"""
        # Arrange
        valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
        mock_session = AsyncMock()
        
        # Act & Assert
        for meal_type in valid_meal_types:
            history = await create_food_history(
                session=mock_session,
                user_id=1,
                food_id="test_food",
                food_name="테스트",
                meal_type=meal_type
            )
            assert history.meal_type == meal_type
    
    def test_user_food_history_model_meal_type(self):
        """UserFoodHistory 모델에 meal_type 필드가 있는지 테스트"""
        # Arrange & Act
        history = UserFoodHistory(
            user_id=1,
            food_id="test_food",
            food_name="테스트 음식",
            meal_type="dinner"
        )
        
        # Assert
        assert hasattr(history, 'meal_type')
        assert history.meal_type == "dinner"
    
    def test_user_food_history_repr_includes_meal_type(self):
        """UserFoodHistory의 __repr__에 meal_type이 포함되는지 테스트"""
        # Arrange
        history = UserFoodHistory(
            history_id=1,
            user_id=1,
            food_id="test_food",
            food_name="테스트 음식",
            meal_type="snack"
        )
        
        # Act
        repr_str = repr(history)
        
        # Assert
        assert "meal_type=snack" in repr_str
        assert "history_id=1" in repr_str
        assert "food_name=테스트 음식" in repr_str


class TestMealTypeAPI:
    """meal_type API 테스트"""
    
    def test_save_food_request_schema_with_meal_type(self):
        """SaveFoodRequest 스키마에 meal_type이 포함되는지 테스트"""
        from app.api.v1.schemas.vision import SaveFoodRequest
        
        # Arrange
        request_data = {
            "userId": 1,
            "foodName": "테스트 음식",
            "mealType": "breakfast",
            "ingredients": ["재료1", "재료2"]
        }
        
        # Act
        request = SaveFoodRequest(**request_data)
        
        # Assert
        assert request.user_id == 1
        assert request.food_name == "테스트 음식"
        assert request.meal_type == "breakfast"
        assert request.ingredients == ["재료1", "재료2"]
    
    def test_save_food_request_schema_default_meal_type(self):
        """SaveFoodRequest에서 meal_type 기본값이 lunch인지 테스트"""
        from app.api.v1.schemas.vision import SaveFoodRequest
        
        # Arrange
        request_data = {
            "userId": 1,
            "foodName": "테스트 음식"
            # mealType 미지정
        }
        
        # Act
        request = SaveFoodRequest(**request_data)
        
        # Assert
        assert request.meal_type == "lunch"
    
    def test_save_food_response_schema_with_meal_type(self):
        """SaveFoodResponse 스키마에 meal_type이 포함되는지 테스트"""
        from app.api.v1.schemas.vision import SaveFoodResponse
        
        # Arrange
        response_data = {
            "historyId": 1,
            "foodId": "test_food_123",
            "foodName": "테스트 음식",
            "mealType": "dinner",
            "consumedAt": "2025-11-20T12:00:00",
            "portionSizeG": 150.0
        }
        
        # Act
        response = SaveFoodResponse(**response_data)
        
        # Assert
        assert response.history_id == 1
        assert response.food_id == "test_food_123"
        assert response.food_name == "테스트 음식"
        assert response.meal_type == "dinner"
        assert response.consumed_at == "2025-11-20T12:00:00"
        assert response.portion_size_g == 150.0
    
    def test_save_recipe_request_schema_with_meal_type(self):
        """SaveRecipeRequest 스키마에 meal_type이 포함되는지 테스트"""
        from app.api.v1.schemas.recipe import SaveRecipeRequest, NutritionInfo
        
        # Arrange
        request_data = {
            "recipe_name": "닭가슴살 샐러드",
            "actual_servings": 1.5,
            "meal_type": "lunch",
            "nutrition_info": {
                "calories": 350,
                "protein": "35g",
                "carbs": "20g",
                "fat": "10g"
            }
        }
        
        # Act
        request = SaveRecipeRequest(**request_data)
        
        # Assert
        assert request.recipe_name == "닭가슴살 샐러드"
        assert request.actual_servings == 1.5
        assert request.meal_type == "lunch"
        assert request.nutrition_info.calories == 350


class TestMealTypeIntegration:
    """meal_type 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_food_history_with_details_includes_meal_type(self):
        """get_user_food_history_with_details가 meal_type을 포함하는지 테스트"""
        from app.services.food_history_service import get_user_food_history_with_details
        
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        
        # Mock 데이터 설정
        mock_row = MagicMock()
        mock_row.history_id = 1
        mock_row.user_id = 1
        mock_row.food_id = "test_food"
        mock_row.food_name = "테스트 음식"
        mock_row.meal_type = "breakfast"
        mock_row.consumed_at = datetime.now()
        mock_row.portion_size_g = 100.0
        mock_row.food_class_1 = "밥류"
        mock_row.food_class_2 = "밥"
        mock_row.category = "한식"
        mock_row.image_ref = None
        
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result
        
        # Act
        histories, total = await get_user_food_history_with_details(
            session=mock_session,
            user_id=1
        )
        
        # Assert
        assert len(histories) == 1
        assert histories[0]["meal_type"] == "breakfast"
        assert histories[0]["food_name"] == "테스트 음식"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

