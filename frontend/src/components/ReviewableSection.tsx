import React, { useState } from 'react';

interface ReviewableSection {
  section: string;
  improvable: boolean;
  questions: string[];
  reasoning: string;
}

interface ReviewableSectionProps {
  section: ReviewableSection;
  content: string;
  onImprove: (section: string, questions: string[]) => void;
}

export const ReviewableSection: React.FC<ReviewableSectionProps> = ({
  section,
  content,
  onImprove
}) => {
  const [isHighlighted, setIsHighlighted] = useState(section.improvable);

  const handleClick = () => {
    if (section.improvable) {
      onImprove(section.section, section.questions);
    }
  };

  const sectionStyle = {
    padding: '12px',
    margin: '8px 0',
    borderRadius: '8px',
    cursor: section.improvable ? 'pointer' : 'default',
    minHeight: '44px', // Mobile-friendly touch target
    display: 'flex',
    alignItems: 'center',
    position: 'relative' as const,
    border: section.improvable ? '2px solid #3b82f6' : '1px solid #e5e7eb',
    backgroundColor: section.improvable ? '#eff6ff' : '#ffffff',
    transition: 'all 0.2s ease-in-out'
  };

  const iconStyle = {
    marginLeft: '8px',
    fontSize: '16px',
    color: '#3b82f6'
  };

  return (
    <div 
      style={sectionStyle}
      onClick={handleClick}
      role={section.improvable ? 'button' : undefined}
      tabIndex={section.improvable ? 0 : undefined}
      onKeyDown={(e) => {
        if (section.improvable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <div style={{ flex: 1 }}>
        <strong>{section.section.replace('_', ' ').toUpperCase()}:</strong>
        <div style={{ marginTop: '4px' }}>{content}</div>
        {section.improvable && (
          <div style={{ 
            fontSize: '12px', 
            color: '#6b7280', 
            marginTop: '4px',
            fontStyle: 'italic'
          }}>
            💡 {section.reasoning}
          </div>
        )}
      </div>
      {section.improvable && (
        <div style={iconStyle}>
          ✨
        </div>
      )}
    </div>
  );
};