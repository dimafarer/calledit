import { useAuth } from '../contexts/AuthContext';

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