# Timezone Edge Case Test Runner

## How to Run Tests

### Manual Testing Process:
1. Open your CalledIt streaming interface
2. For each test case in `timezone_edge_case_tests.json`:
   - Copy the prompt
   - Paste into the streaming interface
   - Record the results below

### Test Results Template:

## Test Results (Date: 2025-06-27)

### Test 1: Market close time varies by timezone and market (4:00 PM EST for NYSE)
**Prompt:** "The stock market will close above 5000 by market close today"
**Agent Response:**
- Verification Date: 2025-06-27 16:00:00
- Date Reasoning: Today is 2025-06-27, and the current time is 15:18:42 EDT according to the provided context. The US ...
- Issues Found: None

### Test 2: Vague time reference - what constitutes 'morning'?
**Prompt:** "It will rain tomorrow morning"
**Agent Response:**
- Verification Date: 2025-06-28 11:00:00
- Date Reasoning: Today is 2025-06-27, so 'tomorrow' refers to 2025-06-28. 'Morning' typically spans from early mornin...
- Issues Found: None

### Test 3: Midnight ambiguity - start or end of day?
**Prompt:** "The meeting will start at midnight"
**Agent Response:**
- Verification Date: 2025-06-28 00:00:00
- Date Reasoning: Today is 2025-06-27 with the current time being 15:18:42 EDT. The prediction states that 'the meetin...
- Issues Found: None

### Test 4: Subjective time range - evening varies by person/season
**Prompt:** "Sarah will call me back this evening"
**Agent Response:**
- Verification Date: 2025-06-27 23:59:59
- Date Reasoning: Today is 2025-06-27, and the current time is 15:18:42 EDT. The prediction refers to 'this evening', ...
- Issues Found: None

### Test 5: Cross-day boundary with specific time
**Prompt:** "The package will arrive before noon tomorrow"
**Agent Response:**
- Verification Date: 2025-06-28 12:00:00
- Date Reasoning: Today is 2025-06-27, so 'tomorrow' refers to 2025-06-28. The prediction specifies 'before noon', wit...
- Issues Found: None

### Test 6: Business day varies by timezone and industry
**Prompt:** "Bitcoin will hit $100k by end of business day"
**Agent Response:**
- Verification Date: 2025-06-27 17:00:00
- Date Reasoning: Today is 2025-06-27, and the current time is 15:18:42 EDT. The prediction refers to 'end of business...
- Issues Found: None

### Test 7: Specific time but subjective outcome
**Prompt:** "The sunrise will be beautiful at 6:30 AM"
**Agent Response:**
- Verification Date: 2025-06-28 06:30:00
- Date Reasoning: Today is 2025-06-27, and the current time is 15:18:42 EDT. Since the prediction mentions a sunrise a...
- Issues Found: None

### Test 8: Specific time with 'past' - when to verify?
**Prompt:** "My flight will be delayed past its 11:45 PM departure time"
**Agent Response:**
- Verification Date: 2025-06-27 23:45:00
- Date Reasoning: Today is 2025-06-27, and the current time is 15:18:42 EDT. The prediction references a flight with a...
- Issues Found: None

### Test 9: Time range rather than specific time
**Prompt:** "The restaurant will be busy during lunch rush"
**Agent Response:**
- Verification Date: 2025-06-27 13:00:00
- Date Reasoning: Today is 2025-06-27, and the current time is 15:18:42 EDT, which is after the typical lunch rush. Th...
- Issues Found: None

### Test 10: Week boundary ambiguity - Friday 5 PM? Sunday midnight?
**Prompt:** "I'll finish this project by the end of the week"
**Agent Response:**
- Verification Date: 2025-06-29 23:59:59
- Date Reasoning: Today is 2025-06-27 (Friday), and the current time is 15:18:42 EDT. The prediction states 'by the en...
- Issues Found: None

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