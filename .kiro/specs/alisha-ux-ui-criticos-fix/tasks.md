# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - UX/UI Critical Issues Exploration
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the 4 UX/UI bugs exist
  - **Scoped PBT Approach**: Test concrete failing cases for each of the 4 issues
  - Test that observation messages appear in user history (should be hidden)
  - Test that asterisk actions display as text instead of executing animations
  - Test that user_name can be inconsistent or incorrect across components
  - Test that vision system makes excessive API calls without rate limiting
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bugs exist)
  - Document counterexamples found to understand root cause
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Normal UX/UI Functionality Preservation
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for normal interactions
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Test that normal user messages continue to display correctly in history with 3-word titles
  - Test that regular Alisha responses without animations continue to show as text normally
  - Test that core identity system maintains Alisha as assistant and Cami as user correctly
  - Test that vision analysis continues to provide effective screen analysis within safe limits
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for Alisha UX/UI Critical Issues

  - [x] 3.1 Implement history observation filtering (Limpieza del Historial)
    - Enhance existing filter in static/js/app.js lines 1068-1072 to completely hide observation messages
    - Expand filter conditions to catch all observation message variants: "[Alisha observa]", "[Alisha sugiere]", "[Sugerencia", etc.
    - Ensure filtered messages are logged separately but never displayed to user
    - Update _cargarSesion function to filter observation messages from loaded sessions
    - Test that observation messages are hidden from user history panel but preserved in logs
    - _Bug_Condition: Messages starting with "[Alisha" appear in user history_
    - _Expected_Behavior: Observation messages hidden from user but logged separately_
    - _Preservation: Normal user messages continue to display with 3-word titles_
    - _Requirements: 2.1, 3.1_

  - [x] 3.2 Implement Live2D animation integration (Sincronización de Animación)
    - Modify tts_engine.py _limpiar_texto_para_tts function to detect asterisk actions instead of stripping them
    - Parse asterisk content (*gira la cabeza*, *sonríe*, etc.) to identify animation types
    - Add animation state variables to alisha_bridge.py (ANIMATION_STATE, animation parameter functions)
    - Map common actions to Live2D parameters: *gira la cabeza* → gaze_x/gaze_y, *sonríe* → mouth_amplitude
    - Send animation commands to alisha_bridge.py instead of removing asterisk text
    - Integrate with existing EMOTION and state management in bridge
    - Test that asterisk actions trigger Live2D animations instead of appearing as text
    - _Bug_Condition: Asterisk actions (*action*) display as text in chat_
    - _Expected_Behavior: Asterisk actions execute as Live2D animations visually_
    - _Preservation: Non-animation responses continue to show as text normally_
    - _Requirements: 2.2, 3.2_

  - [x] 3.3 Implement identity consistency enforcement (Corrección de Identidad)
    - Set default user name to "Cami" in web_app.py perfil initialization
    - Add validation in web_app.py to prevent user_name from being set to "Alisha"
    - Update all identity references across components to use consistent "Cami" value
    - Ensure user_name variable is consistently "Cami" throughout all system components
    - Add identity validation checks in key interaction points
    - Test that system never refers to user as "Alisha" and always uses "Cami"
    - _Bug_Condition: user_name can be "Alisha" or inconsistent across components_
    - _Expected_Behavior: user_name is consistently "Cami" throughout system_
    - _Preservation: Core identity system maintains Alisha as assistant correctly_
    - _Requirements: 2.3, 3.3_

  - [x] 3.4 Implement vision API rate limiting (Optimización de Visión)
    - Add intelligent API call throttling to gemini_vision.py GeminiVision class
    - Track API call timestamps and frequency in _capture_loop method
    - Implement exponential backoff for 429 errors with configurable retry delays
    - Add configurable rate limits (max 30 calls per minute) to prevent CAPTCHA triggers
    - Cache recent results to reduce unnecessary API calls
    - Add rate limiting state variables and cooldown management
    - Test that vision system prevents 429 errors and CAPTCHA triggers while maintaining analysis
    - _Bug_Condition: Vision system makes excessive API calls causing 429 errors_
    - _Expected_Behavior: Rate limiting prevents errors while maintaining effective analysis_
    - _Preservation: Vision analysis continues to provide effective screen analysis within limits_
    - _Requirements: 2.4, 3.4_

  - [x] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - UX/UI Critical Issues Fixed
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bugs are fixed)
    - Verify observation messages are hidden from user history
    - Verify asterisk actions execute as Live2D animations
    - Verify user_name is consistently "Cami" throughout system
    - Verify vision system has proper rate limiting
    - _Requirements: Expected Behavior Properties from design_

  - [x] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Normal UX/UI Functionality Preserved
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm normal user messages still display correctly in history
    - Confirm regular responses without animations still show as text
    - Confirm core identity system still maintains correct roles
    - Confirm vision analysis still works effectively within safe limits
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Verify the 4 main UX/UI issues are resolved:
    1. Limpieza del Historial - "[Alisha observa]" messages hidden from user history
    2. Sincronización de Animación - Asterisk actions execute as Live2D animations
    3. Corrección de Identidad - user_name consistently "Cami" throughout system
    4. Optimización de Visión - Rate limiting prevents Google CAPTCHA triggers
  - Confirm preservation of existing functionality for normal interactions
  - Document any remaining issues or edge cases discovered during testing