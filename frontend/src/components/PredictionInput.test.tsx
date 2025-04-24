import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PredictionInput from './PredictionInput';

describe('PredictionInput Component', () => {
  it('renders the input field and button', () => {
    const mockSubmit = vi.fn();
    render(<PredictionInput onSubmit={mockSubmit} isLoading={false} />);
    
    expect(screen.getByPlaceholderText('Enter your prediction here...')).toBeInTheDocument();
    expect(screen.getByText('Make Call')).toBeInTheDocument();
  });

  it('disables the button when input is empty', () => {
    const mockSubmit = vi.fn();
    render(<PredictionInput onSubmit={mockSubmit} isLoading={false} />);
    
    const button = screen.getByText('Make Call');
    expect(button).toBeDisabled();
  });

  it('enables the button when input has text', () => {
    const mockSubmit = vi.fn();
    render(<PredictionInput onSubmit={mockSubmit} isLoading={false} />);
    
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test prediction' } });
    
    const button = screen.getByText('Make Call');
    expect(button).not.toBeDisabled();
  });

  it('calls onSubmit with input text when button is clicked', () => {
    const mockSubmit = vi.fn();
    render(<PredictionInput onSubmit={mockSubmit} isLoading={false} />);
    
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test prediction' } });
    
    const button = screen.getByText('Make Call');
    fireEvent.click(button);
    
    expect(mockSubmit).toHaveBeenCalledWith('Test prediction');
  });

  it('shows loading state when isLoading is true', () => {
    const mockSubmit = vi.fn();
    render(<PredictionInput onSubmit={mockSubmit} isLoading={true} />);
    
    expect(screen.getByText('Generating...')).toBeInTheDocument();
    const button = screen.getByText('Generating...');
    expect(button).toBeDisabled();
  });
});