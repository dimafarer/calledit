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
      <div className="app-header">
        <h1 className="app-title">Called It!!</h1>
        <div className="header-right">
          <LoginButton />
        </div>
      </div>

      {isAuthenticated && (
        <nav className="nav-bar">
          <button
            onClick={() => setCurrentView('predict')}
            className={`nav-tab ${currentView === 'predict' ? 'active' : ''}`}
          >
            ⚡ Make Prediction
          </button>
          <button
            onClick={() => setCurrentView('list')}
            className={`nav-tab ${currentView === 'list' ? 'active' : ''}`}
          >
            📋 My Predictions
          </button>
          <Link to="/eval" className="nav-tab" style={{ textDecoration: 'none' }}>
            📊 Eval Dashboard
          </Link>
        </nav>
      )}

      {!isAuthenticated && (
        <nav className="nav-bar">
          <Link to="/eval" className="nav-tab" style={{ textDecoration: 'none' }}>
            📊 Eval Dashboard
          </Link>
        </nav>
      )}

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
