/**
 * Hanging Indent Calculator (내어쓰기 자동 계산기)
 *
 * 마커 기반 룩업 테이블 + 폰트 크기 스케일링으로
 * 80% 이상의 정확성을 목표로 함
 *
 * 개선 v2:
 * - 앞 공백 포함 계산
 * - 한글 폰트 보정 계수 적용
 * - 공백 너비 조정
 */
export interface MarkerInfo {
    marker: string;
    type: MarkerType;
    leadingSpaces: number;
}
export type MarkerType = 'bullet' | 'number' | 'korean' | 'parenthesized' | 'parenthesized_korean' | 'circled' | 'roman' | 'alpha' | 'article';
export declare class HangingIndentCalculator {
    private static readonly DEFAULT_FONT_SIZE;
    /**
     * 문자의 너비를 em 단위로 반환
     */
    private getCharWidth;
    /**
     * 마커 문자열의 너비를 em 단위로 계산
     */
    private calculateMarkerWidthInEm;
    /**
     * 마커 너비 계산 (points 단위)
     *
     * @param marker 마커 문자열 (예: "○ ", "1. ")
     * @param fontSize 폰트 크기 (pt)
     * @param fontName 폰트 이름 (선택적, 기본값 사용시 생략)
     * @returns 마커의 너비 (pt)
     */
    calculateMarkerWidth(marker: string, fontSize: number, fontName?: string | null): number;
    /**
     * 텍스트에서 마커 감지 (앞 공백 포함)
     *
     * @param text 텍스트
     * @returns 마커 정보 또는 null
     */
    detectMarker(text: string): MarkerInfo | null;
    /**
     * 텍스트에서 내어쓰기 값 자동 계산 (points 단위)
     *
     * @param text 텍스트
     * @param fontSize 폰트 크기 (pt, 기본값 12pt)
     * @param fontName 폰트 이름 (선택적, 기본값 사용시 생략)
     * @returns 내어쓰기 값 (pt)
     */
    calculateHangingIndent(text: string, fontSize?: number, fontName?: string | null): number;
    /**
     * points를 HWPUNIT으로 변환
     *
     * @param points 포인트 값
     * @returns HWPUNIT 값 (points × 100)
     */
    toHwpUnit(points: number): number;
    /**
     * 텍스트에서 내어쓰기 값 자동 계산 (HWPUNIT 단위)
     *
     * @param text 텍스트
     * @param fontSize 폰트 크기 (pt, 기본값 12pt)
     * @param fontName 폰트 이름 (선택적, 기본값 사용시 생략)
     * @returns 내어쓰기 값 (HWPUNIT)
     */
    calculateHangingIndentInHwpUnit(text: string, fontSize?: number, fontName?: string | null): number;
}
