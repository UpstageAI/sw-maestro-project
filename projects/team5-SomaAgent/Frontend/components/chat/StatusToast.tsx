import { CheckCircle2 } from "lucide-react";

type Props = {
  text: string;
  detail: string;
};

export function StatusToast({ text, detail }: Props) {
  return (
    <div className="mx-auto flex max-w-lg items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50/80 px-4 py-3 text-sm text-emerald-800">
      <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
      <div>
        <p className="font-semibold">{text}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-emerald-800/80">
          {detail}
        </p>
      </div>
    </div>
  );
}
