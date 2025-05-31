/**
 * Type Definitions for the Called It Application
 * 
 * This file contains TypeScript interfaces that define the shape of data
 * used throughout the application, particularly for API responses.
 */

/**
 * VerificationMethod Interface
 * 
 * Defines the structure for verification methods associated with predictions.
 * Each method includes sources to check, criteria for verification, and steps to follow.
 */
export interface VerificationMethod {
  /** Array of sources that can be used to verify the prediction */
  source: string[];
  
  /** Array of criteria that determine if the prediction is verified */
  criteria: string[];
  
  /** Array of steps to follow when verifying the prediction */
  steps: string[];
}

/**
 * NovaResponse Interface
 * 
 * Represents a single prediction with its associated verification details.
 * This is the core data structure for individual predictions in the application.
 */
export interface NovaResponse {
  /** The main prediction statement text */
  prediction_statement: string;
  
  /** The date when the prediction was made */
  prediction_date: string;
  
  /** The date when the prediction should be verified */
  verification_date: string;
  
  /** Detailed method for verifying the prediction */
  verification_method: VerificationMethod;
  
  /** The initial status of the prediction (e.g., "Pending", "Verified") */
  initial_status: string;
}

/**
 * APIResponse Interface
 * 
 * The top-level response structure returned by the API endpoints.
 * Contains an array of prediction responses.
 */
export interface APIResponse {
  /** Array of prediction responses */
  results: NovaResponse[];
}