// LoginButton.tsx - update to match new AuthContext
import React from 'react';
import { useAuth } from '../contexts/AuthContext';

interface LoginButtonProps {
  // We can add props later if needed
}

const LoginButton: React.FC<LoginButtonProps> = () => {
  const { isAuthenticated, login, logout } = useAuth();

  const handleLoginToggle = () => {
    if (isAuthenticated) {
      logout();
    } else {
      login();
    }
  };

  return (
    <div className="login-button-container">
      <button 
        onClick={handleLoginToggle}
        className="send-button"
        aria-label={isAuthenticated ? "Logout" : "Login"}
      >
        {isAuthenticated ? 'Logout' : 'Login'}
      </button>
    </div>
  );
};

export default LoginButton;
