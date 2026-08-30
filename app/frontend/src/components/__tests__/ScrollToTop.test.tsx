import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Link } from 'react-router-dom';
import ScrollToTop from '../ScrollToTop';

const Page: React.FC<{ label: string }> = ({ label }) => (
  <div>
    <h1>{label}</h1>
    <Link to="/other">Go to other page</Link>
  </div>
);

describe('ScrollToTop', () => {
  beforeEach(() => {
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  });

  it('scrolls to the top on every route change', () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={['/first']}>
        <ScrollToTop />
        <Routes>
          <Route path="/first" element={<Page label="First" />} />
          <Route path="/other" element={<Page label="Other" />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(window.scrollTo).toHaveBeenCalledTimes(1);
    expect(window.scrollTo).toHaveBeenLastCalledWith(0, 0);

    fireEvent.click(getByText('Go to other page'));

    expect(window.scrollTo).toHaveBeenCalledTimes(2);
  });
});
