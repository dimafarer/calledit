# MCP Sampling Frontend Implementation Plan

## Current Status
✅ **Backend Complete**: MCP Sampling pattern fully implemented with WebSocket routing  
🔄 **Frontend Needed**: UI components for improvement workflow

## Implementation Overview

### Phase 1: Core UI Components (Priority 1)
**Estimated Time**: 2-3 hours

#### 1.1 ReviewableSection Component
```tsx
interface ReviewableSectionProps {
  section: string;
  content: string;
  isReviewable: boolean;
  onImprove: (section: string) => void;
}
```
- Highlight improvable sections with visual indicators
- Mobile-friendly click targets (44px minimum)
- High contrast borders for accessibility

#### 1.2 ImprovementModal Component  
```tsx
interface ImprovementModalProps {
  questions: string[];
  section: string;
  onSubmit: (answers: string[]) => void;
  onCancel: () => void;
}
```
- Display improvement questions from ReviewAgent
- Text input fields for user answers
- Submit/cancel actions

#### 1.3 StreamingCall Enhancement
- Add review state management
- Handle `review_complete` WebSocket messages
- Integrate ReviewableSection components
- Show improvement loading states

### Phase 2: WebSocket Integration (Priority 1)
**Estimated Time**: 1-2 hours

#### 2.1 WebSocket Message Handlers
```tsx
// Add to existing StreamingCall component
const handleReviewComplete = (data: ReviewData) => {
  setReviewableSections(data.reviewable_sections);
};

const handleImprovementQuestions = (data: QuestionData) => {
  setCurrentQuestions(data.questions);
  setShowImprovementModal(true);
};

const handleImprovedResponse = (data: CallResponse) => {
  setResponse(data);
  setReviewableSections([]);
};
```

#### 2.2 WebSocket Actions
```tsx
const requestImprovement = (section: string) => {
  websocket.send(JSON.stringify({
    action: 'improve_section',
    section: section
  }));
};

const submitAnswers = (answers: string[], section: string) => {
  websocket.send(JSON.stringify({
    action: 'improvement_answers',
    answers: answers,
    section: section
  }));
};
```

### Phase 3: State Management (Priority 2)
**Estimated Time**: 1 hour

#### 3.1 Review State Interface
```tsx
interface ReviewState {
  reviewableSections: ReviewableSection[];
  currentQuestions: string[];
  showImprovementModal: boolean;
  improvingSection: string | null;
  isImproving: boolean;
}
```

#### 3.2 State Updates
- Track which sections are reviewable
- Manage improvement modal visibility
- Handle loading states during regeneration

### Phase 4: Visual Design (Priority 2)
**Estimated Time**: 1-2 hours

#### 4.1 Highlighting Styles
```css
.reviewable-section {
  border: 2px dashed #007bff;
  border-radius: 4px;
  padding: 8px;
  cursor: pointer;
  position: relative;
}

.reviewable-section::after {
  content: "✨ Click to improve";
  position: absolute;
  top: -10px;
  right: 8px;
  background: #007bff;
  color: white;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}
```

#### 4.2 Mobile Optimization
- Touch-friendly interaction areas
- Responsive modal design
- Clear visual feedback for actions

## File Structure

```
frontend/src/components/
├── StreamingCall.tsx           # Enhanced with review functionality
├── ReviewableSection.tsx       # New: Highlightable sections
├── ImprovementModal.tsx        # New: Question/answer interface
└── ImprovementIndicator.tsx    # New: Visual improvement hints

frontend/src/types/
└── review.ts                   # New: Review-related interfaces

frontend/src/hooks/
└── useReviewState.ts           # New: Review state management
```

## Implementation Steps

### Step 1: Create Base Components
1. Create `ReviewableSection.tsx` with highlighting
2. Create `ImprovementModal.tsx` with form handling
3. Add TypeScript interfaces for review data

### Step 2: Enhance StreamingCall
1. Add review state management
2. Integrate WebSocket message handlers
3. Render ReviewableSection components conditionally

### Step 3: Add Visual Polish
1. Implement highlighting styles
2. Add loading indicators
3. Test mobile responsiveness

### Step 4: Integration Testing
1. Test with actual WebSocket backend
2. Verify improvement workflow end-to-end
3. Test error handling and edge cases

## Success Criteria

### Functional Requirements
- ✅ Sections highlight when reviewable
- ✅ Clicking section triggers improvement questions
- ✅ User can provide answers and regenerate
- ✅ Updated response replaces original
- ✅ Mobile-friendly interaction

### Technical Requirements  
- ✅ WebSocket integration working
- ✅ State management clean and predictable
- ✅ TypeScript types complete
- ✅ Error handling robust
- ✅ Loading states clear

### UX Requirements
- ✅ Visual feedback immediate and clear
- ✅ Improvement process intuitive
- ✅ Mobile touch targets adequate
- ✅ Accessibility standards met

## Testing Strategy

### Unit Tests
- ReviewableSection click handling
- ImprovementModal form validation
- WebSocket message parsing

### Integration Tests
- Complete improvement workflow
- WebSocket connection handling
- State synchronization

### E2E Tests
- User clicks section → sees questions → provides answers → gets improved response
- Mobile device testing
- Error scenario handling

## Estimated Timeline

- **Phase 1**: 2-3 hours (Core components)
- **Phase 2**: 1-2 hours (WebSocket integration)  
- **Phase 3**: 1 hour (State management)
- **Phase 4**: 1-2 hours (Visual design)

**Total**: 5-8 hours for complete implementation

## Next Actions

1. **Create ReviewableSection component** with basic highlighting
2. **Enhance StreamingCall** to handle review messages
3. **Add ImprovementModal** for user interaction
4. **Test with existing WebSocket backend**
5. **Polish visual design and mobile UX**

The backend MCP Sampling infrastructure is complete and tested. Frontend implementation can begin immediately with existing WebSocket routes working.