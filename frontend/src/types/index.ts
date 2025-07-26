/**
 * Type Definitions for the Called It Application
 * 
 * This file contains TypeScript interfaces that define the shape of data
 * used throughout the application, particularly for API responses.
 */

/**
 * VerificationMethod Interface
 * 
 * Defines the structure for verification methods associated with calls.
 * Each method includes sources to check, criteria for verification, and steps to follow.
 */
export interface VerificationMethod {
  /** Array of sources that can be used to verify the call */
  source: string[];
  
  /** Array of criteria that determine if the call is verified */
  criteria: string[];
  
  /** Array of steps to follow when verifying the call */
  steps: string[];
}

/**
 * CallResponse Interface
 * 
 * Represents a single call with its associated verification details.
 * This is the core data structure for individual calls in the application.
 */
export interface CallResponse {
  /** The main call statement text */
  prediction_statement: string;
  
  /** The date when the call was made (in UTC) */
  prediction_date?: string;
  
  /** Legacy field for backward compatibility */
  creation_date?: string;
  
  /** The date when the call should be verified (in UTC) */
  verification_date: string;
  
  /** The timezone of the dates (default: UTC) */
  timezone?: string;
  
  /** The verifiability category of the call */
  verifiable_category?: string;
  
  /** Reasoning for the verifiability category selection */
  category_reasoning?: string;
  
  /** Detailed method for verifying the call */
  verification_method: VerificationMethod;
  
  /** The initial status of the call (e.g., "Pending", "Verified") */
  initial_status: string;
  
  /** The actual verification status from the verification system */
  verification_status?: string;
  
  /** Confidence score of the verification (0.0 to 1.0) */
  verification_confidence?: number;
  
  /** AI reasoning for the verification result */
  verification_reasoning?: string;
}

/**
 * APIResponse Interface
 * 
 * The top-level response structure returned by the API endpoints.
 * Contains an array of call responses.
 */
export interface APIResponse {
  /** Array of call responses */
  results: CallResponse[];
}

// Legacy alias for backward compatibility
export type NovaResponse = CallResponse;