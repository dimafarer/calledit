import React from 'react';

interface AnimatedTextProps {
  text: string;
  className?: string;
}

const AnimatedText: React.FC<AnimatedTextProps> = ({ text, className = '' }) => {
  // Split text into words and add wiggle to each
  const words = text.split(/\s+/).filter(word => word.length > 0);
  
  return (
    <div className={`animated-text ${className}`}>
      {words.map((word, index) => (
        <span
          key={`${word}-${index}`}
          style={{
            display: 'inline-block',
            marginRight: '0.25em',
            transform: `rotate(${(Math.random() - 0.5) * 4}deg)` // Random -2° to +2°
          }}
        >
          {word}
        </span>
      ))}
    </div>
  );
};

export default AnimatedText;