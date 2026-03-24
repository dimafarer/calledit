import { useAuth } from '../contexts/AuthContext';

const LoginButton = () => {
  const { isAuthenticated, login, logout } = useAuth();

  return (
    <button
      onClick={isAuthenticated ? logout : login}
      className="navigation-button secondary"
      aria-label={isAuthenticated ? 'Log out' : 'Log in'}
    >
      {isAuthenticated ? '🚪 Logout' : '🔑 Login'}
    </button>
  );
};

export default LoginButton;
