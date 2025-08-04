import { useState, useCallback } from 'react';
import { ReviewableSection, ReviewState } from '../types/review';

export const useReviewState = () => {
  const [reviewState, setReviewState] = useState<ReviewState>({
    reviewableSections: [],
    currentQuestions: [],
    showImprovementModal: false,
    improvingSection: null,
    isImproving: false,
    reviewStatus: ''
  });

  const updateReviewSections = useCallback((sections: ReviewableSection[]) => {
    console.log('📋 Review State: Updating sections:', sections);
    setReviewState(prev => ({
      ...prev,
      reviewableSections: sections,
      reviewStatus: sections.length > 0 
        ? `✨ Found ${sections.length} sections that could be improved`
        : '✅ Response looks good - no improvements suggested'
    }));
  }, []);

  const startImprovement = useCallback((section: string, questions: string[]) => {
    console.log('🚀 Review State: Starting improvement for section:', section, 'with questions:', questions);
    setReviewState(prev => ({
      ...prev,
      improvingSection: section,
      currentQuestions: questions,
      showImprovementModal: true
    }));
  }, []);

  const setImprovementInProgress = useCallback((inProgress: boolean) => {
    console.log('⚙️ Review State: Setting improvement in progress:', inProgress);
    setReviewState(prev => ({
      ...prev,
      isImproving: inProgress,
      showImprovementModal: false,
      reviewStatus: inProgress 
        ? '🔄 Improving response with your input...'
        : prev.reviewStatus
    }));
  }, []);

  const clearReviewState = useCallback(() => {
    console.log('🧹 Review State: Clearing all review state');
    setReviewState({
      reviewableSections: [],
      currentQuestions: [],
      showImprovementModal: false,
      improvingSection: null,
      isImproving: false,
      reviewStatus: ''
    });
  }, []);

  const cancelImprovement = useCallback(() => {
    setReviewState(prev => ({
      ...prev,
      showImprovementModal: false,
      improvingSection: null,
      currentQuestions: []
    }));
  }, []);

  const setReviewStatus = useCallback((status: string) => {
    setReviewState(prev => ({
      ...prev,
      reviewStatus: status
    }));
  }, []);

  return {
    reviewState,
    updateReviewSections,
    startImprovement,
    setImprovementInProgress,
    clearReviewState,
    cancelImprovement,
    setReviewStatus
  };
};