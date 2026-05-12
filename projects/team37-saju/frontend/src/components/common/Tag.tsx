import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface TagProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  selected?: boolean;
  children: ReactNode;
}

export default function Tag({
  selected = false,
  children,
  className = '',
  type = 'button',
  ...rest
}: TagProps) {
  return (
    <button
      {...rest}
      type={type}
      aria-pressed={selected}
      className={[
        'inline-flex items-center justify-center px-3.5 py-1.5 text-sm font-medium rounded-full',
        'border transition-all duration-150',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1',
        selected
          ? 'bg-primary text-white border-primary shadow-sm'
          : 'bg-white text-gray-700 border-gray-200 hover:border-primary-light hover:text-primary',
        className,
      ].join(' ')}
    >
      {children}
    </button>
  );
}
