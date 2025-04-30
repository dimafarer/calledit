import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { configureAmplify } from './config/amplifyConfig'
import { handleAuthRedirect } from './services/authService'

// Configure AWS Amplify
configureAmplify();

// Handle authentication redirect if there's a code in the URL
handleAuthRedirect();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

