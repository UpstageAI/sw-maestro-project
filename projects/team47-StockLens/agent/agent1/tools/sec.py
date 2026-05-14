from __future__ import annotations

import functools

import requests

from models.schema import SECFiling

HEADERS = {"User-Agent": "AI47-Project wlsrl723@gmail.com"}
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
TARGET_FORMS = {"8-K", "4", "10-Q", "10-K"}


def fetch_sec_filings(ticker: str, start_date: str, end_date: str) -> list[SECFiling]:
    """SEC EDGAR 공시 수집. 실패 시 빈 리스트 반환."""
    cik = _get_cik(ticker)
    if not cik:
        return []

    cik_padded = str(cik).zfill(10)
    url = SUBMISSIONS_URL.format(cik=cik_padded)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    filings_raw = data.get("filings", {}).get("recent", {})
    forms = filings_raw.get("form", [])
    dates = filings_raw.get("filingDate", [])
    descriptions = filings_raw.get("primaryDocument", [])
    accession_numbers = filings_raw.get("accessionNumber", [])

    results: list[SECFiling] = []
    for form, filed_at, desc, acc_no in zip(forms, dates, descriptions, accession_numbers):
        if form not in TARGET_FORMS:
            continue
        if not (start_date <= filed_at <= end_date):
            continue

        # 올바른 EDGAR 파일 경로: /Archives/edgar/data/{cik}/{acc_compact}/{primary_doc}
        acc_compact = acc_no.replace("-", "")
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_compact}/{acc_no}-index.htm"
        )
        results.append(
            SECFiling(
                form_type=form,
                filed_at=filed_at,
                description=desc or form,
                url=filing_url,
            )
        )

    return results


@functools.lru_cache(maxsize=1)
def _get_cik(ticker: str) -> int | None:
    """ticker → CIK 변환. 결과를 캐싱해 반복 다운로드 방지."""
    resp = requests.get(TICKERS_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            return int(entry["cik_str"])
    return None
