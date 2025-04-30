import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useApi } from '../utils/api';

export function TestAuth() {
  const { isAuthenticated, login, logout } = useAuth();
  const { callApi } = useApi();
  const [apiResponse, setApiResponse] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleTestApi = async () => {
    try {
      setError('');
      const response = await callApi('/hello');
      setApiResponse(JSON.stringify(response, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    }
  };

  return (
    <div>
      <h2>Authentication Test</h2>
      <div>
        Status: {isAuthenticated ? 'Authenticated' : 'Not Authenticated'}
      </div>
      <div>
        {!isAuthenticated ? (
          <button onClick={login}>Login</button>
        ) : (
          <>
            <button onClick={logout}>Logout</button>
            <button onClick={handleTestApi}>Test API Call</button>
          </>
        )}
      </div>
      {error && (
        <div style={{ color: 'red', marginTop: '1rem' }}>
          Error: {error}
        </div>
      )}
      {apiResponse && (
        <pre style={{ marginTop: '1rem' }}>
          {apiResponse}
        </pre>
      )}
    </div>
  );
}
