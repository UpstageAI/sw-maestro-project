-- =====================================================================
-- 노트북 추천 챗봇 — 더미 데이터 10건 (테스트/개발용)
--
-- 사용법:
--   sqlite3 db/laptops.db < db/schema.sql
--   sqlite3 db/laptops.db < db/seed_dummy.sql
--
-- 정책:
--   - schema.sql 의 모든 NOT NULL / UNIQUE 제약 충족
--   - OS 값은 부록 A.1.2 의 canonical 키워드 기준 ("Windows", "macOS", "FreeDOS", "Linux")
--     ※ Node D 가 `os LIKE '%Windows%'` 식으로 매칭하므로 버전 표기는 자유
--   - 해상도는 부록 A.1.1 의 canonical "WxH" 문자열만 사용
--   - 가격대는 80만~330만원 범위로 분산 (Node E LIMIT 5 검증용)
--   - brightness_nits 중 1건은 NULL (OQ-7 의 NULL-허용 매칭 검증용)
--   - detail_url 은 모두 고유 (UPSERT 키)
--
-- 검증:
--   sqlite3 db/laptops.db "SELECT COUNT(*) FROM laptops;"   -- 10
--   sqlite3 db/laptops.db "SELECT COUNT(*) FROM laptops
--     WHERE price_krw IS NULL OR cpu IS NULL OR ram_gb IS NULL OR storage_gb IS NULL;"  -- 0 (SM-6)
-- =====================================================================

BEGIN TRANSACTION;

-- 멱등성: 재실행 시 dummy URL 행만 정리 후 재삽입 (운영 데이터에 영향 없음)
DELETE FROM laptops WHERE detail_url LIKE 'https://prod.danawa.com/info/?pcode=DUMMY-%';

INSERT INTO laptops
    (product_name, screen_inch, weight_kg, os, resolution, brightness_nits,
     cpu, ram_gb, storage_gb, price_krw, thumbnail_url, detail_url, crawled_at)
VALUES
    -- 1. 초경량 비즈니스 — LG gram
    ('LG gram 14Z90S-G.AA50K',
     14.0, 0.99, 'Windows 11', '1920x1200', 400,
     'Intel Core Ultra 5-125H', 16, 256, 1690000,
     'https://img.danawa.com/prod_img/500000/dummy01.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0001',
     '2026-05-07T10:00:00.000Z'),

    -- 2. 학생용 보급형 — 삼성 갤럭시북4
    ('삼성전자 갤럭시북4 NT750XGR-A51A',
     15.6, 1.55, 'Windows 11', '1920x1080', 250,
     'Intel Core i5-1335U', 16, 512, 1290000,
     'https://img.danawa.com/prod_img/500000/dummy02.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0002',
     '2026-05-07T10:00:00.000Z'),

    -- 3. 디자이너용 고휘도 — 애플 MacBook Air M3
    ('Apple 맥북에어 13 M3 8C-10C 16GB 512GB',
     13.6, 1.24, 'macOS', '2560x1664', 500,
     'Apple M3', 16, 512, 1990000,
     'https://img.danawa.com/prod_img/500000/dummy03.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0003',
     '2026-05-07T10:00:00.000Z'),

    -- 4. 개발자 워크스테이션 — MacBook Pro M3 Pro
    ('Apple 맥북프로 14 M3 Pro 11C-14C 18GB 1TB',
     14.2, 1.61, 'macOS', '3024x1964', 600,
     'Apple M3 Pro', 18, 1024, 3290000,
     'https://img.danawa.com/prod_img/500000/dummy04.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0004',
     '2026-05-07T10:00:00.000Z'),

    -- 5. 게이밍 16인치 — ASUS TUF
    ('ASUS TUF Gaming A16 FA607PI-N3023',
     16.0, 2.20, 'FreeDOS', '2560x1600', 300,
     'AMD Ryzen 9 7940HX', 16, 1024, 2150000,
     'https://img.danawa.com/prod_img/500000/dummy05.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0005',
     '2026-05-07T10:00:00.000Z'),

    -- 6. 가성비 보급형 — 레노버 IdeaPad
    ('레노버 아이디어패드 슬림3 15IRH8',
     15.6, 1.62, 'FreeDOS', '1920x1080', 250,
     'Intel Core i5-13420H', 8, 256, 850000,
     'https://img.danawa.com/prod_img/500000/dummy06.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0006',
     '2026-05-07T10:00:00.000Z'),

    -- 7. 시니어/사무용 — HP 파빌리온 (밝기 NULL — OQ-7 NULL 허용 검증용)
    ('HP 파빌리온 15-eg3088TU',
     15.6, 1.75, 'Windows 11', '1920x1080', NULL,
     'Intel Core i7-1355U', 16, 512, 1390000,
     'https://img.danawa.com/prod_img/500000/dummy07.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0007',
     '2026-05-07T10:00:00.000Z'),

    -- 8. 리눅스 개발자용 — Dell XPS
    ('DELL XPS 13 Plus 9340 DEVELOPER EDITION',
     13.4, 1.24, 'Linux', '2880x1800', 500,
     'Intel Core Ultra 7-155H', 32, 1024, 2890000,
     'https://img.danawa.com/prod_img/500000/dummy08.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0008',
     '2026-05-07T10:00:00.000Z'),

    -- 9. 휴대성 + QHD — ASUS ZenBook
    ('ASUS 젠북14 OLED UX3405MA-PP193',
     14.0, 1.20, 'Windows 11', '2880x1800', 400,
     'Intel Core Ultra 7-155H', 16, 512, 1750000,
     'https://img.danawa.com/prod_img/500000/dummy09.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0009',
     '2026-05-07T10:00:00.000Z'),

    -- 10. 라이젠 가성비 — Acer Swift Go
    ('Acer 스위프트Go SFG14-71-71M3',
     14.0, 1.32, 'Windows 11', '2240x1400', 300,
     'AMD Ryzen 7 7840U', 16, 512, 1190000,
     'https://img.danawa.com/prod_img/500000/dummy10.jpg',
     'https://prod.danawa.com/info/?pcode=DUMMY-0010',
     '2026-05-07T10:00:00.000Z');

COMMIT;

-- =====================================================================
-- 빠른 검증 쿼리 (참고)
-- =====================================================================
-- SELECT COUNT(*) AS total FROM laptops;
-- SELECT os, COUNT(*) FROM laptops GROUP BY os;
-- SELECT product_name, price_krw FROM laptops ORDER BY price_krw ASC LIMIT 5;
-- SELECT product_name FROM laptops WHERE brightness_nits IS NULL OR brightness_nits >= 300;
