import React, { useState, useEffect, useRef } from 'react';
import { CallService } from '../services/callService';
import LogCallButton from './LogCallButton';
import AnimatedText from './AnimatedText';
import { APIResponse } from '../types';

interface StreamingCallProps {
  webSocketUrl: string;
  onNavigateToList?: () => void;
}

// Helper function to display verifiability categories with icons and colors
const getVerifiabilityDisplay = (category: string) => {
  const categoryMap: Record<string, { icon: string; label: string; color: string; bgColor: string }> = {
    'agent_verifiable': {
      icon: '🧠',
      label: 'Agent Verifiable',
      color: '#155724',
      bgColor: '#d4edda'
    },
    'current_tool_verifiable': {
      icon: '⏰',
      label: 'Time-Tool Verifiable',
      color: '#004085',
      bgColor: '#cce7ff'
    },
    'strands_tool_verifiable': {
      icon: '🔧',
      label: 'Strands-Tool Verifiable',
      color: '#721c24',
      bgColor: '#f8d7da'
    },
    'api_tool_verifiable': {
      icon: '🌐',
      label: 'API Verifiable',
      color: '#856404',
      bgColor: '#fff3cd'
    },
    'human_verifiable_only': {
      icon: '👤',
      label: 'Human Verifiable Only',
      color: '#6f42c1',
      bgColor: '#e2d9f3'
    }
  };
  
  const config = categoryMap[category] || categoryMap['human_verifiable_only'];
  
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '4px 12px',
      borderRadius: '16px',
      fontSize: '14px',
      fontWeight: '500',
      color: config.color,
      backgroundColor: config.bgColor,
      border: `1px solid ${config.color}20`
    }}>
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
};

