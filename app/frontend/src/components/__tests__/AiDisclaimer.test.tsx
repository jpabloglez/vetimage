import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AiDisclaimer from '../AiDisclaimer';

describe('AiDisclaimer', () => {
  it('renders the decision-support (not a diagnosis) notice', () => {
    render(<AiDisclaimer />);
    expect(screen.getByText(/Decision support — not a diagnosis/i)).toBeInTheDocument();
    expect(screen.getByText(/veterinarian must review/i)).toBeInTheDocument();
    expect(screen.getByText(/may miss findings/i)).toBeInTheDocument();
  });

  it('exposes the note role for assistive tech and applies extra classes', () => {
    const { container } = render(<AiDisclaimer className="mb-6" />);
    const note = screen.getByRole('note');
    expect(note).toBeInTheDocument();
    expect(container.firstChild).toHaveClass('mb-6');
  });
});
