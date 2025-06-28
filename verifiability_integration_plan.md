# Verifiability Category Integration Plan

## Overview
Add automatic verifiability categorization to the CalledIt streaming lambda, display it in the UI, and save it to DynamoDB for all predictions.

## Implementation Steps

### Step 1: Update Agent System Prompt
**Goal:** Modify the Strands agent to include verifiability categorization in all responses

**Changes needed:**
- Update system prompt in streaming lambda to include verifiability category requirement
- Add JSON field: `"verifiable_category": "one_of_five_categories"`
- Define the 5 categories clearly in the prompt

**Files to modify:**
- Streaming lambda handler (agent system prompt)

### Step 2: Update Response Processing
**Goal:** Extract and validate verifiability category from agent responses

**Changes needed:**
- Parse `verifiable_category` field from agent JSON response
- Validate category is one of the 5 allowed values
- Handle missing or invalid categories with fallback logic

**Files to modify:**
- Streaming lambda response processing logic

### Step 3: Update UI Display
**Goal:** Show verifiability category in the Call Details section

**Changes needed:**
- Add verifiability category display in Make a Call (Streaming) interface
- Style the category with appropriate visual indicators
- Position near other call metadata

**Files to modify:**
- React component for Call Details display
- CSS/styling for category display

### Step 4: Update DynamoDB Schema
**Goal:** Save verifiability category with prediction data

**Changes needed:**
- Add `verifiable_category` field to DynamoDB item structure
- Ensure field is saved with all other prediction metadata
- Update any existing queries/indexes if needed

**Files to modify:**
- DynamoDB write operations in streaming lambda
- Data model/schema documentation

### Step 5: Testing & Validation
**Goal:** Ensure verifiability categorization works end-to-end

**Testing needed:**
- Test all 5 category types with sample predictions
- Verify UI displays categories correctly
- Confirm DynamoDB saves categories properly
- Test error handling for invalid categories

## Technical Details

### 5 Verifiability Categories:
1. **`agent_verifiable`** - Agent can verify with pure reasoning/knowledge
2. **`current_tool_verifiable`** - Verifiable with current_time tool
3. **`strands_tool_verifiable`** - Requires Strands library tools
4. **`api_tool_verifiable`** - Requires custom API/MCP integration
5. **`human_verifiable_only`** - Requires human observation/assessment

### JSON Response Format:
```json
{
  "prediction_statement": "...",
  "verification_date": "...",
  "date_reasoning": "...",
  "verifiable_category": "agent_verifiable",
  "verification_method": {...},
  "initial_status": "pending"
}
```

### UI Display Format:
```
Call Details:
- Prediction: "Bitcoin will hit $100k tomorrow"
- Verification Date: 2025-06-28 23:59:59
- Verifiability: 🔧 Strands-Tool-Verifiable
- Status: Pending
```

### DynamoDB Item Structure:
```json
{
  "prediction_id": "...",
  "prediction_statement": "...",
  "verification_date": "...",
  "verifiable_category": "strands_tool_verifiable",
  "created_at": "...",
  "status": "pending"
}
```

## Implementation Priority:
1. **Step 1** - Update agent system prompt (highest impact)
2. **Step 2** - Update response processing (required for functionality)
3. **Step 4** - Update DynamoDB schema (data persistence)
4. **Step 3** - Update UI display (user visibility)
5. **Step 5** - Testing & validation (quality assurance)

## Success Criteria:
- ✅ All agent responses include valid verifiability category
- ✅ UI displays verifiability category for all predictions
- ✅ DynamoDB stores verifiability category with all records
- ✅ Error handling works for invalid/missing categories
- ✅ Categories match our 5-category framework

Ready to start with Step 1?