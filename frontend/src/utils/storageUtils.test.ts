import { describe, it, expect, beforeEach, vi } from 'vitest';
import { savePredictionData, getPredictionData, clearPredictionData, STORAGE_KEYS } from './storageUtils';
import { APIResponse } from '../types';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

// Replace the global localStorage with our mock
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('Storage Utils', () => {
  // Sample prediction data for testing
  const samplePredictionData: APIResponse = {
    results: [
      {
        prediction_statement: 'Test prediction',
        verification_date: '2023-12-31',
        verification_method: {
          source: ['Test source'],
          criteria: ['Test criteria'],
          steps: ['Test step']
        },
        initial_status: 'pending'
      }
    ]
  };

  beforeEach(() => {
    // Clear all mocks and localStorage before each test
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  describe('savePredictionData', () => {
    it('should save prediction data to localStorage', () => {
      savePredictionData(samplePredictionData);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        STORAGE_KEYS.PREDICTION_DATA,
        JSON.stringify(samplePredictionData)
      );
    });

    it('should remove prediction data from localStorage when null is passed', () => {
      savePredictionData(null);
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(
        STORAGE_KEYS.PREDICTION_DATA
      );
    });

    it('should handle errors gracefully', () => {
      // Mock setItem to throw an error
      localStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('Test error');
      });
      
      // This should not throw an error
      expect(() => savePredictionData(samplePredictionData)).not.toThrow();
    });
  });

  describe('getPredictionData', () => {
    it('should retrieve prediction data from localStorage', () => {
      // Setup: Save data to localStorage
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(samplePredictionData));
      
      const result = getPredictionData();
      
      expect(localStorageMock.getItem).toHaveBeenCalledWith(
        STORAGE_KEYS.PREDICTION_DATA
      );
      expect(result).toEqual(samplePredictionData);
    });

    it('should return null if no data exists', () => {
      // Setup: No data in localStorage
      localStorageMock.getItem.mockReturnValueOnce(null);
      
      const result = getPredictionData();
      
      expect(result).toBeNull();
    });

    it('should handle invalid JSON and clear storage', () => {
      // Setup: Invalid JSON in localStorage
      localStorageMock.getItem.mockReturnValueOnce('invalid json');
      
      const result = getPredictionData();
      
      expect(result).toBeNull();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(
        STORAGE_KEYS.PREDICTION_DATA
      );
    });
  });

  describe('clearPredictionData', () => {
    it('should remove prediction data from localStorage', () => {
      clearPredictionData();
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(
        STORAGE_KEYS.PREDICTION_DATA
      );
    });

    it('should handle errors gracefully', () => {
      // Mock removeItem to throw an error
      localStorageMock.removeItem.mockImplementationOnce(() => {
        throw new Error('Test error');
      });
      
      // This should not throw an error
      expect(() => clearPredictionData()).not.toThrow();
    });
  });
});