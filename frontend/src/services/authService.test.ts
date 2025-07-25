import {
  storeTokens,
  clearTokens,
  getAccessToken,
  getIdToken,
  isAuthenticated,
  getUser,
  AuthResponse,
} from './authService';

// Comment out the Auth import since it's causing issues
// import { Auth } from 'aws-amplify';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('authService', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('storeTokens', () => {
    it('should store tokens in localStorage', () => {
      const mockTokens: AuthResponse = {
        accessToken: 'test-access-token',
        idToken: 'test-id-token',
        refreshToken: 'test-refresh-token',
        expiresIn: 3600,
      };

      storeTokens(mockTokens);

      expect(localStorage.getItem('cognito_token')).toBe('test-access-token');
      expect(localStorage.getItem('cognito_id_token')).toBe('test-id-token');
      expect(localStorage.getItem('cognito_refresh_token')).toBe('test-refresh-token');
      expect(localStorage.getItem('token_expires_at')).toBeDefined();
    });
  });

  describe('clearTokens', () => {
    it('should remove tokens from localStorage', () => {
      // Set up tokens first
      localStorage.setItem('cognito_token', 'test-access-token');
      localStorage.setItem('cognito_id_token', 'test-id-token');
      localStorage.setItem('cognito_refresh_token', 'test-refresh-token');
      localStorage.setItem('token_expires_at', '123456789');

      clearTokens();

      expect(localStorage.getItem('cognito_token')).toBeNull();
      expect(localStorage.getItem('cognito_id_token')).toBeNull();
      expect(localStorage.getItem('cognito_refresh_token')).toBeNull();
      expect(localStorage.getItem('token_expires_at')).toBeNull();
    });
  });

  describe('getAccessToken', () => {
    it('should return the access token from localStorage', async () => {
      localStorage.setItem('cognito_token', 'test-access-token');

      const token = await getAccessToken();

      expect(token).toBe('test-access-token');
    });

    it('should return null if no token exists', async () => {
      const token = await getAccessToken();

      expect(token).toBeNull();
    });
  });

  describe('getIdToken', () => {
    it('should return the ID token from localStorage', async () => {
      localStorage.setItem('cognito_id_token', 'test-id-token');

      const token = await getIdToken();

      expect(token).toBe('test-id-token');
    });

    it('should return null if no token exists', async () => {
      const token = await getIdToken();

      expect(token).toBeNull();
    });
  });

  describe('isAuthenticated', () => {
    it('should return true if token exists and is not expired', async () => {
      localStorage.setItem('cognito_token', 'test-access-token');
      localStorage.setItem('token_expires_at', (Date.now() + 3600000).toString()); // 1 hour in the future

      const authenticated = await isAuthenticated();

      expect(authenticated).toBe(true);
    });

    it('should return false if token is expired', async () => {
      localStorage.setItem('cognito_token', 'test-access-token');
      localStorage.setItem('token_expires_at', (Date.now() - 3600000).toString()); // 1 hour in the past

      const authenticated = await isAuthenticated();

      expect(authenticated).toBe(false);
    });

    it('should return false if no token exists', async () => {
      const authenticated = await isAuthenticated();

      expect(authenticated).toBe(false);
    });
  });

  describe('getUser', () => {
    it('should return null if no ID token exists', async () => {
      const user = await getUser();

      expect(user).toBeNull();
    });

    it('should decode and return user info from ID token', async () => {
      // This is a sample JWT token with payload { "email": "test@example.com" }
      const sampleToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20ifQ.8x5VjWiSaIx0u0JtPA1O0_JLGIM976H_MX86mpnSo5A';
      localStorage.setItem('cognito_id_token', sampleToken);

      // Mock the atob function
      global.atob = vi.fn().mockImplementation((str) => {
        return Buffer.from(str, 'base64').toString('binary');
      });

      const user = await getUser();

      expect(user).toEqual({ email: 'test@example.com' });
    });
  });
});

