// Daily Report — 3 design variations
// A. Newspaper · B. Briefing Card · C. Timeline

const NEWS = {
  date: { full: "5월 10일 화요일", short: "5월 10일", iso: "2026-05-10", weekday: "TUE" },
  briefing:
    "AI 자동화와 통상 압박, 인구 위기가 동시에 부상한 하루였습니다.",
  flow: [
    { cat: "테크", color: "#ff8a3d", line: "AI 에이전트 경쟁이 업무 자동화 시장으로 본격 확산" },
    { cat: "경제", color: "#2cb67d", line: "미국 관세 여파로 반도체·자동차 수출 기업 부담 가중" },
    { cat: "이슈", color: "#7c5cff", line: "합계출산율 역대 최저, 정부 전담 부처 신설로 대응" },
  ],
  headline: {
    cat: "테크",
    color: "#ff8a3d",
    time: "09:20",
    sources: 4,
    title: "오픈AI·앤트로픽, AI 에이전트 경쟁 본격화... 작업 자동화 시대 가시화",
    lede: "이메일 작성, 코드 실행, 파일 관리 등 실제 작업을 AI가 직접 처리하는 서비스가 빠르게 확산되고 있어요.",
    keywords: ["AI 에이전트", "오픈AI", "자동화"],
  },
  subs: [
    { cat: "경제", color: "#2cb67d", time: "08:45", sources: 3, title: "미국 관세 인상 여파... 반도체·자동차 수출 기업 부담 가중" },
    { cat: "이슈", color: "#7c5cff", time: "08:10", sources: 2, title: "합계출산율 0.75명 역대 최저... 인구전략기획부 신설 추진" },
  ],
  keywords: [
    { w: "AI 에이전트", n: 9 },
    { w: "미국 관세", n: 7 },
    { w: "오픈AI", n: 6 },
    { w: "출산율", n: 5 },
    { w: "자동화", n: 4 },
    { w: "수출", n: 3 },
    { w: "저출생", n: 3 },
    { w: "반도체", n: 2 },
  ],
};

// ─────────────────────────────────────────────────────────────
// Shared chrome — phone shell with status bar + bottom nav
// ─────────────────────────────────────────────────────────────
const phoneShell = {
  width: 390, height: 820, borderRadius: 32, background: "#ffffff",
  boxShadow: "0 18px 50px rgba(25,31,40,0.12)",
  overflow: "hidden", display: "flex", flexDirection: "column",
  fontFamily: 'Pretendard, Inter, ui-sans-serif, system-ui, "Segoe UI", sans-serif',
  color: "#191f28",
};
const statusBarStyle = {
  display: "flex", justifyContent: "space-between", alignItems: "center",
  minHeight: 48, padding: "14px 24px 0", color: "#191f28",
  fontSize: 13, fontWeight: 700,
};
const bottomNavStyle = {
  display: "grid", gridTemplateColumns: "1fr 1fr",
  borderTop: "1px solid #e5e8eb", background: "#fff",
  height: 60, flexShrink: 0,
};
const navItemBase = {
  display: "grid", placeItems: "center", gap: 4,
  fontSize: 11, fontWeight: 700, color: "#8b95a1",
};

function StatusBar() {
  return (
    <div style={statusBarStyle}>
      <span>9:41</span>
      <span style={{ fontSize: 12 }}>5G 100%</span>
    </div>
  );
}

