import { useEffect, useState } from 'react';

interface Viewport {
  isMobile: boolean;
  isTablet: boolean;
  isLaptop: boolean;
  isDesktop: boolean;
}

export const useViewport = (): Viewport => {
  const [size, setSize] = useState<Viewport>({
    isMobile: false,
    isTablet: false,
    isLaptop: false,
    isDesktop: false,
  });

  useEffect(() => {
    const calc = () => {
      const w = window.innerWidth;
      setSize({
        isMobile: w < 640,
        isTablet: w >= 640 && w < 768,
        isLaptop: w >= 768 && w < 1024,
        isDesktop: w >= 1024,
      });
    };
    calc();
    window.addEventListener('resize', calc);
    return () => window.removeEventListener('resize', calc);
  }, []);

  return size;
};