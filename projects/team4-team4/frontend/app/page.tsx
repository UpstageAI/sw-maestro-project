"use client";

import { FormEvent, useState } from "react";
import { GenerateResponse, generatePatent } from "../lib/api";
import { sampleResponse } from "../lib/sampleResponse";

export default function Home() {
  const [idea, setIdea] = useState("방구로 가는 자동차");
  const [result, setResult] = useState<GenerateResponse>(sampleResponse);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const response = await generatePatent({ idea, tone: "serious", use_search: true });
      setResult(response);
    } catch {
      setError("API 연결에 실패해 샘플 결과를 표시합니다.");
      setResult(sampleResponse);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="workspace">
        <div className="intro">
          <p className="eyebrow">Brainrot Patent</p>
          <h1>황당한 아이디어를 특허 명세서처럼 바꿉니다.</h1>
          <p>
            엔터테인먼트 목적의 2주 MVP 데모입니다. 실제 특허 출원, 법률 자문,
            신규성 판단을 제공하지 않습니다.
          </p>
        </div>

        <form className="composer" onSubmit={onSubmit}>
          <label htmlFor="idea">발명 아이디어</label>
          <textarea
            id="idea"
            value={idea}
            onChange={(event) => setIdea(event.target.value)}
            rows={4}
            placeholder="예: 잠을 대신 자주는 베개"
          />
          <button type="submit" disabled={isLoading || idea.trim().length === 0}>
            {isLoading ? "특허 문체로 변환 중..." : "명세서 생성"}
          </button>
          {error ? <p className="error">{error}</p> : null}
        </form>
      </section>

      <section className="document" aria-live="polite">
        <div className="documentHeader">
          <span>창작형 특허 명세서</span>
          <strong>{result.document.title}</strong>
        </div>

        <Section title="기술분야" body={result.document.technical_field} />
        <Section title="배경기술" body={result.document.background} />
        <Section title="해결하려는 과제" body={result.document.problem} />
        <Section title="발명의 구성" body={result.document.configuration} />

        <article className="section">
          <h2>청구항</h2>
          <ol>
            {result.document.claims.map((claim, index) => (
              <li key={index}>{claim}</li>
            ))}
          </ol>
        </article>

        <Section title="요약" body={result.document.summary} />

        <article className="section compact">
          <h2>근거</h2>
          {result.sources.length > 0 ? (
            <ul>
              {result.sources.map((source) => (
                <li key={source.url}>
                  <a href={source.url}>{source.title}</a>
                  <p>{source.snippet}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p>검색 근거 없이 생성된 데모 결과입니다.</p>
          )}
        </article>

        <footer>
          {result.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </footer>
      </section>
    </main>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <article className="section">
      <h2>{title}</h2>
      <p>{body}</p>
    </article>
  );
}
