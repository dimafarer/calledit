import { useAuth } from '../contexts/AuthContext';

/**
 * LoginButton Component
 * 
 * This component provides the user interface for authentication actions.
 * It toggles between showing a "Login" or "Logout" button based on the 
 * current authentication state.
 * 
 * The component uses the AuthContext to:
 * 1. Determine the current authentication state
 * 2. Access the login and logout functions
 * 
 * When clicked, it either initiates the login flow (redirecting to Cognito)
 * or performs a logout action (clearing tokens and updating state).
 */

// Keep the interface for future extensibility
interface LoginButtonProps {
  // We can add props later if needed
}

const LoginButton: React.FC<LoginButtonProps> = () => {
  const { isAuthenticated, login, logout } = useAuth();
  
  return (
    <div className="login-button-container">
      <button 
        onClick={isAuthenticated ? logout : login}
        className="send-button"
        aria-label={isAuthenticated ? "Logout" : "Login"}
      >
        {isAuthenticated ? 'Logout' : 'Login'}
      </button>
    </div>
  );
};

export default LoginButton;