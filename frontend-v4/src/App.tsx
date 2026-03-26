import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import './App.css'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import LoginButton from './components/LoginButton'
import PredictionInput from './components/PredictionInput'
import ListPredictions from './components/ListPredictions'
import EvalDashboard from './pages/EvalDashboard'

function AppContent() {
  const [currentView, setCurrentView] = useState<'predict' | 'list'>('predict');
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (!isAuthenticated && currentView === 'list') setCurrentView('predict');
  }, [isAuthenticated, currentView]);

  return (
    <div className="app-container">
      <h1>Called It!!</h1>
      <div className="login-container">
        <div className="header-controls">
          {isAuthenticated && (
            <>
              <button
                onClick={() => setCurrentView('predict')}
                className={`navigation-button ${currentView === 'predict' ? 'active' : ''}`}
              >
                ⚡ Make Prediction
              </button>
              <button
                onClick={() => setCurrentView('list')}
                className={`navigation-button secondary ${currentView === 'list' ? 'active' : ''}`}
              >
                📋 My Predictions
              </button>
            </>
          )}
          <Link to="/eval" className="navigation-button secondary" style={{ textDecoration: 'none' }}>
            📊 Eval Dashboard
          </Link>
          <LoginButton />
        </div>
      </div>

      {isAuthenticated ? (
        currentView === 'predict' ? <PredictionInput /> : <ListPredictions />
      ) : (
        <div className="no-predictions"><p>Log in to make predictions.</p></div>
      )}
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<AppContent />} />
          <Route path="/eval" element={<EvalDashboard />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App
