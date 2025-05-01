import { APIResponse } from '../types';

// Constants for storage keys
export const STORAGE_KEYS = {
  PREDICTION_DATA: 'calledit_prediction_data',
};

/**
 * Saves prediction data to local storage
 * @param data The prediction data to save
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
 * @returns The stored prediction data or null if none exists
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
 */
export const clearPredictionData = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEYS.PREDICTION_DATA);
  } catch (error) {
    console.error('Error clearing prediction data from local storage:', error);
  }
};