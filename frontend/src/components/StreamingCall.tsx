import React, { useState, useRef } from 'react';
import LogCallButton from './LogCallButton';
import AnimatedText from './AnimatedText';
import ReviewableSection from './ReviewableSection';
import ImprovementModal from './ImprovementModal';
import { APIResponse } from '../types';
import { useReviewState } from '../hooks/useReviewState';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { useWebSocketConnection } from '../hooks/useWebSocketConnection';
import { useImprovementHistory } from '../hooks/useImprovementHistory';

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
  const callRef = useRef<any>(null);

  const [response, setResponse] = useState<APIResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  // Use custom hooks for state management
  const { reviewState, updateReviewSections, startImprovement, setImprovementInProgress, clearReviewState, cancelImprovement, setReviewStatus } = useReviewState();
  const { error: errorState, hasError, setWebSocketError, setImprovementError, clearError } = useErrorHandler();
  // Use WebSocket connection hook
  const { callService, handleConnectionError, reconnectCount } = useWebSocketConnection({ url: webSocketUrl });
  
  // Use improvement history hook
  const { history, addHistoryEntry, updateHistoryEntry, clearHistory } = useImprovementHistory();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!prompt.trim() || !callService) {
      setWebSocketError('WebSocket connection not available');
      return;
    }

    setIsLoading(true);
    setIsProcessing(true);
    handleNewCall();

    try {
      await callService.makeCallWithStreaming(
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
          console.log('Complete handler called with:', finalResponse);
          try {
            const parsedResponse = typeof finalResponse === 'string' 
              ? JSON.parse(finalResponse) 
              : finalResponse;
            console.log('Parsed response:', parsedResponse);
            setCall(parsedResponse);
            callRef.current = parsedResponse;
            
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
          setWebSocketError(errorMessage);
          handleConnectionError(errorMessage);
          setIsLoading(false);
          setIsProcessing(false);
          setCurrentTool(null);
        },
        // Review status handler
        (status) => {
          setReviewStatus(status);
        },
        // Review complete handler
        (reviewData) => {
          console.log('Raw review data:', reviewData);
          const sections = reviewData.reviewable_sections || [];
          updateReviewSections(sections);
          setImprovementInProgress(false);
        },
        // Improved response handler
        (improvedData) => {
          console.log('Received improved response:', improvedData);
          console.log('Current call state:', call);
          console.log('Condition check:', {
            hasImprovedData: !!improvedData,
            hasSection: !!improvedData?.section,
            hasImprovedValue: !!improvedData?.improved_value,
            hasCall: !!call
          });
          
          if (improvedData && improvedData.section && improvedData.improved_value && callRef.current) {
            // Update specific section in existing call data
            const updatedCall = { ...callRef.current };
            console.log('Updating call with improved data:', improvedData.section, improvedData.improved_value);
            
            if (improvedData.section === 'verification_method') {
              updatedCall.verification_method = {
                source: [improvedData.improved_value],
                criteria: callRef.current.verification_method?.criteria || ['Updated verification criteria'],
                steps: callRef.current.verification_method?.steps || ['Updated verification steps']
              };
            } else if (improvedData.section === 'prediction_statement') {
              updatedCall.prediction_statement = improvedData.improved_value;
            } else if (improvedData.section === 'verifiable_category') {
              updatedCall.verifiable_category = improvedData.improved_value;
            } else {
              updatedCall[improvedData.section] = improvedData.improved_value;
            }
            
            console.log('Setting updated call:', updatedCall);
            setCall(updatedCall);
            callRef.current = updatedCall;
            
            // Update improvement history
            if (history.length > 0) {
              const lastEntry = history[history.length - 1];
              updateHistoryEntry(lastEntry.timestamp, improvedData.improved_value);
            }
            
            // Format response for LogCallButton compatibility
            const apiResponse: APIResponse = {
              results: [updatedCall]
            };
            setResponse(apiResponse);
          } else {
            console.log('❌ Cannot update - missing data or call state is null');
          }
          
          setImprovementInProgress(false);
          updateReviewSections([]);
          setReviewStatus('✅ Response improved! Analyzing for further improvements...');
        }
      );
    } catch (err) {
      setWebSocketError((err as Error).message);
      setIsLoading(false);
      setIsProcessing(false);
      setCurrentTool(null);
    }
  };

  // Clear call data when starting new call
  const handleNewCall = () => {
    console.log('🗑️ Clearing call state in handleNewCall');
    setCall(null);
    callRef.current = null;
    setResponse(null);
    setStreamingText('');
    clearError();
    setIsProcessing(false);
    setCurrentTool(null);
    clearReviewState();
    clearError();
    clearHistory();
  };

  // Handle improvement request
  const handleImprove = (section: string) => {
    if (!callService) {
      setWebSocketError('WebSocket connection not available');
      return;
    }
    
    const sectionData = reviewState.reviewableSections.find(s => s.section === section);
    if (sectionData) {
      startImprovement(section, sectionData.questions);
    }
  };

  // Handle improvement answers submission
  const handleAnswers = (answers: string[]) => {
    if (!callService || !reviewState.improvingSection) {
      setImprovementError('WebSocket connection or section not available');
      return;
    }
    
    try {
      // Add to improvement history
      addHistoryEntry({
        section: reviewState.improvingSection,
        questions: reviewState.currentQuestions,
        answers: answers,
        originalContent: call?.prediction_statement || ''
      });
      
      setImprovementInProgress(true);
      
      // Set improvement in progress flag
      (callService as any).setImprovementInProgress(true);
      
      // Send improvement request via WebSocket
      const websocketService = (callService as any).websocket;
      if (websocketService) {
        websocketService.send('improvement_answers', {
          section: reviewState.improvingSection,
          answers: answers,
          original_value: call?.[reviewState.improvingSection] || '',
          full_context: call
        });
        
        console.log('Sent improvement answers:', {
          section: reviewState.improvingSection,
          answers: answers
        });
      } else {
        throw new Error('WebSocket service not available');
      }
    } catch (err) {
      setImprovementError((err as Error).message);
      setImprovementInProgress(false);
    }
  };

  // Handle modal cancel
  const handleModalCancel = () => {
    cancelImprovement();
  };

  // Error handler for LogCallButton
  const handleLogCallError = (error: string | null | ((prev: string | null) => string | null)) => {
    if (typeof error === 'string') {
      setWebSocketError(error);
    } else if (error === null) {
      clearError();
    } else if (typeof error === 'function') {
      const result = error(errorState.message);
      if (result) {
        setWebSocketError(result);
      } else {
        clearError();
      }
    }
  };

  return (
    <div className="streaming-call" style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <h2 style={{ margin: 0 }}>Make a Call (Streaming)</h2>
        {reconnectCount > 0 && (
          <div style={{
            padding: '4px 8px',
            borderRadius: '4px',
            backgroundColor: '#fff3cd',
            border: '1px solid #ffeaa7',
            color: '#856404',
            fontSize: '12px'
          }}>
            🔄 Reconnecting... ({reconnectCount}/3)
          </div>
        )}
      </div>
      
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
          disabled={isLoading || !prompt.trim() || !callService} 
          style={{
            padding: '10px 20px',
            backgroundColor: isLoading ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: (isLoading || !callService) ? 'not-allowed' : 'pointer'
          }}
        >
          {!callService ? 'Connecting...' : (isLoading ? 'Processing...' : 'Make Call')}
        </button>
      </form>
      
      {hasError && (
        <div style={{ 
          backgroundColor: '#f8d7da', 
          color: '#721c24', 
          padding: '10px', 
          borderRadius: '4px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <p style={{ margin: 0 }}>Error: {errorState.message}</p>
          <button 
            onClick={clearError}
            style={{
              background: 'none',
              border: 'none',
              color: '#721c24',
              cursor: 'pointer',
              fontSize: '16px',
              padding: '0 4px'
            }}
          >
            ×
          </button>
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
              {reviewState.reviewableSections.find(s => s.section === 'prediction_statement') ? (
                <ReviewableSection
                  section="prediction_statement"
                  content={call.prediction_statement}
                  isReviewable={true}
                  questions={reviewState.reviewableSections.find(s => s.section === 'prediction_statement')?.questions || []}
                  reasoning={reviewState.reviewableSections.find(s => s.section === 'prediction_statement')?.reasoning}
                  onImprove={handleImprove}
                />
              ) : (
                <p>{call.prediction_statement}</p>
              )}
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
                {reviewState.reviewableSections.find(s => s.section === 'verifiable_category') ? (
                  <ReviewableSection
                    section="verifiable_category"
                    content={call.verifiable_category}
                    isReviewable={true}
                    questions={reviewState.reviewableSections.find(s => s.section === 'verifiable_category')?.questions || []}
                    reasoning={reviewState.reviewableSections.find(s => s.section === 'verifiable_category')?.reasoning}
                    onImprove={handleImprove}
                  />
                ) : (
                  <p>{getVerifiabilityDisplay(call.verifiable_category)}</p>
                )}
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
                  {reviewState.reviewableSections.find(s => s.section === 'verification_method') && (
                    <ReviewableSection
                      section="verification_method"
                      content="Click to improve verification method"
                      isReviewable={true}
                      questions={reviewState.reviewableSections.find(s => s.section === 'verification_method')?.questions || []}
                      reasoning={reviewState.reviewableSections.find(s => s.section === 'verification_method')?.reasoning}
                      onImprove={handleImprove}
                    />
                  )}
                  <div className="method-section">
                    <h4>Sources:</h4>
                    <ul>
                      {call.verification_method.source?.map((item: string, index: number) => (
                        <li key={`source-${index}`}>{item}</li>
                      )) || <li>No sources available</li>}
                    </ul>
                  </div>
                  <div className="method-section">
                    <h4>Criteria:</h4>
                    <ul>
                      {call.verification_method.criteria?.map((item: string, index: number) => (
                        <li key={`criteria-${index}`}>{item}</li>
                      )) || <li>No criteria available</li>}
                    </ul>
                  </div>
                  <div className="method-section">
                    <h4>Steps:</h4>
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
          
          {reviewState.reviewStatus && (
            <div style={{
              marginTop: '20px',
              padding: '12px 16px',
              borderRadius: '8px',
              backgroundColor: reviewState.reviewableSections.length > 0 ? '#fff3cd' : '#d4edda',
              border: `1px solid ${reviewState.reviewableSections.length > 0 ? '#ffeaa7' : '#c3e6cb'}`,
              color: reviewState.reviewableSections.length > 0 ? '#856404' : '#155724'
            }}>
              <strong>Review Status:</strong> {reviewState.reviewStatus}
            </div>
          )}
          
          {reviewState.isImproving && (
            <div style={{
              marginTop: '20px',
              padding: '12px 16px',
              borderRadius: '8px',
              backgroundColor: '#cce7ff',
              border: '1px solid #007bff',
              color: '#004085',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <span>🔄</span>
              <span>Improving response with your input...</span>
            </div>
          )}
          <div style={{ marginTop: '10px' }}>
            <LogCallButton
              response={response}
              isLoading={isLoading}
              isVisible={true}
              setIsLoading={setIsLoading}
              setError={handleLogCallError}
              setResponse={setResponse}
              setPrompt={setPrompt}
              onSuccessfulLog={onNavigateToList}
            />
          </div>
        </div>
      )}
      
      <ImprovementModal
        isOpen={reviewState.showImprovementModal}
        section={reviewState.improvingSection || ''}
        questions={reviewState.currentQuestions}
        reasoning={reviewState.reviewableSections.find(s => s.section === reviewState.improvingSection)?.reasoning}
        onSubmit={handleAnswers}
        onCancel={handleModalCancel}
      />
    </div>
  );
};

export default StreamingCall;