import React from 'react';

interface ReviewableSectionProps {
  section: string;
  content: string;
  isReviewable: boolean;
  questions?: string[];
  reasoning?: string;
  onImprove: (section: string) => void;
}

const ReviewableSection: React.FC<ReviewableSectionProps> = ({
  section,
  content,
  isReviewable,
  reasoning,
  onImprove
}) => {
  if (!isReviewable) {
    return <span>{content}</span>;
  }

  return (
    <div 
      className="reviewable-section"
      onClick={() => onImprove(section)}
      style={{
        position: 'relative',
        display: 'inline-block',
        border: '2px dashed #007bff',
        borderRadius: '6px',
        padding: '8px 12px',
        margin: '2px',
        cursor: 'pointer',
        backgroundColor: 'rgba(0, 123, 255, 0.15)',
        color: '#007bff',
        fontWeight: '500',
        transition: 'all 0.2s ease',
        minHeight: '44px',
        minWidth: '44px'
      }}
      title={reasoning || `Click to improve ${section}`}
    >
      {content}
      
      <div
        style={{
          position: 'absolute',
          top: '-8px',
          right: '-8px',
          backgroundColor: '#007bff',
          color: 'white',
          borderRadius: '50%',
          width: '20px',
          height: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '12px',
          fontWeight: 'bold',
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
        }}
      >
        ✨
      </div>
    </div>
  );
};

export default ReviewableSection;