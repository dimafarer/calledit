import React, { useState } from 'react';

interface ImprovementModalProps {
  isOpen: boolean;
  section: string;
  questions: string[];
  reasoning?: string;
  onSubmit: (answers: string[]) => void;
  onCancel: () => void;
}

const ImprovementModal: React.FC<ImprovementModalProps> = ({
  isOpen,
  section,
  questions,
  reasoning,
  onSubmit,
  onCancel
}) => {
  const [answers, setAnswers] = useState<string[]>(new Array(questions.length).fill(''));

  if (!isOpen) return null;

  const handleAnswerChange = (index: number, value: string) => {
    const newAnswers = [...answers];
    newAnswers[index] = value;
    setAnswers(newAnswers);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const validAnswers = answers.filter(answer => answer.trim() !== '');
    if (validAnswers.length > 0) {
      onSubmit(answers);
      setAnswers(new Array(questions.length).fill(''));
    }
  };

  const handleCancel = () => {
    setAnswers(new Array(questions.length).fill(''));
    onCancel();
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '20px'
      }}
      onClick={handleCancel}
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '24px',
          maxWidth: '500px',
          width: '100%',
          maxHeight: '80vh',
          overflowY: 'auto',
          boxShadow: '0 10px 25px rgba(0, 0, 0, 0.2)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ marginBottom: '20px' }}>
          <h3 style={{ margin: '0 0 8px 0', color: '#333' }}>
            ✨ Improve {section.replace('_', ' ')}
          </h3>
          {reasoning && (
            <p style={{ 
              margin: '0 0 16px 0', 
              color: '#666', 
              fontSize: '14px',
              fontStyle: 'italic'
            }}>
              {reasoning}
            </p>
          )}
        </div>

        <form onSubmit={handleSubmit}>
          {questions.map((question, index) => (
            <div key={index} style={{ marginBottom: '16px' }}>
              <label 
                style={{ 
                  display: 'block', 
                  marginBottom: '6px', 
                  fontWeight: '500',
                  color: '#333'
                }}
              >
                {question}
              </label>
              <textarea
                value={answers[index]}
                onChange={(e) => handleAnswerChange(index, e.target.value)}
                placeholder="Your answer..."
                rows={3}
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '14px',
                  resize: 'vertical',
                  fontFamily: 'inherit'
                }}
              />
            </div>
          ))}

          <div style={{ 
            display: 'flex', 
            gap: '12px', 
            justifyContent: 'flex-end',
            marginTop: '24px'
          }}>
            <button
              type="button"
              onClick={handleCancel}
              style={{
                padding: '10px 20px',
                border: '1px solid #ddd',
                backgroundColor: 'white',
                color: '#666',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={answers.every(answer => answer.trim() === '')}
              style={{
                padding: '10px 20px',
                border: 'none',
                backgroundColor: answers.some(answer => answer.trim() !== '') ? '#007bff' : '#ccc',
                color: 'white',
                borderRadius: '4px',
                cursor: answers.some(answer => answer.trim() !== '') ? 'pointer' : 'not-allowed',
                fontSize: '14px'
              }}
            >
              Improve Response
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ImprovementModal;