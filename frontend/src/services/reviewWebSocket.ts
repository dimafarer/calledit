/**
 * WebSocket service extension for review functionality
 */

export interface ReviewSection {
  section: string;
  improvable: boolean;
  questions: string[];
  reasoning: string;
}

export interface ReviewCompleteData {
  reviewable_sections: ReviewSection[];
}

export const handleReviewMessages = (
  message: any,
  setReviewStatus: (status: string) => void,
  setReviewSections: (sections: ReviewSection[]) => void,
  setIsReviewComplete: (complete: boolean) => void
) => {
  switch (message.type) {
    case 'status':
      if (message.status === 'reviewing') {
        setReviewStatus('🔍 Reviewing response for improvements...');
        setIsReviewComplete(false);
      }
      break;
      
    case 'review_complete':
      const reviewData: ReviewCompleteData = message.data;
      setReviewSections(reviewData.reviewable_sections);
      setIsReviewComplete(true);
      
      const improvableCount = reviewData.reviewable_sections.filter(s => s.improvable).length;
      if (improvableCount > 0) {
        setReviewStatus(`✨ Found ${improvableCount} sections that could be improved`);
      } else {
        setReviewStatus('✅ Response looks good - no improvements suggested');
      }
      break;
      
    case 'complete':
      if (message.status === 'ready_for_improvements') {
        setReviewStatus('💡 Click highlighted sections to improve them');
      }
      break;
  }
};