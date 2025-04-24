import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import LogCallButton from './LogCallButton';

describe('LogCallButton Component', () => {
  it('renders nothing when isVisible is false', () => {
    const mockLogCall = vi.fn();
    const { container } = render(
      <LogCallButton onLogCall={mockLogCall} isLoading={false} isVisible={false} />
    );
    
    expect(container.firstChild).toBeNull();
  });

  it('renders the button when isVisible is true', () => {
    const mockLogCall = vi.fn();
    render(
      <LogCallButton onLogCall={mockLogCall} isLoading={false} isVisible={true} />
    );
    
    expect(screen.getByText('Log Call')).toBeInTheDocument();
  });

  it('calls onLogCall when clicked', () => {
    const mockLogCall = vi.fn();
    render(
      <LogCallButton onLogCall={mockLogCall} isLoading={false} isVisible={true} />
    );
    
    const button = screen.getByText('Log Call');
    fireEvent.click(button);
    
    expect(mockLogCall).toHaveBeenCalledTimes(1);
  });

  it('shows loading state when isLoading is true', () => {
    const mockLogCall = vi.fn();
    render(
      <LogCallButton onLogCall={mockLogCall} isLoading={true} isVisible={true} />
    );
    
    expect(screen.getByText('Logging...')).toBeInTheDocument();
    const button = screen.getByText('Logging...');
    expect(button).toBeDisabled();
  });
});