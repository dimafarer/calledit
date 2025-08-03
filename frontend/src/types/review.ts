export interface ReviewableSection {
  section: string;
  improvable: boolean;
  questions: string[];
  reasoning: string;
}

export interface ReviewData {
  review_id: string;
  reviewable_sections: ReviewableSection[];
}

export interface ImprovementRequest {
  section: string;
}

export interface ImprovementAnswers {
  section: string;
  answers: string[];
}

export interface ReviewState {
  reviewableSections: ReviewableSection[];
  currentQuestions: string[];
  showImprovementModal: boolean;
  improvingSection: string | null;
  isImproving: boolean;
  reviewStatus: string;
}