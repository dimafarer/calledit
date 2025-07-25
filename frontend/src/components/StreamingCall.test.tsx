import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import StreamingCall from './StreamingCall';
import { CallService } from '../services/callService';

// Mock the CallService
vi.mock('../services/callService');
const MockedCallService = vi.mocked(CallService);

// Mock LogCallButton component
vi.mock('./LogCallButton', () => ({
  default: ({ isVisible, response }: { isVisible: boolean; response: any }) => (
    <div data-testid="log-call-button">
      {isVisible && response && <span>Log Call Available</span>}
    </div>
  ),
}));

describe('StreamingCall', () => {
  const mockWebSocketUrl = 'wss://test-websocket-url';
  const mockOnNavigateToList = vi.fn();
  let mockCallService: any;

  beforeEach(() => {
    mockCallService = {
      makeCallWithStreaming: vi.fn(),
      cleanup: vi.fn(),
    };
    MockedCallService.mockImplementation(() => mockCallService);
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('renders the streaming call interface', () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    expect(screen.getByText('Make a Call (Streaming)')).toBeInTheDocument();
    expect(screen.getByLabelText('Your Call:')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Make Call' })).toBeInTheDocument();
  });

  it('initializes CallService with correct WebSocket URL', () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    expect(MockedCallService).toHaveBeenCalledWith(mockWebSocketUrl);
  });

  it('disables submit button when prompt is empty', () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    expect(submitButton).toBeDisabled();
  });

  it('enables submit button when prompt has content', () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    fireEvent.change(textarea, { target: { value: 'Test prediction' } });
    
    expect(submitButton).not.toBeDisabled();
  });

  it('shows loading state during call processing', async () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    // Mock a long-running call
    mockCallService.makeCallWithStreaming.mockImplementation(() => new Promise(() => {}));
    
    fireEvent.change(textarea, { target: { value: 'Test prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Processing...')).toBeInTheDocument();
      expect(textarea).toBeDisabled();
    });
  });

  it('displays streaming text during processing', async () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    // Mock streaming with text chunks
    mockCallService.makeCallWithStreaming.mockImplementation(
      (_prompt: string, onText: (text: string) => void, _onTool: (tool: string) => void, _onComplete: (response: any) => void, _onError: (error: string) => void) => {
        onText('Processing your prediction...');
        onText(' with AI agent');
        return Promise.resolve();
      }
    );
    
    fireEvent.change(textarea, { target: { value: 'Test prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Processing your call...')).toBeInTheDocument();
      expect(screen.getByText(/Processing your prediction... with AI agent/)).toBeInTheDocument();
    });
  });

  it('displays tool usage during processing', async () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    // Mock streaming with tool usage
    mockCallService.makeCallWithStreaming.mockImplementation(
      (_prompt: string, _onText: (text: string) => void, onTool: (tool: string) => void, _onComplete: (response: any) => void, _onError: (error: string) => void) => {
        onTool('current_time');
        return Promise.resolve();
      }
    );
    
    fireEvent.change(textarea, { target: { value: 'Test prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/\[Using tool: current_time\]/)).toBeInTheDocument();
    });
  });

  it('displays call details after successful completion', async () => {
    const mockResponse = {
      prediction_statement: 'Bitcoin will hit $100k tomorrow',
      verification_date: '2025-01-28T15:00:00Z',
      verifiable_category: 'api_tool_verifiable',
      category_reasoning: 'Requires external API data',
      verification_method: {
        source: ['CoinGecko API'],
        criteria: ['BTC price exceeds $100k'],
        steps: ['Check price on date']
      },
      initial_status: 'pending'
    };

    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    // Mock successful completion
    mockCallService.makeCallWithStreaming.mockImplementation(
      (_prompt: string, _onText: (text: string) => void, _onTool: (tool: string) => void, onComplete: (response: any) => void, _onError: (error: string) => void) => {
        onComplete(JSON.stringify(mockResponse));
        return Promise.resolve();
      }
    );
    
    fireEvent.change(textarea, { target: { value: 'Test prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Call Details')).toBeInTheDocument();
      expect(screen.getByText('Bitcoin will hit $100k tomorrow')).toBeInTheDocument();
      expect(screen.getByText('API Verifiable')).toBeInTheDocument();
      expect(screen.getByText('Requires external API data')).toBeInTheDocument();
    });
  });

  it('displays verifiability category with correct styling', async () => {
    const mockResponse = {
      prediction_statement: 'Test prediction',
      verifiable_category: 'agent_verifiable',
      category_reasoning: 'Pure reasoning test'
    };

    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    mockCallService.makeCallWithStreaming.mockImplementation(
      (_prompt: string, _onText: (text: string) => void, _onTool: (tool: string) => void, onComplete: (response: any) => void, _onError: (error: string) => void) => {
        onComplete(JSON.stringify(mockResponse));
        return Promise.resolve();
      }
    );
    
    fireEvent.change(textarea, { target: { value: 'Test prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      const categoryElement = screen.getByText('Agent Verifiable');
      expect(categoryElement).toBeInTheDocument();
      
      // Check for brain emoji (agent_verifiable icon)
      expect(screen.getByText('🧠')).toBeInTheDocument();
    });
  });

  it('handles different verifiability categories correctly', async () => {
    const categories = [
      { category: 'current_tool_verifiable', label: 'Time-Tool Verifiable', icon: '⏰' },
      { category: 'strands_tool_verifiable', label: 'Strands-Tool Verifiable', icon: '🔧' },
      { category: 'api_tool_verifiable', label: 'API Verifiable', icon: '🌐' },
      { category: 'human_verifiable_only', label: 'Human Verifiable Only', icon: '👤' }
    ];

    for (const { category, label, icon } of categories) {
      const mockResponse = {
        prediction_statement: 'Test prediction',
        verifiable_category: category
      };

      const { unmount } = render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
      
      const textarea = screen.getByLabelText('Your Call:');
      const submitButton = screen.getByRole('button', { name: 'Make Call' });
      
      mockCallService.makeCallWithStreaming.mockImplementation(
        (_prompt: string, _onText: (text: string) => void, _onTool: (tool: string) => void, onComplete: (response: any) => void, _onError: (error: string) => void) => {
          onComplete(JSON.stringify(mockResponse));
          return Promise.resolve();
        }
      );
      
      fireEvent.change(textarea, { target: { value: 'Test prediction' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(label)).toBeInTheDocument();
        expect(screen.getByText(icon)).toBeInTheDocument();
      });
      
      unmount();
    }
  });

  it('displays error messages when call fails', async () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    // Mock error during streaming
    mockCallService.makeCallWithStreaming.mockImplementation(
      (_prompt: string, _onText: (text: string) => void, _onTool: (tool: string) => void, _onComplete: (response: any) => void, onError: (error: string) => void) => {
        onError('WebSocket connection failed');
        return Promise.resolve();
      }
    );
    
    fireEvent.change(textarea, { target: { value: 'Test prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Error: WebSocket connection failed')).toBeInTheDocument();
    });
  });

  it('clears previous data when starting new call', async () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    // First call with success
    mockCallService.makeCallWithStreaming.mockImplementationOnce(
      (_prompt: string, _onText: (text: string) => void, _onTool: (tool: string) => void, onComplete: (response: any) => void, _onError: (error: string) => void) => {
        onComplete(JSON.stringify({ prediction_statement: 'First call' }));
        return Promise.resolve();
      }
    );
    
    fireEvent.change(textarea, { target: { value: 'First prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('First call')).toBeInTheDocument();
    });
    
    // Second call should clear previous data
    mockCallService.makeCallWithStreaming.mockImplementationOnce(
      (_prompt: string, _onText: (text: string) => void, _onTool: (tool: string) => void, _onComplete: (response: any) => void, _onError: (error: string) => void) => {
        // Don't complete immediately to test clearing
        return new Promise(() => {});
      }
    );
    
    fireEvent.change(textarea, { target: { value: 'Second prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.queryByText('First call')).not.toBeInTheDocument();
    });
  });

  it('shows LogCallButton when call is completed', async () => {
    const mockResponse = {
      prediction_statement: 'Test prediction',
      verifiable_category: 'agent_verifiable'
    };

    render(<StreamingCall webSocketUrl={mockWebSocketUrl} onNavigateToList={mockOnNavigateToList} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    mockCallService.makeCallWithStreaming.mockImplementation(
      (_prompt: string, _onText: (text: string) => void, _onTool: (tool: string) => void, onComplete: (response: any) => void, _onError: (error: string) => void) => {
        onComplete(JSON.stringify(mockResponse));
        return Promise.resolve();
      }
    );
    
    fireEvent.change(textarea, { target: { value: 'Test prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByTestId('log-call-button')).toBeInTheDocument();
      expect(screen.getByText('Log Call Available')).toBeInTheDocument();
    });
  });

  it('cleans up CallService on unmount', () => {
    const { unmount } = render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    unmount();
    
    expect(mockCallService.cleanup).toHaveBeenCalled();
  });

  it('handles JSON parsing errors gracefully', async () => {
    render(<StreamingCall webSocketUrl={mockWebSocketUrl} />);
    
    const textarea = screen.getByLabelText('Your Call:');
    const submitButton = screen.getByRole('button', { name: 'Make Call' });
    
    // Mock completion with invalid JSON
    mockCallService.makeCallWithStreaming.mockImplementation(
      (_prompt: string, _onText: (text: string) => void, _onTool: (tool: string) => void, onComplete: (response: any) => void, _onError: (error: string) => void) => {
        onComplete('Invalid JSON response');
        return Promise.resolve();
      }
    );
    
    fireEvent.change(textarea, { target: { value: 'Test prediction' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      // Should still show call details even with parsing error
      expect(screen.getByText('Call Details')).toBeInTheDocument();
    });
  });
});