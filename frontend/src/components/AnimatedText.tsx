import React from 'react';

interface AnimatedTextProps {
  text: string;
  className?: string;
}

const AnimatedText: React.FC<AnimatedTextProps> = ({ text, className = '' }) => {
  return (
    <div className={`animated-text ${className}`}>
      {text}
    </div>
  );
};

export default AnimatedText;