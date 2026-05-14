export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-2 px-5 py-8 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <p>© {new Date().getFullYear()} 사장님메이트 (bossmate) · SOMA 17기 AI 17조 데모</p>
        <p className="font-mono uppercase tracking-widest">
          mock image · solar fallback ready
        </p>
      </div>
    </footer>
  );
}
