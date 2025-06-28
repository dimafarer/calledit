import React, { useState, useEffect, useRef } from 'react';
import { PredictionService } from '../services/predictionService';
import LogCallButton from './LogCallButton';
import { APIResponse } from '../types';

interface StreamingPredictionProps {
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

const StreamingPrediction: React.FC<StreamingPredictionProps> = ({ webSocketUrl, onNavigateToList }) => {
  const [prompt, setPrompt] = useState('');
  const [streamingText, setStreamingText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [prediction, setPrediction] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<APIResponse | null>(null);
  const predictionServiceRef = useRef<PredictionService | null>(null);

  useEffect(() => {
    // Initialize the prediction service
    predictionServiceRef.current = new PredictionService(webSocketUrl);

    // Clean up on unmount
    return () => {
      if (predictionServiceRef.current) {
        predictionServiceRef.current.cleanup();
      }
    };
  }, [webSocketUrl]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!prompt.trim() || !predictionServiceRef.current) {
      return;
    }

    setIsLoading(true);
    handleNewCall();

    try {
      await predictionServiceRef.current.makePredictionWithStreaming(
        prompt,
        // Text chunk handler
        (text) => {
          setStreamingText((prev) => prev + text);
        },
        // Tool use handler
        (toolName) => {
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
            setPrediction(parsedResponse);
            
            // Format response for LogCallButton compatibility
            const apiResponse: APIResponse = {
              results: [parsedResponse]
            };
            setResponse(apiResponse);
            setIsLoading(false);
          } catch (parseError) {
            console.error('Error parsing final response:', parseError);
            setPrediction({ raw: finalResponse });
            setIsLoading(false);
          }
        },
        // Error handler
        (errorMessage) => {
          setError(errorMessage);
          setIsLoading(false);
        }
      );
    } catch (err) {
      setError((err as Error).message);
      setIsLoading(false);
    }
  };

  // Clear call data when starting new call
  const handleNewCall = () => {
    setPrediction(null);
    setResponse(null);
    setStreamingText('');
    setError(null);
  };

  return (
    <div className="streaming-prediction" style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
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
      
      {streamingText && (
        <div style={{ marginBottom: '20px' }}>
          <h3>Processing your call...</h3>
          <div style={{ 
            backgroundColor: '#f8f9fa', 
            padding: '15px', 
            borderRadius: '4px',
            border: '1px solid #dee2e6',
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace',
            fontSize: '14px',
            maxHeight: '300px',
            overflowY: 'auto'
          }}>
            {streamingText}
          </div>
        </div>
      )}
      
      {prediction && (
        <div style={{ marginTop: '20px' }}>
          <h3>Call Details</h3>
          
          {/* User-friendly display */}
          <div style={{ 
            backgroundColor: '#f8f9fa', 
            padding: '20px', 
            borderRadius: '8px',
            border: '1px solid #dee2e6',
            marginBottom: '15px'
          }}>
            <div style={{ marginBottom: '15px' }}>
              <strong>Prediction:</strong> {prediction.prediction_statement}
            </div>
            
            <div style={{ marginBottom: '15px' }}>
              <strong>Verification Date:</strong> {new Date(prediction.verification_date).toLocaleString()}
            </div>
            
            <div style={{ marginBottom: '15px' }}>
              <strong>Verifiability:</strong> {getVerifiabilityDisplay(prediction.verifiable_category)}
            </div>
            
            {prediction.category_reasoning && (
              <div style={{ marginBottom: '15px' }}>
                <strong>Category Reasoning:</strong> 
                <div style={{ 
                  fontStyle: 'italic', 
                  color: '#6c757d',
                  marginTop: '5px',
                  paddingLeft: '10px',
                  borderLeft: '3px solid #dee2e6'
                }}>
                  {prediction.category_reasoning}
                </div>
              </div>
            )}
            
            <div>
              <strong>Status:</strong> 
              <span style={{ 
                color: '#856404',
                backgroundColor: '#fff3cd',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                marginLeft: '8px'
              }}>
                {prediction.initial_status.toUpperCase()}
              </span>
            </div>
          </div>
          
          {/* Raw JSON (collapsible) */}
          <details style={{ marginBottom: '15px' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 'bold', marginBottom: '10px' }}>
              View Raw JSON
            </summary>
            <div style={{ 
              backgroundColor: '#d4edda', 
              padding: '15px', 
              borderRadius: '4px',
              border: '1px solid #c3e6cb'
            }}>
              <pre style={{ 
                whiteSpace: 'pre-wrap', 
                fontSize: '14px',
                margin: 0
              }}>
                {JSON.stringify(prediction, null, 2)}
              </pre>
            </div>
          </details>
          
          <div>
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

export default StreamingPrediction;