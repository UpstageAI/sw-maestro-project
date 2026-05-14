type StepState = 'pending' | 'active' | 'done';

interface AgentStepCardProps {
  index: number;
  title: string;
  description: string;
  state: StepState;
}

export default function AgentStepCard({
  index,
  title,
  description,
  state,
}: AgentStepCardProps) {
  const isActive = state === 'active';
  const isDone = state === 'done';
  const isPending = state === 'pending';

  return (
    <div
      className={[
        'flex items-start gap-3 rounded-2xl border transition-all duration-300',
        'p-3.5',
        isActive
          ? 'bg-white border-primary shadow-soft scale-[1.01]'
          : isDone
            ? 'bg-white/70 border-cream-dark'
            : 'bg-white/40 border-transparent opacity-60',
      ].join(' ')}
      aria-current={isActive ? 'step' : undefined}
    >
      <div
        className={[
          'shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm',
          isActive
            ? 'bg-primary text-white shadow-soft'
            : isDone
              ? 'bg-cream-dark text-primary'
              : 'bg-gray-100 text-gray-400',
        ].join(' ')}
      >
        {isDone ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <span>{index}</span>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3
            className={[
              'text-sm font-semibold truncate',
              isActive
                ? 'text-primary'
                : isDone
                  ? 'text-gray-700'
                  : 'text-gray-400',
            ].join(' ')}
          >
            {title}
          </h3>
          {isActive && (
            <span
              className="inline-block w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin"
              aria-hidden="true"
            />
          )}
        </div>
        <p
          className={[
            'text-xs leading-relaxed mt-0.5',
            isActive
              ? 'text-gray-600'
              : isDone
                ? 'text-gray-500'
                : 'text-gray-400',
          ].join(' ')}
        >
          {description}
        </p>
      </div>

      {isPending && (
        <span className="shrink-0 text-xs text-gray-400 mt-1">대기</span>
      )}
    </div>
  );
}
