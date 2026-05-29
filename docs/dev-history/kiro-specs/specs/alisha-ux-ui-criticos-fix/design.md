# Alisha UX/UI Critical Issues Bugfix Design

## Overview

This design addresses four critical UX/UI issues in Alisha that significantly impact user experience: (1) technical observation messages cluttering user history, (2) animation actions appearing as text instead of executing visually, (3) identity confusion where the system may call the user "Alisha" instead of "Cami", and (4) Google Vision API rate limiting issues causing CAPTCHA triggers. The fix approach involves implementing history filtering, Live2D animation integration, identity validation, and intelligent rate limiting to preserve Alisha's core functionality while eliminating these user-facing problems.

## Glossary

- **Bug_Condition (C)**: The conditions that trigger each of the four UX/UI issues - observation messages in history, text animations, identity confusion, and rate limiting problems
- **Property (P)**: The desired behavior for each issue - hidden observations, visual animations, correct identity, and proper rate limiting
- **Preservation**: Existing functionality that must remain unchanged - normal chat display, regular responses, core identity system, and effective vision analysis
- **[Alisha observa]**: Technical observation messages that should be hidden from user history but logged separately
- **Live2D Integration**: The connection between asterisk actions (*action*) and the Live2D model for visual animation execution
- **user_name**: The system variable that should consistently be "Cami" throughout all interactions
- **Rate Limiting**: Intelligent throttling of Google Gemini Vision API calls to prevent 429 errors and CAPTCHA triggers

## Bug Details

### Bug Condition

The bugs manifest in four distinct scenarios:

1. **History Pollution**: When Alisha makes automatic observations, the system displays "[Alisha observa]" and "[Alisha sugiere]" messages in the user's chat history
2. **Animation Failure**: When Alisha needs to perform animations, the system writes actions between asteriscos (e.g., *gira la cabeza*) as text instead of executing them visually through Live2D
3. **Identity Confusion**: When processing interactions, the system may incorrectly identify the user as "Alisha" instead of using the correct name "Cami"
4. **Rate Limiting Issues**: When using the vision system, excessive API calls to Google Gemini Vision cause 429 errors and CAPTCHA challenges

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type SystemInteraction
  OUTPUT: boolean
  
  RETURN (input.messageType == "observation" AND input.visibleInHistory == true)
         OR (input.messageType == "animation" AND input.executionMode == "text")
         OR (input.userIdentity == "Alisha" AND input.actualUser == "Cami")
         OR (input.apiCallRate > SAFE_RATE_LIMIT AND input.apiErrors.contains("429"))
