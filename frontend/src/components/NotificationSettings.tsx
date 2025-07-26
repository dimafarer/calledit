import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

/**
 * NotificationSettings Component
 * 
 * Allows users to manage their notification preferences for "crying" successful predictions.
 * Currently supports email notifications via SNS, with future social media integration planned.
 */

interface NotificationSettingsProps {
  onClose?: () => void;
}

interface SubscriptionStatus {
  isSubscribed: boolean;
  email?: string;
  subscriptionArn?: string;
}

const NotificationSettings: React.FC<NotificationSettingsProps> = ({ onClose }) => {
  const [email, setEmail] = useState('');
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus>({ isSubscribed: false });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const { isAuthenticated, getToken } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      checkSubscriptionStatus();
    }
  }, [isAuthenticated]);

  const checkSubscriptionStatus = async () => {
    try {
      const token = getToken();
      const apiEndpoint = import.meta.env.VITE_APIGATEWAY + '/notification-status';
      
      const response = await axios.get(apiEndpoint, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });

      setSubscriptionStatus(response.data);
      if (response.data.email) {
        setEmail(response.data.email);
      }
    } catch (error) {
      console.log('Could not check subscription status - endpoint may not exist yet');
      // This is expected until we implement the backend endpoint
    }
  };

  const handleSubscribe = async () => {
    if (!email.trim()) {
      setMessage({ type: 'error', text: 'Please enter a valid email address' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const token = getToken();
      const apiEndpoint = import.meta.env.VITE_APIGATEWAY + '/subscribe-notifications';
      
      const response = await axios.post(apiEndpoint, {
        email: email.trim()
      }, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });

      if (response.data.success) {
        setMessage({ 
          type: 'success', 
          text: 'Subscription request sent! Please check your email and click the confirmation link.' 
        });
        setSubscriptionStatus({ isSubscribed: false, email: email.trim() }); // Pending confirmation
      }
    } catch (error: any) {
      console.error('Subscription error:', error);
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.error || 'Failed to subscribe. Please try again.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUnsubscribe = async () => {
    setIsLoading(true);
    setMessage(null);

    try {
      const token = getToken();
      const apiEndpoint = import.meta.env.VITE_APIGATEWAY + '/unsubscribe-notifications';
      
      await axios.post(apiEndpoint, {}, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });

      setSubscriptionStatus({ isSubscribed: false });
      setMessage({ type: 'success', text: 'Successfully unsubscribed from notifications.' });
    } catch (error: any) {
      console.error('Unsubscribe error:', error);
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.error || 'Failed to unsubscribe. Please try again.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="notification-settings">
        <p>Please log in to manage notification settings.</p>
      </div>
    );
  }

  return (
    <div className="notification-settings">
      <div className="settings-header">
        <h2>🎉 Crying Settings</h2>
        <p>Get notified when your predictions are verified as TRUE!</p>
        {onClose && (
          <button className="close-button" onClick={onClose} aria-label="Close">×</button>
        )}
      </div>

      <div className="settings-content">
        <div className="notification-section">
          <h3>📧 Email Notifications</h3>
          <p>Receive email alerts when your predictions are successfully verified.</p>
          
          {subscriptionStatus.isSubscribed ? (
            <div className="subscription-active">
              <div className="status-indicator success">
                ✅ You're subscribed to email notifications
              </div>
              <p>Email: <strong>{subscriptionStatus.email}</strong></p>
              <button 
                onClick={handleUnsubscribe}
                disabled={isLoading}
                className="unsubscribe-button"
              >
                {isLoading ? 'Unsubscribing...' : 'Unsubscribe'}
              </button>
            </div>
          ) : (
            <div className="subscription-form">
              <div className="status-indicator">
                📭 Not subscribed to email notifications
              </div>
              <div className="email-input-group">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email address"
                  className="email-input"
                  disabled={isLoading}
                />
                <button 
                  onClick={handleSubscribe}
                  disabled={isLoading || !email.trim()}
                  className="subscribe-button"
                >
                  {isLoading ? 'Subscribing...' : 'Subscribe'}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="social-section">
          <h3>🌐 Social Media (Coming Soon)</h3>
          <p>Automatically share your successful predictions on social media.</p>
          
          <div className="social-platforms">
            <div className="platform-item disabled">
              <span className="platform-icon">🐦</span>
              <span className="platform-name">Twitter</span>
              <span className="coming-soon">Coming Soon</span>
            </div>
            <div className="platform-item disabled">
              <span className="platform-icon">💼</span>
              <span className="platform-name">LinkedIn</span>
              <span className="coming-soon">Coming Soon</span>
            </div>
            <div className="platform-item disabled">
              <span className="platform-icon">📘</span>
              <span className="platform-name">Facebook</span>
              <span className="coming-soon">Coming Soon</span>
            </div>
          </div>
        </div>

        {message && (
          <div className={`message ${message.type}`}>
            {message.text}
          </div>
        )}
      </div>

      <style>{`
        .notification-settings {
          max-width: 600px;
          margin: 0 auto;
          padding: 20px;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .settings-header {
          position: relative;
          margin-bottom: 30px;
          text-align: center;
        }
        .settings-header h2 {
          margin: 0 0 10px 0;
          color: #333;
        }
        .settings-header p {
          color: #666;
          margin: 0;
        }
        .close-button {
          position: absolute;
          top: 0;
          right: 0;
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          color: #999;
        }
        .close-button:hover {
          color: #333;
        }
        .notification-section, .social-section {
          margin-bottom: 30px;
          padding: 20px;
          border: 1px solid #e0e0e0;
          border-radius: 6px;
        }
        .notification-section h3, .social-section h3 {
          margin: 0 0 10px 0;
          color: #333;
        }
        .status-indicator {
          padding: 10px;
          border-radius: 4px;
          margin: 15px 0;
          font-weight: 500;
        }
        .status-indicator.success {
          background: #d4edda;
          color: #155724;
          border: 1px solid #c3e6cb;
        }
        .status-indicator:not(.success) {
          background: #f8f9fa;
          color: #6c757d;
          border: 1px solid #dee2e6;
        }
        .email-input-group {
          display: flex;
          gap: 10px;
          margin-top: 15px;
        }
        .email-input {
          flex: 1;
          padding: 10px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
        }
        .subscribe-button, .unsubscribe-button {
          padding: 10px 20px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
        }
        .subscribe-button {
          background: #007bff;
          color: white;
        }
        .subscribe-button:hover:not(:disabled) {
          background: #0056b3;
        }
        .unsubscribe-button {
          background: #dc3545;
          color: white;
          margin-top: 10px;
        }
        .unsubscribe-button:hover:not(:disabled) {
          background: #c82333;
        }
        .subscribe-button:disabled, .unsubscribe-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .social-platforms {
          display: flex;
          flex-direction: column;
          gap: 10px;
          margin-top: 15px;
        }
        .platform-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          opacity: 0.6;
        }
        .platform-item.disabled {
          cursor: not-allowed;
        }
        .platform-icon {
          font-size: 18px;
        }
        .platform-name {
          flex: 1;
          font-weight: 500;
        }
        .coming-soon {
          font-size: 12px;
          color: #6c757d;
          background: #f8f9fa;
          padding: 2px 8px;
          border-radius: 12px;
        }
        .message {
          padding: 12px;
          border-radius: 4px;
          margin-top: 20px;
        }
        .message.success {
          background: #d4edda;
          color: #155724;
          border: 1px solid #c3e6cb;
        }
        .message.error {
          background: #f8d7da;
          color: #721c24;
          border: 1px solid #f5c6cb;
        }
        .message.info {
          background: #cce7ff;
          color: #004085;
          border: 1px solid #b3d7ff;
        }
      `}</style>
    </div>
  );
};

export default NotificationSettings;