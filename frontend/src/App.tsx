import { useState, useEffect } from 'react'
import './App.css'
import { MakePredictions, ListPredictions, LoginButton } from './components'
import { AuthProvider, useAuth } from './contexts/AuthContext'

// Navigation buttons component
const NavigationControls = ({ 
  currentView, 
  navigateTo 
}: { 
  currentView: 'make' | 'list', 
  navigateTo: (view: 'make' | 'list') => void 
}) => {
  const { isAuthenticated } = useAuth();
  
  return (
    <div className="header-controls">
      {isAuthenticated && (
        <button 
          onClick={() => navigateTo(currentView === 'make' ? 'list' : 'make')}
          className="navigation-button"
          aria-label={currentView === 'make' ? "View my predictions" : "Make new prediction"}
        >
          {currentView === 'make' ? 'View My Predictions' : 'Make New Prediction'}
        </button>
      )}
      <LoginButton />
    </div>
  );
};

function AppContent() {
  const [currentView, setCurrentView] = useState<'make' | 'list'>('make');
  const { isAuthenticated } = useAuth();
  
  // Effect to redirect to make predictions view when user logs out while on list view
  useEffect(() => {
    if (!isAuthenticated && currentView === 'list') {
      setCurrentView('make');
    }
  }, [isAuthenticated, currentView]);

  // Single navigation handler that accepts the view as parameter
  const navigateTo = (view: 'make' | 'list') => setCurrentView(view);

  return (
    <div className="app-container">
      <h1>Called It!!</h1>
      
      <div className="login-container">
        <NavigationControls currentView={currentView} navigateTo={navigateTo} />
      </div>
      
      {/* Use component mapping for cleaner conditional rendering */}
      {currentView === 'make' ? 
        <MakePredictions onNavigateToList={() => navigateTo('list')} /> : 
        <ListPredictions onNavigateToMake={() => navigateTo('make')} />
      }
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App