const StreamingCall: React.FC<StreamingCallProps> = ({ webSocketUrl, onNavigateToList }) => {
  const [prompt, setPrompt] = useState('');
  const [streamingText, setStreamingText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [call, setCall] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<APIResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  const callServiceRef = useRef<CallService | null>(null);

  useEffect(() => {
    // Initialize the call service
    callServiceRef.current = new CallService(webSocketUrl);

    // Clean up on unmount
    return () => {
      if (callServiceRef.current) {
        callServiceRef.current.cleanup();
      }
    };
  }, [webSocketUrl]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!prompt.trim() || !callServiceRef.current) {
      return;
    }

    setIsLoading(true);
    setIsProcessing(true);
    handleNewCall();

    try {
      await callServiceRef.current.makeCallWithStreaming(
        prompt,
        // Text chunk handler
        (text) => {
          setStreamingText((prev) => prev + text);
        },
        // Tool use handler
        (toolName) => {
          setCurrentTool(toolName);
          setStreamingText((prev) => 
            prev + `\n[Using tool: ${toolName}]\n`
          );
        },
        // Complete handler
        (finalResponse) => {
          try {
            const parsedResponse = typeof finalResponse === 'string' 
              ? JSON.parse(finalResponse) 
              : finalResponse;
            setCall(parsedResponse);
            
            // Format response for LogCallButton compatibility
            const apiResponse: APIResponse = {
              results: [parsedResponse]
            };
            setResponse(apiResponse);
            setIsLoading(false);
            setIsProcessing(false);
            setCurrentTool(null);
          } catch (parseError) {
            console.error('Error parsing final response:', parseError);
            setCall({ raw: finalResponse });
            setIsLoading(false);
            setIsProcessing(false);
            setCurrentTool(null);
          }
        },
        // Error handler
        (errorMessage) => {
          setError(errorMessage);
          setIsLoading(false);
          setIsProcessing(false);
          setCurrentTool(null);
        }
      );
    } catch (err) {
      setError((err as Error).message);
      setIsLoading(false);
      setIsProcessing(false);
      setCurrentTool(null);
    }
  };

  // Clear call data when starting new call
  const handleNewCall = () => {
    setCall(null);
    setResponse(null);
    setStreamingText('');
    setError(null);
    setIsProcessing(false);
    setCurrentTool(null);
  };

  return (
    <div className="streaming-call" style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h2>Make a Call (Streaming)</h2>
      
      <form onSubmit={handleSubmit} style={{ marginBottom: '20px' }}>
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="call-input" style={{ display: 'block', marginBottom: '5px' }}>
            Your Call:
          </label>
          <textarea
            id="call-input"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter your call..."
            rows={4}
            disabled={isLoading}
            style={{ 
              width: '100%', 
              padding: '10px', 
              border: '1px solid #ccc', 
              borderRadius: '4px',
              fontSize: '14px'
            }}
          />
        </div>
        
        <button 
          type="submit" 
          disabled={isLoading || !prompt.trim()} 
          style={{
            padding: '10px 20px',
            backgroundColor: isLoading ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer'
          }}
        >
          {isLoading ? 'Processing...' : 'Make Call'}
        </button>
      </form>
      
      {error && (
        <div style={{ 
          backgroundColor: '#f8d7da', 
          color: '#721c24', 
          padding: '10px', 
          borderRadius: '4px',
          marginBottom: '20px'
        }}>
          <p>Error: {error}</p>
        </div>
      )}
      
      {(streamingText || isProcessing) && (
        <div className="streaming-response">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, color: '#667eea' }}>🧠 AI Reasoning Process</h3>
            {isProcessing && (
              <div className="processing-indicator">
                <span>Processing</span>
                <div className="processing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
          </div>
          
          {currentTool && (
            <div style={{
              background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)',
              border: '1px solid rgba(102, 126, 234, 0.2)',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <span style={{ fontSize: '1.2rem' }}>🔧</span>
              <span style={{ color: '#667eea', fontWeight: '500' }}>Using tool: {currentTool}</span>
            </div>
          )}
          
          {streamingText && (
            <div style={{ 
              padding: '16px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.8)',
              border: '1px solid rgba(102, 126, 234, 0.1)',
              minHeight: '100px'
            }}>
              <AnimatedText 
                text={streamingText}
                className="streaming-text"
              />
            </div>
          )}
        </div>
      )}
      
      {call && (
        <div style={{ marginTop: '20px' }}>
          <h3>Call Details</h3>
          <div className="structured-response">
            <div className="response-field">
              <h3>Call Statement:</h3>
              <p>{call.prediction_statement}</p>
            </div>
            <div className="response-field">
              <h3>Call Date:</h3>
              <p>{call.prediction_date ? new Date(call.prediction_date).toLocaleString() : (call.local_prediction_date || 'Not available')}</p>
            </div>
            <div className="response-field">
              <h3>Verification Date:</h3>
              <p>{call.verification_date ? new Date(call.verification_date).toLocaleString() : 'Not available'}</p>
            </div>
            {call.verifiable_category && (
              <div className="response-field">
                <h3>Verifiability:</h3>
                <p>{getVerifiabilityDisplay(call.verifiable_category)}</p>
                {call.category_reasoning && (
                  <div style={{ 
                    fontStyle: 'italic', 
                    color: '#6c757d',
                    marginTop: '8px',
                    paddingLeft: '12px',
                    borderLeft: '3px solid #dee2e6',
                    fontSize: '14px'
                  }}>
                    {call.category_reasoning}
                  </div>
                )}
              </div>
            )}
            <div className="response-field">
              <h3>Verification Method:</h3>
              {call.verification_method && (
                <div className="verification-method">
                  <div className="method-section">
                    <h3>Sources:</h3>
                    <ul>
                      {call.verification_method.source?.map((item: string, index: number) => (
                        <li key={`source-${index}`}>{item}</li>
                      )) || <li>No sources available</li>}
                    </ul>
                  </div>
                  <div className="method-section">
                    <h3>Criteria:</h3>
                    <ul>
                      {call.verification_method.criteria?.map((item: string, index: number) => (
                        <li key={`criteria-${index}`}>{item}</li>
                      )) || <li>No criteria available</li>}
                    </ul>
                  </div>
                  <div className="method-section">
                    <h3>Steps:</h3>
                    <ul>
                      {call.verification_method.steps?.map((item: string, index: number) => (
                        <li key={`step-${index}`}>{item}</li>
                      )) || <li>No steps available</li>}
                    </ul>
                  </div>
                </div>
              )}
            </div>
            <div className="response-field">
              <h3>Initial Status:</h3>
              <p>{call.initial_status}</p>
            </div>
          </div>
          <div style={{ marginTop: '10px' }}>
            <LogCallButton
              response={response}
              isLoading={isLoading}
              isVisible={true}
              setIsLoading={setIsLoading}
              setError={setError}
              setResponse={setResponse}
              setPrompt={setPrompt}
              onSuccessfulLog={onNavigateToList}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default StreamingCall;