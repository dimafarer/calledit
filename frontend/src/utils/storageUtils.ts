import { APIResponse } from '../types';

/**
 * Storage Utilities
 * 
 * This module provides utility functions for managing prediction data in local storage.
 * It handles saving, retrieving, and clearing prediction data with proper error handling.
 */

/**
 * Constants for storage keys to ensure consistency across the application
 * and make it easier to change keys if needed in the future.
 */
export const STORAGE_KEYS = {
  PREDICTION_DATA: 'calledit_prediction_data',
};

/**
 * Saves prediction data to local storage
 * 
 * This function handles both saving new data and removing existing data:
 * - If data is provided, it will be stringified and stored
 * - If null is provided, any existing data will be removed
 * 
 * @param data The prediction data to save or null to clear
 */
export const savePredictionData = (data: APIResponse | null): void => {
  try {
    if (data) {
      localStorage.setItem(STORAGE_KEYS.PREDICTION_DATA, JSON.stringify(data));
    } else {
      localStorage.removeItem(STORAGE_KEYS.PREDICTION_DATA);
    }
  } catch (error) {
    console.error('Error saving prediction data to local storage:', error);
  }
};

/**
 * Retrieves prediction data from local storage
 * 
 * This function:
 * 1. Attempts to retrieve the stored JSON string
 * 2. Parses it into an APIResponse object
 * 3. Handles any errors that occur during retrieval or parsing
 * 4. Clears invalid data to prevent future errors
 * 
 * @returns The stored prediction data or null if none exists or an error occurs
 */
export const getPredictionData = (): APIResponse | null => {
  try {
    const storedData = localStorage.getItem(STORAGE_KEYS.PREDICTION_DATA);
    if (storedData) {
      return JSON.parse(storedData) as APIResponse;
    }
  } catch (error) {
    console.error('Error retrieving prediction data from local storage:', error);
    // If there's an error parsing the data, clear it to prevent future errors
    clearPredictionData();
  }
  return null;
};

/**
 * Clears prediction data from local storage
 * 
 * This function removes the prediction data item from local storage
 * and handles any errors that might occur during the process.
 */
export const clearPredictionData = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEYS.PREDICTION_DATA);
  } catch (error) {
    console.error('Error clearing prediction data from local storage:', error);
  }
};