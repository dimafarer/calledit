# Timezone Edge Case Test Runner

## How to Run Tests

### Manual Testing Process:
1. Open your CalledIt streaming interface
2. For each test case in `timezone_edge_case_tests.json`:
   - Copy the prompt
   - Paste into the streaming interface
   - Record the results below

### Test Results Template:

## Test Results (Date: ______)

### Test 1: Market Close
**Prompt:** "The stock market will close above 5000 by market close today"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

### Test 2: Tomorrow Morning  
**Prompt:** "It will rain tomorrow morning"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

### Test 3: Midnight Ambiguity
**Prompt:** "The meeting will start at midnight"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

### Test 4: This Evening
**Prompt:** "Sarah will call me back this evening"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

### Test 5: Before Noon Tomorrow
**Prompt:** "The package will arrive before noon tomorrow"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

### Test 6: End of Business Day
**Prompt:** "Bitcoin will hit $100k by end of business day"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

### Test 7: Specific Time
**Prompt:** "The sunrise will be beautiful at 6:30 AM"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

### Test 8: Past Specific Time
**Prompt:** "My flight will be delayed past its 11:45 PM departure time"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

### Test 9: Lunch Rush
**Prompt:** "The restaurant will be busy during lunch rush"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

### Test 10: End of Week
**Prompt:** "I'll finish this project by the end of the week"
**Agent Response:**
- Verification Date: ___________
- Date Reasoning: ___________
- Issues Found: ___________

## Analysis Framework

For each test, evaluate:

### ✅ **Correct Behaviors:**
- [ ] Time converted from 12-hour to 24-hour format
- [ ] Verification date in user's local timezone context
- [ ] Reasonable interpretation of vague time references
- [ ] Clear date reasoning provided

### ❌ **Issues to Look For:**
- [ ] UTC references in agent response
- [ ] Incorrect timezone conversion
- [ ] Unreasonable time interpretations
- [ ] Missing or unclear date reasoning
- [ ] Tool usage problems (multiple current_time calls)

### 🔧 **Common Fixes Needed:**
- Improve vague time interpretation
- Better business hours handling
- Cross-day boundary logic
- Ambiguous time resolution