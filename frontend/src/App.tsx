import { useState } from 'react'
import './App.css'
import { MakePredictions, ListPredictions, LoginButton } from './components'
import { AuthProvider } from './contexts/AuthContext'

function App() {
  const [currentView, setCurrentView] = useState<'make' | 'list'>('make')

  // Single navigation handler that accepts the view as parameter
  const navigateTo = (view: 'make' | 'list') => setCurrentView(view)

  return (
    <AuthProvider>
      <div className="app-container">
        <h1>Called It!!</h1>
        
        <div className="login-container">
          <LoginButton />
        </div>
        
        {/* Use component mapping for cleaner conditional rendering */}
        {currentView === 'make' ? 
          <MakePredictions onNavigateToList={() => navigateTo('list')} /> : 
          <ListPredictions onNavigateToMake={() => navigateTo('make')} />
        }
      </div>
    </AuthProvider>
  )
}

export default App