import { useNavigate } from 'react-router-dom';
import type { ReactNode } from 'react';

interface HeaderProps {
  title: string;
  showBack?: boolean;
  onBack?: () => void;
  right?: ReactNode;
}

export default function Header({
  title,
  showBack = true,
  onBack,
  right,
}: HeaderProps) {
  const navigate = useNavigate();

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate(-1);
    }
  };

  return (
    <header className="flex items-center justify-between h-12 mb-2">
      <div className="w-10 flex items-center justify-start">
        {showBack && (
          <button
            type="button"
            onClick={handleBack}
            aria-label="뒤로가기"
            className="w-10 h-10 flex items-center justify-center rounded-full text-primary hover:bg-cream-dark transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
        )}
      </div>

      <h1 className="flex-1 text-center text-lg font-bold text-gray-900 truncate">
        {title}
      </h1>

      <div className="w-10 flex items-center justify-end">{right}</div>
    </header>
  );
}
