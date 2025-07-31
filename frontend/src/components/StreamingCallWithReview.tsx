import React, { useState, useEffect } from 'react';
import { ReviewStatus } from './ReviewStatus';
import { ReviewableSection } from './ReviewableSection';
import { handleReviewMessages, ReviewSection } from '../services/reviewWebSocket';

export const StreamingCallWithReview: React.FC = () => {
  const [callResponse, setCallResponse] = useState<any>(null);
  const [reviewStatus, setReviewStatus] = useState<string>('');
  const [reviewSections, setReviewSections] = useState<ReviewSection[]>([]);
  const [isReviewing, setIsReviewing] = useState<boolean>(false);
  const [isReviewComplete, setIsReviewComplete] = useState<boolean>(false);

  // WebSocket message handler
  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'call_response':
        // Initial response received
        setCallResponse(JSON.parse(message.content));
        break;
        
      case 'status':
        if (message.status === 'reviewing') {
          setIsReviewing(true);
        }
        break;
        
      default:
        // Handle review messages
        handleReviewMessages(
          message,
          setReviewStatus,
          setReviewSections,
          (complete) => {
            setIsReviewComplete(complete);
            setIsReviewing(false);
          }
        );
    }
  };

  const handleSectionImprovement = (section: string, questions: string[]) => {
    // TODO: Implement improvement flow
    console.log(`Improving section: ${section}`, questions);
  };

  return (
    <div style={{ padding: '20px' }}>
      {/* Initial Call Response */}
      {callResponse && (
        <div style={{ marginBottom: '20px' }}>
          <h3>Your Prediction:</h3>
          <div style={{ 
            padding: '16px', 
            backgroundColor: '#f9fafb', 
            borderRadius: '8px',
            border: '1px solid #e5e7eb'
          }}>
            <p><strong>Statement:</strong> {callResponse.prediction_statement}</p>
            <p><strong>Verification Date:</strong> {callResponse.verification_date}</p>
            <p><strong>Category:</strong> {callResponse.verifiable_category}</p>
          </div>
        </div>
      )}

      {/* Review Status */}
      <ReviewStatus 
        status={reviewStatus}
        isReviewing={isReviewing}
        isComplete={isReviewComplete}
      />

      {/* Reviewable Sections */}
      {isReviewComplete && reviewSections.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <h4>Sections You Can Improve:</h4>
          {reviewSections.map((section, index) => (
            <ReviewableSection
              key={index}
              section={section}
              content={callResponse?.[section.section] || 'N/A'}
              onImprove={handleSectionImprovement}
            />
          ))}
        </div>
      )}
    </div>
  );
};