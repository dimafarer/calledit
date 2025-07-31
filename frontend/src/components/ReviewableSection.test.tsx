import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReviewableSection } from './ReviewableSection';

describe('ReviewableSection', () => {
  const mockOnImprove = vi.fn();

  const improvableSection = {
    section: 'prediction_statement',
    improvable: true,
    questions: ['What specific time of day?', 'Any location constraints?'],
    reasoning: 'More temporal precision could change verifiability category'
  };

  const nonImprovableSection = {
    section: 'verification_method',
    improvable: false,
    questions: [],
    reasoning: 'Verification method is already optimal'
  };

  beforeEach(() => {
    mockOnImprove.mockClear();
  });

  test('renders section content correctly', () => {
    render(
      <ReviewableSection
        section={improvableSection}
        content="Bitcoin will hit $100k today"
        onImprove={mockOnImprove}
      />
    );

    expect(screen.getByText((content, element) => {
      return element?.textContent === 'PREDICTION STATEMENT:';
    })).toBeInTheDocument();
    expect(screen.getByText('Bitcoin will hit $100k today')).toBeInTheDocument();
  });

  test('shows improvement reasoning for improvable sections', () => {
    render(
      <ReviewableSection
        section={improvableSection}
        content="Bitcoin will hit $100k today"
        onImprove={mockOnImprove}
      />
    );

    expect(screen.getByText(/More temporal precision could change verifiability category/)).toBeInTheDocument();
    expect(screen.getByText('✨')).toBeInTheDocument();
  });

  test('does not show improvement UI for non-improvable sections', () => {
    render(
      <ReviewableSection
        section={nonImprovableSection}
        content="Check API at end of day"
        onImprove={mockOnImprove}
      />
    );

    expect(screen.queryByText('✨')).not.toBeInTheDocument();
    expect(screen.queryByText(/More temporal precision/)).not.toBeInTheDocument();
  });

  test('calls onImprove when improvable section is clicked', () => {
    render(
      <ReviewableSection
        section={improvableSection}
        content="Bitcoin will hit $100k today"
        onImprove={mockOnImprove}
      />
    );

    const sectionElement = screen.getByRole('button');
    fireEvent.click(sectionElement);

    expect(mockOnImprove).toHaveBeenCalledWith(
      'prediction_statement',
      ['What specific time of day?', 'Any location constraints?']
    );
  });

  test('handles keyboard navigation for improvable sections', () => {
    render(
      <ReviewableSection
        section={improvableSection}
        content="Bitcoin will hit $100k today"
        onImprove={mockOnImprove}
      />
    );

    const sectionElement = screen.getByRole('button');
    
    // Test Enter key
    fireEvent.keyDown(sectionElement, { key: 'Enter' });
    expect(mockOnImprove).toHaveBeenCalledTimes(1);

    // Test Space key
    fireEvent.keyDown(sectionElement, { key: ' ' });
    expect(mockOnImprove).toHaveBeenCalledTimes(2);

    // Test other keys (should not trigger)
    fireEvent.keyDown(sectionElement, { key: 'Tab' });
    expect(mockOnImprove).toHaveBeenCalledTimes(2);
  });

  test('formats section names correctly', () => {
    render(
      <ReviewableSection
        section={improvableSection}
        content="Bitcoin will hit $100k today"
        onImprove={mockOnImprove}
      />
    );

    // Should convert prediction_statement to PREDICTION STATEMENT
    expect(screen.getByText((content, element) => {
      return element?.textContent === 'PREDICTION STATEMENT:';
    })).toBeInTheDocument();
  });

  test('has proper accessibility attributes', () => {
    render(
      <ReviewableSection
        section={improvableSection}
        content="Bitcoin will hit $100k today"
        onImprove={mockOnImprove}
      />
    );

    const sectionElement = screen.getByRole('button');
    expect(sectionElement).toHaveAttribute('tabIndex', '0');
  });
});