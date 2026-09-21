import { useEffect } from 'react';
import { ENTITY } from '../pages/legalInfo';

// Sets the browser-tab title for a route and restores the previous one on the
// way out. document.title rather than a React <title>: index.html already has a
// static <title> for crawlers, and the first one in <head> wins.
export function usePageTitle(title) {
  useEffect(() => {
    const previous = document.title;
    document.title = `${title} · ${ENTITY.brand}`;
    return () => { document.title = previous; };
  }, [title]);
}
