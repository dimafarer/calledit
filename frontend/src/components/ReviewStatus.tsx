import React from 'react';

interface ReviewStatusProps {
  status: string;
  isReviewing: boolean;
  isComplete: boolean;
}

export const ReviewStatus: React.FC<ReviewStatusProps> = ({
  status,
  isReviewing,
  isComplete
}) => {
  const getStatusStyle = () => {
    if (isReviewing) {
      return {
        backgroundColor: '#fef3c7',
        borderColor: '#f59e0b',
        color: '#92400e'
      };
    }
    
    if (isComplete) {
      return {
        backgroundColor: '#d1fae5',
        borderColor: '#10b981',
        color: '#065f46'
      };
    }
    
    return {
      backgroundColor: '#f3f4f6',
      borderColor: '#d1d5db',
      color: '#374151'
    };
  };

  return (
    <div
      style={{
        padding: '12px 16px',
        margin: '8px 0',
        borderRadius: '8px',
        border: '1px solid',
        fontSize: '14px',
        fontWeight: '500',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        ...getStatusStyle()
      }}
    >
      {isReviewing && (
        <div
          style={{
            width: '16px',
            height: '16px',
            border: '2px solid currentColor',
            borderTop: '2px solid transparent',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }}
        />
      )}
      <span>{status}</span>
      
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};