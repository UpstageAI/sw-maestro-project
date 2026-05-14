import type { OcrResult } from "./types";

const SAMPLE = `근로계약서

사용자(이하 "회사")와 근로자(이하 "사원")는 다음과 같이 근로계약을 체결한다.

제1조 (근로계약기간) 2025년 1월 1일부터 2025년 12월 31일까지로 한다.
제2조 (근무장소) 서울특별시 강남구 ...
제3조 (업무내용) 카페 매장 서비스 업무
제4조 (근로시간) 1일 9시간(휴게 30분 포함), 주 5일 근무, 주 45시간
제5조 (휴게시간) 12:00 ~ 12:30 (30분)
제6조 (임금) 월 1,800,000원, 매월 25일 지급
제7조 (휴일) 매주 일요일을 주휴일로 한다.
제8조 (수습기간) 입사일로부터 3개월간 수습기간으로 하며, 수습기간 중 임금은 본 임금의 90%로 한다.
`;

export async function ocrMock(filePath: string): Promise<OcrResult> {
  return { text: SAMPLE, source: "mock", raw: { mock: true, filePath } };
}
