// TypeScript interfaces define the shape of our API response data
export interface VerificationMethod {
  source: string[]; // Array of verification sources
  criteria: string[]; // Array of verification criteria  
  steps: string[]; // Array of verification steps
}

export interface NovaResponse {
  prediction_statement: string; // The prediction text
  verification_date: string; // When prediction will be verified
  verification_method: VerificationMethod; // Nested verification details
  initial_status: string; // Initial prediction status
}

export interface APIResponse {
  results: NovaResponse[]; // Array of prediction responses
}