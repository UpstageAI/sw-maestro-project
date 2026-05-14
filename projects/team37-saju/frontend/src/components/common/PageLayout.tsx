import type { ReactNode } from 'react';

interface PageLayoutProps {
  children: ReactNode;
  background?: 'mystic' | 'cream' | 'white';
  className?: string;
}

const backgroundClasses = {
  mystic: 'bg-mystic',
  cream: 'bg-cream',
  white: 'bg-white',
};

export default function PageLayout({
  children,
  background = 'mystic',
  className = '',
}: PageLayoutProps) {
  return (
    <div className={[`min-h-screen ${backgroundClasses[background]}`].join(' ')}>
      <div
        className={[
          'mx-auto w-full max-w-md px-5 py-6 min-h-screen flex flex-col',
          className,
        ].join(' ')}
      >
        {children}
      </div>
    </div>
  );
}
