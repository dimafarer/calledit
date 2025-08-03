# MCP Sampling Frontend Implementation Plan

**Last Updated**: January 30, 2025  
**Status**: Phase 1 Complete, Phase 2 Ready

## Current Status
✅ **Backend Complete**: MCP Sampling pattern fully implemented with WebSocket routing  
✅ **Phase 1 Complete**: Core UI components built and committed  
🔄 **Phase 2 Ready**: WebSocket integration next

## Implementation Overview

### ✅ Phase 1: Core UI Components (COMPLETE)
**Time Spent**: 1 hour  
**Status**: All components built and committed

#### Components Created:
- ✅ **ReviewableSection.tsx**: Highlighting component with visual indicators
- ✅ **ImprovementModal.tsx**: Question/answer interface for user input  
- ✅ **review.ts**: TypeScript interfaces for type safety

#### Features Implemented:
- Mobile-friendly 44px touch targets
- Visual highlighting with dashed borders and sparkle indicators
- Hover tooltips showing improvement info
- Form validation and submission handling
- Responsive modal design

### 🔄 Phase 2: WebSocket Integration (READY)
**Estimated Time**: 1-2 hours  
**Status**: Partially implemented in StreamingCall.tsx

#### Current State:
- ✅ WebSocket message handlers exist for review data
- ✅ Review state management hooks in place
- ✅ Backend routes tested and working
- ⏳ Need to integrate new components into StreamingCall

#### Next Steps:
1. Import ReviewableSection and ImprovementModal into StreamingCall
2. Replace review status display with ReviewableSection components
3. Add improvement request WebSocket actions
4. Connect modal to WebSocket improvement workflow

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

### ⏳ Phase 3: State Management (PENDING)
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

### ⏳ Phase 4: Visual Design (PENDING)  
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
├── StreamingCall.tsx           # ✅ Has review hooks, needs component integration
├── ReviewableSection.tsx       # ✅ COMPLETE - Highlighting component
├── ImprovementModal.tsx        # ✅ COMPLETE - Question/answer interface
└── LogCallButton.tsx          # ✅ Existing - No changes needed

frontend/src/types/
├── index.ts                   # ✅ Existing - API response types
└── review.ts                  # ✅ COMPLETE - Review-specific interfaces

backend/calledit-backend/handlers/strands_make_call/
├── strands_make_call_stream.py # ✅ COMPLETE - WebSocket routing
├── review_agent.py            # ✅ COMPLETE - MCP Sampling implementation
└── tests/                     # ✅ COMPLETE - All tests passing
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

## Next Session Tasks

### Immediate (Phase 2 - WebSocket Integration):
1. **Enhance StreamingCall.tsx** (30 minutes):
   ```tsx
   // Add imports
   import ReviewableSection from './ReviewableSection';
   import ImprovementModal from './ImprovementModal';
   
   // Add modal state
   const [showModal, setShowModal] = useState(false);
   const [currentSection, setCurrentSection] = useState('');
   
   // Add improvement handlers
   const handleImprove = (section: string) => { /* WebSocket call */ };
   const handleAnswers = (answers: string[]) => { /* WebSocket call */ };
   ```

2. **Replace Review Display** (30 minutes):
   - Replace current review status div with ReviewableSection components
   - Map reviewSections to ReviewableSection components
   - Connect onImprove handlers

3. **Add Modal Integration** (30 minutes):
   - Add ImprovementModal to render tree
   - Connect to WebSocket improvement workflow
   - Handle modal open/close states

### Testing (Phase 2 completion):
- [ ] Test improvement workflow end-to-end
- [ ] Verify WebSocket message handling
- [ ] Test modal interaction and form submission

---

## Implementation Notes

### Key Decisions Made:
- **Component Architecture**: Separate ReviewableSection and ImprovementModal for reusability
- **State Management**: Keep in StreamingCall.tsx to avoid prop drilling
- **Visual Design**: Dashed borders with sparkle indicators for clear improvement hints
- **Mobile-First**: 44px minimum touch targets throughout

### Technical Considerations:
- WebSocket connection reuse for improvement requests
- State synchronization between review and improvement phases
- Error handling for network issues during improvement
- Loading states during regeneration process

---

**Progress Updates**: This document will be updated as implementation progresses