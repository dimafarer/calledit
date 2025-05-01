// Import necessary dependencies from React and other libraries
import { useState } from 'react' // useState hook for managing component state
import './App.css' // Component styles
// Import components
import { 
  MakePredictions,
  ListPredictions,
  LoginButton
} from './components'
// Import auth provider
import { AuthProvider } from './contexts/AuthContext'

// Main App Component
function App() {
  // State to manage which component to display
  const [currentView, setCurrentView] = useState<'make' | 'list'>('make');

  // Navigation handlers
  const handleNavigateToList = () => {
    setCurrentView('list');
  };

  const handleNavigateToMake = () => {
    setCurrentView('make');
  };

  // Component's main render method
  return (
    <AuthProvider>
      <div className="app-container">
        <h1>Call It!!</h1>
        
        {/* Login button always visible at the top */}
        <div className="login-container">
          <LoginButton />
        </div>
        
        {/* Conditional rendering based on current view */}
        {currentView === 'make' ? (
          <MakePredictions onNavigateToList={handleNavigateToList} />
        ) : (
          <ListPredictions onNavigateToMake={handleNavigateToMake} />
        )}
      </div>
    </AuthProvider>
  )
}

export default App







