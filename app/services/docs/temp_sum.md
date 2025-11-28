# 레시피 추천 시스템 성능 최적화 및 UX 개선 구현 가이드

## 1. 핵심 목표
*   **속도 향상**: "응(네)" 응답 시 에이전트 추론 없이 즉시 처리 (목표: 3초 이내).
*   **신뢰도 향상**: 선(先) 건강 체크 후 유해성 고지.
*   **UX 개선**: 단계별 피드백("건강 확인 중" -> "생성 중") 제공.

## 2. 표준 처리 프로세스 (6단계 흐름)
1.  **사용자 입력 감지**: "응", "네", "보여줘" 등 긍정 확답.
2.  **의도 파악 및 건강 체크 (AI)**: `RecipeService.quick_analyze_intent` 호출 (Agent 건너뜀).
3.  **유해성 판단 (Yes/No)**: `disease_conflict` / `allergy_conflict` 확인.
4.  **경고 UI 노출 (Frontend Interaction)**: 위험 시 `HEALTH_CONFIRMATION` 반환 -> 프론트엔드 경고 팝업 (빨간색 ChatBubble).
5.  **사용자 최종 선택**: `proceed` (그대로) vs `health_first` (건강하게).
6.  **맞춤형 레시피 생성**: 선택에 따른 최적화된 프롬프트로 즉시 생성.

---

## 3. 백엔드 구현 요구사항 (`app/api/v1/routes/chat_v2.py`)

**파일 위치**: `food-calorie-vision-backend/app/api/v1/routes/chat_v2.py` (신규 생성)
**참고 파일**: `food-calorie-vision-backend/app/api/v1/routes/chat.py`

### 주요 변경 사항 (함수: `handle_chat_message`)

*   **라인 270~380 구간 (Agent 실행 로직) 대체**:
    *   기존: `_invoke_agent_response` 내부에서 `agent_executor.ainvoke` 무조건 실행.
    *   변경: `mode="execute"` 또는 긍정 확답 감지 시 **단축 경로(Shortcut)** 진입.

#### 단축 경로 로직 (Pseudo-code)
```python
# 1. 건강 체크 (필수)
quick_analysis = await recipe_service.quick_analyze_intent(
    user=current_user,
    intent_text=request.message,
    # ... context (diseases, allergies) ...
)

# 2. 위험 감지 시 즉시 리턴 (Short-circuit)
# 기존 chat.py의 requires_confirmation 로직 재사용
if quick_analysis.get("disease_conflict") or quick_analysis.get("allergy_conflict"):
    # 경고 메시지 구성 (기존 로직 참조)
    confirm_message = f"{quick_analysis.get('user_message')}\n\n{combined_warning}\n\n건강을 우선해서 레시피를 조정할까요?"
    
    # HEALTH_CONFIRMATION 페이로드 반환
    return ChatMessageResponse(..., action_type="HEALTH_CONFIRMATION", message=confirm_message, ...)

# 3. 안전하거나 사용자가 이미 선택(safety_mode)한 경우 -> 레시피 생성 직행
# AgentExecutor 생성/실행 과정 생략!
result = await recipe_service.get_recipe_recommendations(
    user=current_user,
    user_request=request.message,
    safety_mode=safety_mode, # proceed or health_first
    # ... context ...
)

# 4. 응답 변환 (Dict -> JSON String)
ai_response_payload = json.dumps(result, ensure_ascii=False)
return ChatMessageResponse(..., response=ai_response_payload, ...)
```

---

## 4. 서비스 및 프롬프트 최적화 (`app/services/recipe_recommendation_service.py`)

**파일 위치**: `food-calorie-vision-backend/app/services/recipe_recommendation_service.py`

### A. `_build_recipe_prompt` 함수 수정 (라인 120~)
*   **목표**: 중복된 지시사항 제거 및 `safety_mode`에 따른 명확한 지시.
*   **삭제 대상 (필수)**:
    *   **`2. 건강 상태(질병, 알레르기)를 반드시 고려하세요...`** -> 이미 앞단에서 체크했으므로 삭제. LLM 혼란 방지.
    *   **`5. 사용자가 칼로리/나트륨이 높거나... 확인 질문을 포함하세요.`** -> 이미 질문했으므로 삭제.
    *   **`8. 사용자가 원하는 음식이 건강에 부적합한 경우... 설명을 포함하세요.`** -> 이미 설명했으므로 삭제.
*   **추가/수정**:
    *   `intent_metadata` 또는 `safety_mode` 인자를 활용하여 프롬프트 서두에 강력한 지시 추가.
    *   `if safety_mode == "proceed"`: "**경고 무시 및 원래 맛 유지**. 사용자가 건강 위험을 감수하고 원래 레시피를 강력히 원함."
    *   `if safety_mode == "health_first"`: "**건강 최우선 변형**. 원래 메뉴의 맛을 내되, 저염/저지방 재료로 적극적으로 대체할 것."

### B. `get_recipe_recommendations` 함수 (라인 230~)
*   **수정**: `safety_mode` 파라미터를 명시적으로 받고, 이를 `_build_recipe_prompt`에 전달.

---

## 5. 프론트엔드 UX 요구사항 (`app/recommend/page.tsx`)

**파일 위치**: `food-calorie-vision-frontend/src/app/recommend/page.tsx`

### A. 로딩 메시지 개선 (`requestRecipeAgentResponse`)
*   **라인 365 (`funnyRecipeLoadingMessages`)**:
    *   기존: "GPT가 요리책 읽는 중..."
    *   변경:
        1.  "사용자의 질환과 알러지를 확인하고 있습니다..." (초기 2초)
        2.  "건강에 맞는 맞춤 레시피를 생성 중입니다..." (이후)

### B. 경고 팝업 처리 (`handleRecipeAgentResponse`)
*   **라인 305**: `HEALTH_CONFIRMATION` 액션 타입 처리 로직 확인. (이미 구현됨, 백엔드 연동만 확인)
*   **버튼 클릭 시**: "그대로 진행해줘" -> `safety_mode="proceed"`, "건강하게 바꿔줘" -> `safety_mode="health_first"` 파라미터 전송 확인.
