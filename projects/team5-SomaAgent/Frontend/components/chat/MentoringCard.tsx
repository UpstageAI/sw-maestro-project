import {
  CalendarDays,
  CheckCircle2,
  Clock,
  Loader2,
  MapPin,
  Tag,
  UserRound,
  Users,
} from "lucide-react";
import { ActionButton } from "@/components/ui/ActionButton";
import { formatMentoringSchedule } from "@/lib/relativeTime";
import {
  type MentoringCard as MentoringCardType,
  getCapacityRatio,
  isCapacityFull,
} from "@/lib/types/mentoring";

export type MentoringCardLocalStatus =
  | "open"
  | "applied"
  | "closed"
  | "applying"
  | "cancelling";

type Props = {
  card: MentoringCardType;
  status: MentoringCardLocalStatus;
  onApply: (card: MentoringCardType) => void;
  onCancel: (card: MentoringCardType) => void;
};

type StatusBadgeStyle = {
  className: string;
  label: string;
};

const STATUS_BADGE: Record<MentoringCardLocalStatus, StatusBadgeStyle> = {
  open: {
    className: "bg-blue-50 text-blue-700",
    label: "신청 가능",
  },
  applied: {
    className: "bg-emerald-50 text-emerald-700",
    label: "신청 완료",
  },
  closed: {
    className: "bg-slate-100 text-slate-500",
    label: "마감",
  },
  applying: {
    className: "bg-blue-50 text-blue-700",
    label: "신청 처리 중",
  },
  cancelling: {
    className: "bg-amber-50 text-amber-700",
    label: "취소 처리 중",
  },
};

function CapacityBar({ card }: { card: MentoringCardType }) {
  if (!card.capacity) return null;
  const ratio = getCapacityRatio(card);
  const percent = Math.round(ratio * 100);
  const tone =
    ratio >= 1
      ? "bg-rose-500"
      : ratio >= 0.8
        ? "bg-amber-500"
        : "bg-emerald-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1">
          <Users className="h-3 w-3 text-slate-400" />
          {card.capacity.current}/{card.capacity.max}명
        </span>
        <span className="text-slate-400">{percent}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={card.capacity.current}
        aria-valuemax={card.capacity.max}
        aria-label="멘토링 정원"
        className="h-1 w-full overflow-hidden rounded-full bg-slate-100"
      >
        <div
          className={`h-full rounded-full transition-all ${tone}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function CardActions({
  card,
  status,
  onApply,
  onCancel,
}: Pick<Props, "card" | "status" | "onApply" | "onCancel">) {
  const isBusy = status === "applying" || status === "cancelling";
  const full = isCapacityFull(card);

  if (status === "applied" || status === "cancelling") {
    return (
      <ActionButton
        variant="ghost"
        disabled={isBusy}
        onClick={() => onCancel(card)}
        aria-label={`${card.title} 신청 취소하기`}
      >
        {status === "cancelling" ? (
          <span className="inline-flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" /> 취소 처리 중…
          </span>
        ) : (
          "신청 취소하기"
        )}
      </ActionButton>
    );
  }

  if (status === "closed") {
    return (
      <ActionButton variant="ghost" disabled>
        신청 마감
      </ActionButton>
    );
  }

  if (status === "open" && full) {
    return (
      <ActionButton variant="ghost" disabled>
        정원 마감
      </ActionButton>
    );
  }

  return (
    <ActionButton
      variant="primary"
      disabled={isBusy}
      onClick={() => onApply(card)}
      aria-label={`${card.title} 신청하기`}
    >
      {status === "applying" ? (
        <span className="inline-flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" /> 신청 처리 중…
        </span>
      ) : (
        "이 멘토링 신청하기"
      )}
    </ActionButton>
  );
}

export function MentoringCard({ card, status, onApply, onCancel }: Props) {
  const badge = STATUS_BADGE[status];

  return (
    <article className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-start justify-between gap-3">
        <h4 className="min-w-0 text-sm font-semibold text-slate-900">
          {card.title}
        </h4>
        <span
          className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${badge.className}`}
        >
          {status === "applied" && (
            <CheckCircle2 className="h-3 w-3" />
          )}
          {(status === "applying" || status === "cancelling") && (
            <Loader2 className="h-3 w-3 animate-spin" />
          )}
          {badge.label}
        </span>
      </header>

      {card.description && (
        <p className="line-clamp-2 text-xs text-slate-500">{card.description}</p>
      )}

      <dl className="space-y-1.5 text-xs text-slate-600">
        <div className="flex items-center gap-2">
          <UserRound className="h-3.5 w-3.5 text-slate-400" />
          <span className="font-medium text-slate-700">{card.mentor.name}</span>
          {card.mentor.organization && (
            <span className="text-slate-400">· {card.mentor.organization}</span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <CalendarDays className="h-3.5 w-3.5 text-slate-400" />
          <span>
            {formatMentoringSchedule(
              card.sessionStartedAt,
              card.sessionEndedAt,
            )}
          </span>
        </div>

        {card.location && (
          <div className="flex items-center gap-2">
            <MapPin className="h-3.5 w-3.5 text-slate-400" />
            <span>
              {card.location.type === "online"
                ? "온라인"
                : `오프라인 · ${card.location.place}`}
            </span>
          </div>
        )}

        {card.tags.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <Tag className="h-3.5 w-3.5 text-slate-400" />
            {card.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-md bg-blue-50 px-1.5 py-0.5 text-[11px] font-medium text-blue-600"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </dl>

      <CapacityBar card={card} />

      {status === "applied" && card.applySn && (
        <p className="text-[11px] text-emerald-700">
          접수번호 #{card.applySn} · 시작 30분 전 알림이 발송됩니다.
        </p>
      )}

      {status === "applying" && (
        <div
          className="flex items-center justify-center gap-2 text-xs text-blue-700"
          aria-live="polite"
          role="status"
        >
          <Clock className="h-3 w-3" /> 신청 결과가 곧 표시됩니다.
        </div>
      )}

      <CardActions
        card={card}
        status={status}
        onApply={onApply}
        onCancel={onCancel}
      />
    </article>
  );
}
