import { useState, useEffect } from 'react'
import './App.css'
import { MakePredictions, ListPredictions, LoginButton } from './components'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import StreamingCall from './components/StreamingCall'
import NotificationSettings from './components/NotificationSettings'

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
  currentView: 'make' | 'list' | 'streaming' | 'notifications', 
  navigateTo: (view: 'make' | 'list' | 'streaming' | 'notifications') => void 
}) => {
  const { isAuthenticated } = useAuth();
  
  return (
    <div className="header-controls">
      {isAuthenticated && (
        <>
          <button 
            onClick={() => navigateTo('streaming')}
            className={`navigation-button ${currentView === 'streaming' ? 'active' : ''}`}
            aria-label="Make streaming call"
          >
            ⚡ Streaming Mode
          </button>
          <button 
            onClick={() => navigateTo('list')}
            className={`navigation-button secondary ${currentView === 'list' ? 'active' : ''}`}
            aria-label="View my calls"
          >
            📋 View Calls
          </button>
          <button 
            onClick={() => navigateTo('notifications')}
            className={`navigation-button secondary ${currentView === 'notifications' ? 'active' : ''}`}
            aria-label="Notification settings"
          >
            🎉 Crying
          </button>
          <button 
            onClick={() => navigateTo('make')}
            className={`navigation-button legacy ${currentView === 'make' ? 'active' : ''}`}
            aria-label="Legacy non-streaming mode"
            title="Non-streaming mode (for educational comparison)"
          >
            📜 Legacy Mode
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
  const [currentView, setCurrentView] = useState<'make' | 'list' | 'streaming' | 'notifications'>('make');
  const { isAuthenticated } = useAuth();
  
  // Effect to redirect to make predictions view when user logs out while on list view
  useEffect(() => {
    if (!isAuthenticated && (currentView === 'list' || currentView === 'streaming' || currentView === 'notifications')) {
      setCurrentView('make');
    }
  }, [isAuthenticated, currentView]);

  // Single navigation handler that accepts the view as parameter
  const navigateTo = (view: 'make' | 'list' | 'streaming' | 'notifications') => setCurrentView(view);

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
        <StreamingCall 
          webSocketUrl={import.meta.env.VITE_WEBSOCKET_URL || ''} 
          onNavigateToList={() => navigateTo('list')}
        />
      }
      {currentView === 'list' && 
        <ListPredictions onNavigateToMake={() => navigateTo('make')} />
      }
      {currentView === 'notifications' && 
        <NotificationSettings onClose={() => navigateTo('make')} />
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