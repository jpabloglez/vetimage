import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Client-side route changes don't reset scroll position the way a full page
 * load does — without this, navigating (e.g. from a link deep in a page's
 * footer) leaves the new page scrolled to wherever the previous one was.
 */
export const ScrollToTop: React.FC = () => {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
};

export default ScrollToTop;
