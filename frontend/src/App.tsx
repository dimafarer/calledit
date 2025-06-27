import { useState, useEffect } from 'react'
import './App.css'
import { MakePredictions, ListPredictions, LoginButton } from './components'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import StreamingPrediction from './components/StreamingPrediction'

/**
 * NavigationControls Component
 * 
 * This component renders the navigation buttons in the header of the application.
 * It displays a toggle button to switch between making predictions and viewing predictions,
 * but only when the user is authenticated. It also always displays the login/logout button.
 * 
 * @param currentView - The current active view ('make' or 'list')
 * @param navigateTo - Function to change the current view
 */
const NavigationControls = ({ 
  currentView, 
  navigateTo 
}: { 
  currentView: 'make' | 'list' | 'streaming', 
  navigateTo: (view: 'make' | 'list' | 'streaming') => void 
}) => {
  const { isAuthenticated } = useAuth();
  
  return (
    <div className="header-controls">
      {isAuthenticated && (
        <>
          <button 
            onClick={() => navigateTo('make')}
            className={`navigation-button ${currentView === 'make' ? 'active' : ''}`}
            aria-label="Make new call"
          >
            Make Call
          </button>
          <button 
            onClick={() => navigateTo('streaming')}
            className={`navigation-button ${currentView === 'streaming' ? 'active' : ''}`}
            aria-label="Make streaming call"
          >
            Streaming Call
          </button>
          <button 
            onClick={() => navigateTo('list')}
            className={`navigation-button ${currentView === 'list' ? 'active' : ''}`}
            aria-label="View my calls"
          >
            View Calls
          </button>
        </>
      )}
      <LoginButton />
    </div>
  );
};

/**
 * AppContent Component
 * 
 * This is the main content container for the application that handles:
 * 1. View state management between making and listing predictions
 * 2. Automatic redirection to the make predictions view when a user logs out
 * 3. Rendering the appropriate view based on the current state
 * 
 * The component uses the AuthContext to determine if a user is authenticated
 * and conditionally renders different views based on authentication status.
 */
function AppContent() {
  const [currentView, setCurrentView] = useState<'make' | 'list' | 'streaming'>('make');
  const { isAuthenticated } = useAuth();
  
  // Effect to redirect to make predictions view when user logs out while on list view
  useEffect(() => {
    if (!isAuthenticated && (currentView === 'list' || currentView === 'streaming')) {
      setCurrentView('make');
    }
  }, [isAuthenticated, currentView]);

  // Single navigation handler that accepts the view as parameter
  const navigateTo = (view: 'make' | 'list' | 'streaming') => setCurrentView(view);

  return (
    <div className="app-container">
      <h1>Called It!!</h1>
      
      <div className="login-container">
        <NavigationControls currentView={currentView} navigateTo={navigateTo} />
      </div>
      
      {/* Use component mapping for cleaner conditional rendering */}
      {currentView === 'make' && 
        <MakePredictions onNavigateToList={() => navigateTo('list')} />
      }
      {currentView === 'streaming' && 
        <StreamingPrediction 
          webSocketUrl={import.meta.env.VITE_WEBSOCKET_URL || ''} 
          onNavigateToList={() => navigateTo('list')}
        />
      }
      {currentView === 'list' && 
        <ListPredictions onNavigateToMake={() => navigateTo('make')} />
      }
    </div>
  );
}

/**
 * App Component
 * 
 * The root component of the application that wraps the main content
 * with the AuthProvider to make authentication context available
 * throughout the component tree.
 * 
 * @returns The wrapped application with authentication context
 */
function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App