function BottomNav({ activeColor = "#ff8a3d" }) {
  return (
    <nav style={bottomNavStyle} aria-label="bottom nav">
      <div style={{ ...navItemBase }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M4 10.5 12 4l8 6.5"/><path d="M6.5 10v9h11v-9"/><path d="M10 19v-5h4v5"/>
        </svg>
        홈
      </div>
      <div style={{ ...navItemBase, color: activeColor }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
          <rect x="6" y="4" width="12" height="16" rx="3"/><path d="M9 9h6"/><path d="M9 13h6"/><path d="M9 17h4"/>
        </svg>
        리포트
      </div>
    </nav>
  );
}

// ─────────────────────────────────────────────────────────────
// VARIANT A — Newspaper
// ─────────────────────────────────────────────────────────────
const variantAStyles = {
  scroll: { flex: 1, overflowY: "auto", padding: "20px 22px 30px",
    fontFamily: 'Pretendard, "Noto Serif KR", system-ui, sans-serif' },
  masthead: {
    display: "flex", justifyContent: "space-between", alignItems: "baseline",
    paddingBottom: 10, borderBottom: "2px solid #191f28",
    fontSize: 11, fontWeight: 800, letterSpacing: "0.18em",
    color: "#191f28", textTransform: "uppercase",
  },
  titleRow: {
    display: "flex", justifyContent: "space-between", alignItems: "flex-end",
    marginTop: 14, marginBottom: 8,
  },
  pageTitle: {
    margin: 0, fontFamily: '"Noto Serif KR", "Times New Roman", Georgia, serif',
    fontSize: 32, fontWeight: 900, lineHeight: 1.1, letterSpacing: "-0.01em",
  },
  vol: { fontSize: 10, fontWeight: 700, letterSpacing: "0.16em", color: "#8b95a1" },
  pull: {
    margin: "16px 0 18px", padding: "14px 18px",
    borderTop: "1px solid #191f28", borderBottom: "1px solid #191f28",
    fontFamily: '"Noto Serif KR", Georgia, serif',
    fontSize: 17, lineHeight: 1.55, fontWeight: 600, fontStyle: "italic",
    color: "#191f28", letterSpacing: "-0.005em",
  },
  pullLabel: {
    display: "inline-block", marginRight: 8, padding: "2px 7px",
    background: "#191f28", color: "#fff", fontSize: 9, fontWeight: 800,
    letterSpacing: "0.14em", verticalAlign: "middle", borderRadius: 2,
    fontStyle: "normal", fontFamily: "Pretendard, sans-serif",
  },
  topStory: { paddingBottom: 16, borderBottom: "1px solid #d1d6db" },
  rank: { fontSize: 11, fontWeight: 900, letterSpacing: "0.18em", color: "#ff8a3d" },
  headlineH: {
    margin: "8px 0 8px",
    fontFamily: '"Noto Serif KR", Georgia, serif',
    fontSize: 22, fontWeight: 900, lineHeight: 1.25, color: "#191f28",
    wordBreak: "keep-all",
  },
  catChip: (c) => ({
    display: "inline-block", padding: "2px 8px", marginRight: 6,
    background: c, color: "#fff", fontSize: 10, fontWeight: 800,
    letterSpacing: "0.06em",
  }),
  dotsRow: { display: "flex", alignItems: "center", gap: 6, marginTop: 10,
    fontSize: 11, fontWeight: 700, color: "#6b7684" },
  dot: { width: 6, height: 6, borderRadius: 999, background: "#ff8a3d" },
  lede: { margin: 0, fontSize: 13, lineHeight: 1.6, color: "#404953", fontWeight: 500,
    wordBreak: "keep-all" },
  belowFold: { display: "grid", gap: 0, marginTop: 4 },
  subItem: {
    display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 10,
    padding: "14px 0", borderBottom: "1px solid #e5e8eb", alignItems: "start",
  },
  subRank: { fontFamily: '"Noto Serif KR", Georgia, serif', fontSize: 24, fontWeight: 900,
    color: "#d1d6db", lineHeight: 1, paddingTop: 2 },
  subTitle: { margin: "0 0 4px", fontSize: 14, lineHeight: 1.4, fontWeight: 800,
    color: "#191f28", wordBreak: "keep-all" },
  subMeta: { fontSize: 11, color: "#8b95a1", fontWeight: 700 },
  flowSection: { marginTop: 22 },
  flowHead: { display: "flex", alignItems: "center", gap: 8, marginBottom: 12 },
  flowHeadLine: { flex: 1, height: 1, background: "#191f28" },
  flowHeadLabel: { fontSize: 11, fontWeight: 900, letterSpacing: "0.18em" },
  flowGrid: { display: "grid", gap: 10 },
  flowRow: { display: "grid", gridTemplateColumns: "auto auto 1fr", gap: 10,
    alignItems: "baseline", paddingBottom: 8, borderBottom: "1px dashed #e5e8eb" },
  flowCat: { fontSize: 10, fontWeight: 900, letterSpacing: "0.1em" },
  flowText: { fontSize: 13, lineHeight: 1.45, color: "#191f28", fontWeight: 600,
    wordBreak: "keep-all" },
  kwSection: { marginTop: 22 },
  kwLine: { display: "flex", flexWrap: "wrap", gap: "6px 10px",
    fontFamily: '"Noto Serif KR", Georgia, serif', lineHeight: 1.3 },
};

function VariantA() {
  const s = variantAStyles;
  return (
    <div style={phoneShell}>
      <StatusBar />
      <div style={s.scroll}>
        <div style={s.masthead}>
          <span>NewPick · Daily</span>
          <span>{NEWS.date.weekday} · {NEWS.date.short}</span>
        </div>

        <div style={s.titleRow}>
          <h1 style={s.pageTitle}>오늘의 브리핑</h1>
          <span style={s.vol}>VOL.131</span>
        </div>

        <div style={s.pull}>
          <span style={s.pullLabel}>AI BRIEFING</span>
          {NEWS.briefing}
        </div>

        <section style={s.topStory}>
          <span style={s.rank}>#1 TOP STORY</span>
          <h2 style={s.headlineH}>
            <span style={s.catChip(NEWS.headline.color)}>{NEWS.headline.cat}</span>
            {NEWS.headline.title}
          </h2>
          <p style={s.lede}>{NEWS.headline.lede}</p>
          <div style={s.dotsRow}>
            {Array.from({length: NEWS.headline.sources}).map((_, i) => (
              <span key={i} style={s.dot}/>
            ))}
            <span>{NEWS.headline.sources}개 매체가 동시에 다룬 이슈</span>
            <span style={{ marginLeft: "auto" }}>{NEWS.headline.time}</span>
          </div>
        </section>

        <div style={s.belowFold}>
          {NEWS.subs.map((it, i) => (
            <div key={i} style={s.subItem}>
              <span style={s.subRank}>#{i+2}</span>
              <div>
                <h3 style={s.subTitle}>
                  <span style={{ ...s.catChip(it.color), marginRight: 6 }}>{it.cat}</span>
                  {it.title}
                </h3>
                <span style={s.subMeta}>{it.sources}개 매체 · {it.time}</span>
              </div>
            </div>
          ))}
        </div>

        <section style={s.flowSection}>
          <div style={s.flowHead}>
            <span style={s.flowHeadLabel}>오늘의 흐름</span>
            <span style={s.flowHeadLine}/>
          </div>
          <div style={s.flowGrid}>
            {NEWS.flow.map((f, i) => (
              <div key={i} style={s.flowRow}>
                <span style={{ ...s.flowCat, color: f.color }}>{f.cat.toUpperCase()}</span>
                <span style={{ width: 1, height: 12, background: "#d1d6db" }}/>
                <span style={s.flowText}>{f.line}</span>
              </div>
            ))}
          </div>
        </section>

        <section style={s.kwSection}>
          <div style={s.flowHead}>
            <span style={s.flowHeadLabel}>오늘의 키워드</span>
            <span style={s.flowHeadLine}/>
          </div>
          <div style={s.kwLine}>
            {NEWS.keywords.map((k, i) => {
              const size = 12 + Math.min(k.n, 9) * 1.4;
              const weight = k.n >= 6 ? 900 : k.n >= 4 ? 700 : 500;
              return <span key={i} style={{
                fontSize: size, fontWeight: weight,
                color: k.n >= 6 ? "#191f28" : "#6b7684",
              }}>{k.w}</span>;
            })}
          </div>
        </section>
      </div>
      <BottomNav activeColor="#191f28"/>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// VARIANT B — Briefing Card (hero + 마무리 카드)
// ─────────────────────────────────────────────────────────────
const variantBStyles = {
  scroll: { flex: 1, overflowY: "auto", padding: "16px 18px 30px" },
  hero: {
    position: "relative", padding: "22px 22px 24px", borderRadius: 24,
    background: "linear-gradient(160deg, #fff5ec 0%, #ffe4d0 60%, #ffd4b3 100%)",
    overflow: "hidden",
  },
  heroDateRow: { display: "flex", justifyContent: "space-between",
    alignItems: "center", marginBottom: 14 },
  heroDate: { fontSize: 13, fontWeight: 800, color: "#cc6a26",
    letterSpacing: "-0.005em" },
  readChip: { display: "inline-flex", alignItems: "center", gap: 5,
    padding: "5px 10px", borderRadius: 999,
    background: "rgba(255,255,255,0.7)", color: "#cc6a26",
    fontSize: 11, fontWeight: 800 },
  heroTitle: { margin: "0 0 14px", fontSize: 26, fontWeight: 900,
    lineHeight: 1.2, color: "#3a1f0e", wordBreak: "keep-all" },
  heroBriefingLabel: { fontSize: 10, fontWeight: 900, letterSpacing: "0.16em",
    color: "#cc6a26", marginBottom: 6 },
  heroBriefing: { margin: 0, fontSize: 16, lineHeight: 1.6, fontWeight: 700,
    color: "#3a1f0e", wordBreak: "keep-all" },

  sectionLabel: { fontSize: 13, fontWeight: 900, color: "#ff8a3d",
    margin: "26px 4px 12px", letterSpacing: "-0.005em" },

  headCard: {
    padding: 18, borderRadius: 22, background: "#fff",
    border: "1px solid #e5e8eb",
    boxShadow: "0 12px 28px rgba(25,31,40,0.06)",
  },
  headTopRow: { display: "flex", alignItems: "center", gap: 8, marginBottom: 12,
    fontSize: 11, fontWeight: 800, color: "#8b95a1" },
  catPill: (c) => ({
    display: "inline-flex", alignItems: "center", padding: "4px 10px",
    borderRadius: 999, background: `${c}1a`, color: c,
    fontSize: 11, fontWeight: 800,
  }),
  sourceBadge: {
    display: "inline-flex", alignItems: "center", gap: 5,
    padding: "4px 9px", borderRadius: 999, background: "#191f28",
    color: "#fff", fontSize: 10, fontWeight: 800,
  },
  headTitle: { margin: "0 0 8px", fontSize: 19, fontWeight: 900, lineHeight: 1.32,
    color: "#191f28", wordBreak: "keep-all" },
  headLede: { margin: 0, fontSize: 13, lineHeight: 1.55, color: "#6b7684",
    fontWeight: 600, wordBreak: "keep-all" },
  headKw: { display: "flex", flexWrap: "wrap", gap: 6, marginTop: 12 },
  kwChip: { display: "inline-flex", padding: "4px 9px", borderRadius: 999,
    background: "#f2f4f6", color: "#6b7684", fontSize: 11, fontWeight: 700 },

  subList: { display: "grid", gap: 10 },
  subRow: {
    display: "grid", gridTemplateColumns: "28px 1fr auto", gap: 12,
    alignItems: "center", padding: "12px 14px",
    background: "#fff", border: "1px solid #e5e8eb", borderRadius: 16,
  },
  subRank: { fontSize: 16, fontWeight: 900, color: "#d1d6db",
    fontFamily: '"Noto Serif KR", Georgia, serif', lineHeight: 1 },
  subTitle: { fontSize: 13.5, lineHeight: 1.4, fontWeight: 800,
    color: "#191f28", wordBreak: "keep-all" },
  subMeta: { fontSize: 10, fontWeight: 700, color: "#8b95a1", marginTop: 4 },

  flowGrid: { display: "grid", gap: 10 },
  flowCard: {
    display: "grid", gridTemplateColumns: "8px 1fr", gap: 12, alignItems: "center",
    padding: "14px 16px", background: "#fff",
    border: "1px solid #e5e8eb", borderRadius: 16,
  },
  flowBar: (c) => ({ width: 4, height: "100%", minHeight: 36, borderRadius: 4,
    background: c }),
  flowCatLabel: (c) => ({ display: "inline-block", fontSize: 11, fontWeight: 900,
    color: c, letterSpacing: "-0.005em", marginBottom: 3 }),
  flowText: { fontSize: 13.5, lineHeight: 1.45, fontWeight: 700,
    color: "#191f28", wordBreak: "keep-all" },

  kwCloud: { display: "flex", flexWrap: "wrap", gap: 6,
    padding: 16, background: "#fafbfc", borderRadius: 16 },

  finishCard: {
    marginTop: 22, padding: 18, borderRadius: 20,
    background: "linear-gradient(135deg, #191f28 0%, #2c3540 100%)",
    color: "#fff",
    display: "grid", gridTemplateColumns: "auto 1fr", gap: 14, alignItems: "center",
  },
  finishCheck: {
    width: 38, height: 38, borderRadius: 999,
    background: "#ff8a3d", color: "#fff",
    display: "grid", placeItems: "center", fontSize: 18, fontWeight: 900,
  },
  finishTitle: { fontSize: 14, fontWeight: 900, marginBottom: 3 },
  finishSub: { fontSize: 11.5, color: "#aab2c0", fontWeight: 600,
    lineHeight: 1.4 },
};

function VariantB() {
  const s = variantBStyles;
  return (
    <div style={phoneShell}>
      <StatusBar />
      <div style={s.scroll}>
        <div style={s.hero}>
          <div style={s.heroDateRow}>
            <span style={s.heroDate}>{NEWS.date.full}</span>
            <span style={s.readChip}>⏱ 5분이면 끝</span>
          </div>
          <h1 style={s.heroTitle}>오늘 다 따라잡기</h1>
          <div style={s.heroBriefingLabel}>AI 브리핑</div>
          <p style={s.heroBriefing}>{NEWS.briefing}</p>
        </div>

        <div style={s.sectionLabel}>오늘의 헤드라인</div>
        <div style={s.headCard}>
          <div style={s.headTopRow}>
            <span style={s.catPill(NEWS.headline.color)}>{NEWS.headline.cat}</span>
            <span style={s.sourceBadge}>● {NEWS.headline.sources}개 매체 동시 보도</span>
            <span style={{ marginLeft: "auto" }}>{NEWS.headline.time}</span>
          </div>
          <h3 style={s.headTitle}>{NEWS.headline.title}</h3>
          <p style={s.headLede}>{NEWS.headline.lede}</p>
          <div style={s.headKw}>
            {NEWS.headline.keywords.map((k, i) => (
              <span key={i} style={s.kwChip}>#{k}</span>
            ))}
          </div>
        </div>

        <div style={s.sectionLabel}>주요 이슈</div>
        <div style={s.subList}>
          {NEWS.subs.map((it, i) => (
            <div key={i} style={s.subRow}>
              <span style={s.subRank}>#{i+2}</span>
              <div>
                <div style={s.subTitle}>{it.title}</div>
                <div style={s.subMeta}>
                  <span style={{ color: it.color, fontWeight: 800 }}>● {it.cat}</span>
                  &nbsp;·&nbsp;{it.sources}개 매체&nbsp;·&nbsp;{it.time}
                </div>
              </div>
              <span style={{ color: "#c5cbd3", fontWeight: 800 }}>›</span>
            </div>
          ))}
        </div>

        <div style={s.sectionLabel}>오늘의 흐름</div>
        <div style={s.flowGrid}>
          {NEWS.flow.map((f, i) => (
            <div key={i} style={s.flowCard}>
              <div style={s.flowBar(f.color)}/>
              <div>
                <div style={s.flowCatLabel(f.color)}>{f.cat}</div>
                <div style={s.flowText}>{f.line}</div>
              </div>
            </div>
          ))}
        </div>

        <div style={s.sectionLabel}>오늘의 키워드</div>
        <div style={s.kwCloud}>
          {NEWS.keywords.map((k, i) => {
            const big = k.n >= 6;
            return <span key={i} style={{
              padding: "5px 11px", borderRadius: 999,
              background: big ? "#ff8a3d" : "#fff",
              color: big ? "#fff" : "#6b7684",
              fontSize: big ? 13 : 11.5,
              fontWeight: big ? 900 : 700,
              border: big ? "none" : "1px solid #e5e8eb",
            }}>#{k.w}</span>;
          })}
        </div>

        <div style={s.finishCard}>
          <div style={s.finishCheck}>✓</div>
          <div>
            <div style={s.finishTitle}>오늘 정리 완료!</div>
            <div style={s.finishSub}>3개 이슈 · 9개 키워드를 5분만에 따라잡았어요. 내일도 같은 시간에 만나요.</div>
          </div>
        </div>
      </div>
      <BottomNav />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// VARIANT C — Timeline
// ─────────────────────────────────────────────────────────────
const variantCStyles = {
  scroll: { flex: 1, overflowY: "auto", padding: "20px 22px 30px",
    background: "linear-gradient(180deg, #fffaf5 0%, #ffffff 280px)" },
  topRow: { display: "flex", alignItems: "baseline", justifyContent: "space-between",
    marginBottom: 4 },
  dateBig: { margin: 0, fontSize: 30, fontWeight: 900, lineHeight: 1.05,
    letterSpacing: "-0.02em", color: "#191f28" },
  dateSmall: { fontSize: 11, fontWeight: 800, color: "#8b95a1",
    letterSpacing: "0.06em" },
  dayLabel: { fontSize: 13, fontWeight: 700, color: "#6b7684",
    marginBottom: 18 },

  briefingCard: {
    padding: "14px 16px", borderRadius: 16,
    background: "#fff", border: "1px solid #ffe2cf",
    boxShadow: "0 6px 18px rgba(255,138,61,0.10)",
    marginBottom: 22,
    display: "grid", gridTemplateColumns: "auto 1fr", gap: 12, alignItems: "center",
  },
  briefingIcon: {
    width: 32, height: 32, borderRadius: 10, background: "#ff8a3d", color: "#fff",
    display: "grid", placeItems: "center", fontSize: 13, fontWeight: 900,
  },
  briefingLabel: { fontSize: 10, fontWeight: 900, color: "#cc6a26",
    letterSpacing: "0.16em", marginBottom: 2 },
  briefingText: { fontSize: 13.5, lineHeight: 1.45, fontWeight: 700,
    color: "#191f28", wordBreak: "keep-all" },

  timelineHead: { display: "flex", alignItems: "center", gap: 8,
    marginBottom: 14, fontSize: 12, fontWeight: 900, color: "#191f28",
    letterSpacing: "-0.005em" },
  timelineLabel: { textTransform: "none" },
  timelineCount: { fontSize: 11, fontWeight: 700, color: "#8b95a1" },

  timeline: { position: "relative", paddingLeft: 30 },
  rail: { position: "absolute", left: 11, top: 8, bottom: 8,
    width: 2, background: "linear-gradient(180deg, #ff8a3d 0%, #2cb67d 50%, #7c5cff 100%)",
    borderRadius: 2, opacity: 0.5 },
  node: (c, big) => ({
    position: "absolute", left: big ? 1 : 5, top: big ? 8 : 12,
    width: big ? 22 : 14, height: big ? 22 : 14, borderRadius: 999,
    background: "#fff", border: `${big ? 4 : 3}px solid ${c}`,
    boxShadow: big ? `0 0 0 6px ${c}22` : "none",
    zIndex: 2,
  }),
  tlItem: { position: "relative", marginBottom: 18 },
  tlTime: { display: "block", fontSize: 11, fontWeight: 800, color: "#8b95a1",
    marginBottom: 6 },
  tlBig: {
    padding: 16, borderRadius: 18, background: "#fff",
    border: "1px solid #e5e8eb",
    boxShadow: "0 8px 22px rgba(25,31,40,0.06)",
  },
  tlBigCat: (c) => ({ fontSize: 10, fontWeight: 900, letterSpacing: "0.1em",
    color: c, marginBottom: 6 }),
  tlBigTitle: { margin: "0 0 8px", fontSize: 17, fontWeight: 900, lineHeight: 1.3,
    color: "#191f28", wordBreak: "keep-all" },
  tlBigLede: { margin: "0 0 10px", fontSize: 12.5, lineHeight: 1.5,
    color: "#6b7684", fontWeight: 600, wordBreak: "keep-all" },
  sourceTag: {
    display: "inline-flex", alignItems: "center", gap: 5,
    fontSize: 10, fontWeight: 800, color: "#191f28",
  },
  sourceTagDots: { display: "inline-flex", gap: 2 },
  tlSmall: {
    padding: "10px 14px", borderRadius: 14, background: "#fafbfc",
    border: "1px solid #e5e8eb",
  },
  tlSmallCat: (c) => ({ fontSize: 10, fontWeight: 900, color: c,
    marginBottom: 3, letterSpacing: "0.05em" }),
  tlSmallTitle: { fontSize: 13, fontWeight: 800, lineHeight: 1.4,
    color: "#191f28", wordBreak: "keep-all" },
  tlSmallMeta: { fontSize: 10, color: "#8b95a1", marginTop: 5, fontWeight: 700 },

  kwTitle: { fontSize: 12, fontWeight: 900, color: "#191f28",
    marginTop: 24, marginBottom: 12 },
  kwCloud: { display: "flex", flexWrap: "wrap", gap: "6px 10px",
    alignItems: "baseline" },
};

function VariantC() {
  const s = variantCStyles;
  return (
    <div style={phoneShell}>
      <StatusBar />
      <div style={s.scroll}>
        <div style={s.topRow}>
          <h1 style={s.dateBig}>5월 10일</h1>
          <span style={s.dateSmall}>09:30 업데이트</span>
        </div>
        <div style={s.dayLabel}>화요일 · 오늘의 흐름</div>

        <div style={s.briefingCard}>
          <div style={s.briefingIcon}>AI</div>
          <div>
            <div style={s.briefingLabel}>BRIEFING</div>
            <div style={s.briefingText}>{NEWS.briefing}</div>
          </div>
        </div>

        <div style={s.timelineHead}>
          <span style={s.timelineLabel}>오늘 일어난 일</span>
          <span style={{ flex: 1, height: 1, background: "#e5e8eb" }}/>
          <span style={s.timelineCount}>3건</span>
        </div>

        <div style={s.timeline}>
          <div style={s.rail}/>

          {/* Headline node */}
          <div style={s.tlItem}>
            <div style={s.node(NEWS.headline.color, true)}/>
            <span style={s.tlTime}>오늘 {NEWS.headline.time} · 가장 많이 다뤄진 이슈</span>
            <div style={s.tlBig}>
              <div style={s.tlBigCat(NEWS.headline.color)}>● {NEWS.headline.cat.toUpperCase()}</div>
              <h3 style={s.tlBigTitle}>{NEWS.headline.title}</h3>
              <p style={s.tlBigLede}>{NEWS.headline.lede}</p>
              <span style={s.sourceTag}>
                <span style={s.sourceTagDots}>
                  {Array.from({length: NEWS.headline.sources}).map((_, i) => (
                    <span key={i} style={{ width: 5, height: 5, borderRadius: 999,
                      background: NEWS.headline.color }}/>
                  ))}
                </span>
                {NEWS.headline.sources}개 매체가 동시에 보도
              </span>
            </div>
          </div>

          {NEWS.subs.map((it, i) => (
            <div key={i} style={s.tlItem}>
              <div style={s.node(it.color, false)}/>
              <span style={s.tlTime}>오늘 {it.time}</span>
              <div style={s.tlSmall}>
                <div style={s.tlSmallCat(it.color)}>● {it.cat.toUpperCase()}</div>
                <div style={s.tlSmallTitle}>{it.title}</div>
                <div style={s.tlSmallMeta}>{it.sources}개 매체 보도</div>
              </div>
            </div>
          ))}
        </div>

        <div style={s.kwTitle}>오늘의 키워드</div>
        <div style={s.kwCloud}>
          {NEWS.keywords.map((k, i) => {
            const size = 12 + Math.min(k.n, 9) * 1.2;
            const op = 0.5 + Math.min(k.n, 9) * 0.05;
            return <span key={i} style={{
              fontSize: size,
              fontWeight: k.n >= 6 ? 900 : k.n >= 4 ? 800 : 600,
              color: `rgba(25,31,40,${op})`,
              letterSpacing: "-0.01em",
            }}>{k.w}</span>;
          })}
        </div>
      </div>
      <BottomNav />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// VARIANT C+ — Timeline 보강형
//   = C 베이스 + 카테고리별 흐름 섹션 + 미니멀 마침표
// ─────────────────────────────────────────────────────────────
const variantCPStyles = {
  ...variantCStyles,
  scroll: { flex: 1, overflowY: "auto", padding: "20px 22px 26px",
    background: "#ffffff" },
  // 흐름 섹션 — timeline과 별도, 카테고리 정리용
  flowHead: { display: "flex", alignItems: "center", gap: 8,
    marginTop: 26, marginBottom: 12, fontSize: 12, fontWeight: 900,
    color: "#191f28" },
  flowList: { display: "grid", gap: 0,
    borderTop: "1px solid #e5e8eb" },
  flowRow: {
    display: "grid", gridTemplateColumns: "auto 1fr",
    gap: 12, alignItems: "baseline",
    padding: "12px 0", borderBottom: "1px solid #e5e8eb",
  },
  flowRowCat: (c) => ({
    fontSize: 11, fontWeight: 900, color: c,
    letterSpacing: "0.05em", minWidth: 28,
  }),
  flowRowText: { fontSize: 13.5, lineHeight: 1.45, fontWeight: 600,
    color: "#191f28", wordBreak: "keep-all" },
  // 마침표 — 미니멀
  footerMark: {
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
    marginTop: 28, paddingTop: 18,
    borderTop: "1px dashed #d1d6db",
    fontSize: 12, fontWeight: 700, color: "#8b95a1",
  },
  footerCheck: {
    width: 18, height: 18, borderRadius: 999,
    background: "#ff8a3d", color: "#fff",
    display: "grid", placeItems: "center",
    fontSize: 11, fontWeight: 900,
  },
};

function VariantCPlus() {
  const s = variantCPStyles;
  return (
    <div style={phoneShell}>
      <StatusBar />
      <div style={s.scroll}>
        <div style={s.topRow}>
          <h1 style={s.dateBig}>5월 10일</h1>
          <span style={s.dateSmall}>09:30 업데이트</span>
        </div>
        <div style={s.dayLabel}>화요일 · 데일리 리포트</div>

        <div style={s.briefingCard}>
          <div style={s.briefingIcon}>AI</div>
          <div>
            <div style={s.briefingLabel}>BRIEFING</div>
            <div style={s.briefingText}>{NEWS.briefing}</div>
          </div>
        </div>

        <div style={s.timelineHead}>
          <span style={s.timelineLabel}>가장 많이 다뤄진 순</span>
          <span style={{ flex: 1, height: 1, background: "#e5e8eb" }}/>
          <span style={s.timelineCount}>3건</span>
        </div>

        <div style={s.timeline}>
          <div style={s.rail}/>

          <div style={s.tlItem}>
            <div style={s.node(NEWS.headline.color, true)}/>
            <span style={s.tlTime}>오늘 {NEWS.headline.time} · 가장 많이 다뤄진 이슈</span>
            <div style={s.tlBig}>
              <div style={s.tlBigCat(NEWS.headline.color)}>● {NEWS.headline.cat.toUpperCase()}</div>
              <h3 style={s.tlBigTitle}>{NEWS.headline.title}</h3>
              <p style={s.tlBigLede}>{NEWS.headline.lede}</p>
              <span style={s.sourceTag}>
                <span style={s.sourceTagDots}>
                  {Array.from({length: NEWS.headline.sources}).map((_, i) => (
                    <span key={i} style={{ width: 5, height: 5, borderRadius: 999,
                      background: NEWS.headline.color }}/>
                  ))}
                </span>
                {NEWS.headline.sources}개 매체가 동시에 보도
              </span>
            </div>
          </div>

          {NEWS.subs.map((it, i) => (
            <div key={i} style={s.tlItem}>
              <div style={s.node(it.color, false)}/>
              <span style={s.tlTime}>오늘 {it.time}</span>
              <div style={s.tlSmall}>
                <div style={s.tlSmallCat(it.color)}>● {it.cat.toUpperCase()}</div>
                <div style={s.tlSmallTitle}>{it.title}</div>
                <div style={s.tlSmallMeta}>{it.sources}개 매체 보도</div>
              </div>
            </div>
          ))}
        </div>

        {/* 추가 — 카테고리별 흐름 정리 */}
        <div style={s.flowHead}>
          <span>오늘의 흐름</span>
          <span style={{ flex: 1, height: 1, background: "#e5e8eb" }}/>
          <span style={{ fontSize: 11, fontWeight: 700, color: "#8b95a1" }}>카테고리별 한 줄</span>
        </div>
        <div style={s.flowList}>
          {NEWS.flow.map((f, i) => (
            <div key={i} style={s.flowRow}>
              <span style={s.flowRowCat(f.color)}>{f.cat}</span>
              <span style={s.flowRowText}>{f.line}</span>
            </div>
          ))}
        </div>

        <div style={s.kwTitle}>오늘의 키워드</div>
        <div style={s.kwCloud}>
          {NEWS.keywords.map((k, i) => {
            const size = 12 + Math.min(k.n, 9) * 1.2;
            const op = 0.5 + Math.min(k.n, 9) * 0.05;
            return <span key={i} style={{
              fontSize: size,
              fontWeight: k.n >= 6 ? 900 : k.n >= 4 ? 800 : 600,
              color: `rgba(25,31,40,${op})`,
              letterSpacing: "-0.01em",
            }}>{k.w}</span>;
          })}
        </div>

        {/* 미니멀 마침표 */}
        <div style={s.footerMark}>
          <span style={s.footerCheck}>✓</span>
          <span>오늘 따라잡기 끝 — 내일 09:30에 다시 만나요</span>
        </div>
      </div>
      <BottomNav />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Mount via design canvas
// ─────────────────────────────────────────────────────────────
function App() {
  return (
    <DesignCanvas
      title="데일리 리포트 — 변형 비교"
      subtitle="A. 신문 톤  ·  B. 브리핑 카드  ·  C. 타임라인"
    >
      <DCSection id="report" title="Daily Report Variants">
        <DCArtboard id="cp" label="C+. 타임라인 (보강형) ★" width={390} height={820}>
          <VariantCPlus />
        </DCArtboard>
        <DCArtboard id="c" label="C. 타임라인 (원본)" width={390} height={820}>
          <VariantC />
        </DCArtboard>
        <DCArtboard id="b" label="B. 브리핑 카드" width={390} height={820}>
          <VariantB />
        </DCArtboard>
        <DCArtboard id="a" label="A. 신문 톤" width={390} height={820}>
          <VariantA />
        </DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
