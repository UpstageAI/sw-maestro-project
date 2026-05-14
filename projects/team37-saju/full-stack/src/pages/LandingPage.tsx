import { useNavigate } from 'react-router-dom';
import { Button, PageLayout } from '../components/common';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <PageLayout background="mystic">
      <div className="relative flex-1 flex flex-col">
        <div
          className="absolute inset-0 pointer-events-none overflow-hidden"
          aria-hidden="true"
        >
          <span className="absolute top-[8%] left-[10%] text-2xl opacity-60 animate-pulse">✨</span>
          <span className="absolute top-[16%] right-[12%] text-xl opacity-50 animate-pulse [animation-delay:0.6s]">⭐</span>
          <span className="absolute top-[30%] left-[6%] text-lg opacity-40 animate-pulse [animation-delay:1.2s]">✨</span>
          <span className="absolute bottom-[25%] right-[8%] text-2xl opacity-50 animate-pulse [animation-delay:0.3s]">⭐</span>
          <span className="absolute bottom-[18%] left-[14%] text-xl opacity-40 animate-pulse [animation-delay:0.9s]">✨</span>
        </div>

        <main className="relative flex-1 flex flex-col items-center justify-center text-center px-2">
          <div className="mb-2 text-6xl drop-shadow-sm" aria-hidden="true">
            <span className="inline-block">🌙</span>
            <span className="inline-block ml-2 animate-pulse">✨</span>
          </div>

          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-gradient-primary">
            AI 사주 여행
          </h1>

          <p className="mt-5 text-base text-gray-700 leading-relaxed max-w-xs">
            지금 나에게 어울리는
            <br />
            국내 여행지를 사주로 찾아드립니다
          </p>

          <div
            className="mt-10 flex items-center justify-center gap-3 text-3xl opacity-80"
            aria-hidden="true"
          >
            <span>⛰️</span>
            <span>🌊</span>
            <span>🌸</span>
            <span>🏯</span>
          </div>
        </main>

        <footer className="relative pb-2 pt-6">
          <Button
            variant="primary"
            size="lg"
            fullWidth
            onClick={() => navigate('/input')}
          >
            내 여행지 추천 받기
          </Button>
          <p className="mt-4 text-center text-xs text-gray-500">
            본 서비스는 재미와 참고용입니다
          </p>
        </footer>
      </div>
    </PageLayout>
  );
}
