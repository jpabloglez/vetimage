import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FindingsOverlay } from '../FindingsOverlay';

// Mock cornerstone-core: a 100x100 image, identity-ish pixel→canvas mapping.
vi.mock('cornerstone-core', () => ({
  getEnabledElement: () => ({ image: { width: 100, height: 100 } }),
  pixelToCanvas: (_el: any, p: { x: number; y: number }) => ({ x: p.x, y: p.y }),
}));

const findings = [
  { label: 'cardiomegaly', region: 'cardiac', confidence: 0.83, bbox: [0.4, 0.45, 0.3, 0.35] as [number, number, number, number] },
  { label: 'no_box', region: 'lung', confidence: 0.6 }, // no bbox -> not drawn
];

describe('FindingsOverlay', () => {
  let element: HTMLDivElement;
  beforeEach(() => {
    element = document.createElement('div');
  });

  it('draws a box (with label + confidence) only for findings that have a bbox', () => {
    render(<FindingsOverlay element={element} findings={findings as any} visible />);
    expect(screen.getByTestId('findings-overlay')).toBeInTheDocument();
    expect(screen.getByText(/cardiomegaly · 83%/)).toBeInTheDocument();
    expect(screen.queryByText(/no box/)).not.toBeInTheDocument();
  });

  it('renders nothing when hidden', () => {
    render(<FindingsOverlay element={element} findings={findings as any} visible={false} />);
    expect(screen.queryByTestId('findings-overlay')).not.toBeInTheDocument();
  });

  it('renders nothing when there are no boxed findings', () => {
    render(<FindingsOverlay element={element} findings={[{ label: 'x' }] as any} visible />);
    expect(screen.queryByTestId('findings-overlay')).not.toBeInTheDocument();
  });
});