END FUNCTION
```

### Examples

- **History Issue**: User sees "[Alisha observa] Mirá vos lo que tiene la Camila, che es un objeto super chulo!" in their chat history instead of it being hidden
- **Animation Issue**: User sees "*gira la cabeza*" as text in chat instead of seeing Alisha's Live2D model actually turn her head
- **Identity Issue**: System processes interaction with user_name="Alisha" instead of user_name="Cami", causing confusion in responses
- **Rate Limiting Issue**: Vision system makes 10+ API calls per minute, triggering Google's rate limits and CAPTCHA challenges

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Normal user messages must continue to display in history with 3-word titles as before
- Regular Alisha responses without animations must continue to show as text normally
- Core identity system must continue to maintain Alisha as assistant and Cami as user
- Vision analysis must continue to provide effective screen analysis when operating within rate limits

**Scope:**
All inputs that do NOT involve the four specific bug conditions should be completely unaffected by this fix. This includes:
- Normal chat conversations and responses
- Non-animation text interactions
- Correct identity scenarios
- Vision system usage within safe rate limits

## Hypothesized Root Cause

Based on the bug analysis and code examination, the most likely issues are:

1. **History Filtering Missing**: The web interface (static/js/app.js) has partial filtering logic but observation messages still appear in user history
   - Current filter in app.js line 1068-1072 exists but may not be comprehensive
   - Messages are saved to memory_db with "[Alisha observa]" entries that should be hidden

2. **Animation System Disconnected**: Asterisk actions are processed as text rather than triggering Live2D animations
   - TTS engine (tts_engine.py line 638) strips asterisk content instead of processing it
   - No bridge exists between asterisk detection and alisha_bridge.py Live2D parameters

3. **Identity Variable Inconsistency**: The user_name variable is not consistently set to "Cami" across all system components
   - web_app.py uses perfil.get("nombre", "") which may be empty or incorrect
   - Multiple components may have hardcoded or inconsistent identity references

4. **Vision Rate Limiting Absent**: GeminiVision class lacks intelligent rate limiting for API calls
   - gemini_vision.py makes calls without tracking frequency or implementing backoff
   - No protection against 429 errors or CAPTCHA triggers from excessive requests

## Correctness Properties

Property 1: Bug Condition - History Observation Hiding

_For any_ system interaction where observation messages are generated (isBugCondition returns true for observation type), the fixed system SHALL hide "[Alisha observa]" and "[Alisha sugiere]" messages from the user's visible chat history while preserving them in hidden logs.

**Validates: Requirements 2.1**

Property 2: Bug Condition - Animation Execution

_For any_ system interaction where animation actions are detected (asterisk-wrapped text), the fixed system SHALL execute the corresponding Live2D animation visually instead of displaying the text in chat.

**Validates: Requirements 2.2**

Property 3: Bug Condition - Identity Consistency

_For any_ system interaction processing, the fixed system SHALL ensure user_name is consistently "Cami" throughout all components and never refer to the user as "Alisha".

**Validates: Requirements 2.3**

Property 4: Bug Condition - Rate Limiting Protection

_For any_ vision system usage, the fixed system SHALL implement appropriate rate limiting to prevent 429 errors and CAPTCHA triggers while maintaining effective analysis capability.

**Validates: Requirements 2.4**

Property 5: Preservation - Normal Chat Functionality

_For any_ input that does not involve the four bug conditions (normal messages, non-animations, correct identity, safe API usage), the fixed system SHALL produce exactly the same behavior as the original system, preserving all existing chat and interaction functionality.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `static/js/app.js`

**Function**: Message filtering and display logic

**Specific Changes**:
1. **Enhanced History Filtering**: Strengthen the existing filter (lines 1068-1072) to completely hide observation messages
   - Expand filter conditions to catch all observation message variants
   - Ensure filtered messages are logged separately but never displayed to user

**File**: `tts_engine.py`

**Function**: `limpiar_texto_para_tts`

**Specific Changes**:
2. **Animation Detection and Processing**: Replace asterisk stripping (line 638) with animation trigger system
   - Parse asterisk content to identify animation types
   - Send animation commands to alisha_bridge.py instead of removing text
   - Map common actions (*gira la cabeza*, *sonríe*, etc.) to Live2D parameters

**File**: `alisha_bridge.py`

**Function**: Add animation parameter functions

**Specific Changes**:
3. **Live2D Animation Bridge**: Add animation state variables and functions
   - Add ANIMATION_STATE variable to track current animation
   - Add functions to translate text actions to Live2D parameters
   - Integrate with existing EMOTION and state management

**File**: `web_app.py`

**Function**: User identity initialization and management

**Specific Changes**:
4. **Identity Consistency Enforcement**: Ensure user_name is always "Cami"
   - Set default user name to "Cami" in perfil initialization
   - Add validation to prevent user_name from being set to "Alisha"
   - Update all identity references to use consistent "Cami" value

**File**: `gemini_vision.py`

**Function**: `GeminiVision` class API call management

**Specific Changes**:
5. **Rate Limiting Implementation**: Add intelligent API call throttling
   - Track API call timestamps and frequency
   - Implement exponential backoff for 429 errors
   - Add configurable rate limits (e.g., max 30 calls per minute)
   - Cache recent results to reduce unnecessary API calls

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that simulate each bug condition and assert that the problems occur. Run these tests on the UNFIXED code to observe failures and understand the root causes.

**Test Cases**:
1. **History Pollution Test**: Generate observation messages and verify they appear in user history (will fail on unfixed code)
2. **Animation Text Test**: Trigger asterisk actions and verify they appear as text instead of animations (will fail on unfixed code)
3. **Identity Confusion Test**: Check user_name consistency across system components (will fail on unfixed code)
4. **Rate Limiting Test**: Make rapid vision API calls and verify 429 errors occur (will fail on unfixed code)

**Expected Counterexamples**:
- Observation messages visible in chat history when they should be hidden
- Animation actions displayed as text instead of executing visually
- user_name variable inconsistencies or incorrect identity references
- API rate limit errors and CAPTCHA triggers from excessive calls

### Fix Checking

**Goal**: Verify that for all inputs where the bug conditions hold, the fixed system produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixedSystem(input)
  ASSERT expectedBehavior(result)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug conditions do NOT hold, the fixed system produces the same result as the original system.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalSystem(input) = fixedSystem(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for normal interactions, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Normal Chat Preservation**: Verify regular messages continue to display correctly in history
2. **Response Display Preservation**: Verify non-animation responses continue to show as text
3. **Core Identity Preservation**: Verify Alisha-as-assistant and Cami-as-user relationships remain intact
4. **Vision Analysis Preservation**: Verify effective screen analysis continues within safe rate limits

### Unit Tests

- Test observation message filtering in web interface
- Test asterisk action detection and Live2D parameter mapping
- Test user_name consistency validation across components
- Test rate limiting logic with various API call patterns

### Property-Based Tests

- Generate random chat interactions and verify normal messages display correctly
- Generate random animation triggers and verify Live2D integration works
- Generate random identity scenarios and verify consistent user_name usage
- Generate random vision usage patterns and verify rate limiting prevents errors

### Integration Tests

- Test complete chat flow with observation messages properly hidden
- Test full animation sequence from asterisk detection to Live2D execution
- Test identity consistency across multi-component interactions
- Test vision system with rate limiting under various usage scenarios