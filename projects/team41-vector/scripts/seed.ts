import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import Papa from 'papaparse';

// ── DB 설정 (lib/db.ts와 동일 경로, 직접 열기) ──
const DB_PATH = path.join(process.cwd(), 'data', 'factpokmoney.db');

const dir = path.dirname(DB_PATH);
if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT DEFAULT '사용자',
    monthly_income INTEGER DEFAULT 2800000,
    current_savings INTEGER DEFAULT 5000000,
    created_at INTEGER
  );

  CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    date TEXT,
    category TEXT,
    merchant TEXT,
    amount INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
  );

  CREATE TABLE IF NOT EXISTS missions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    text TEXT,
    saving_amount INTEGER,
    created_at INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
  );

  CREATE TABLE IF NOT EXISTS chat_history (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    role TEXT,
    content TEXT,
    created_at INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
  );
`);

// ── 헬퍼 ──
const insertUser = db.prepare(
  `INSERT OR REPLACE INTO users (id, name, monthly_income, current_savings, created_at) VALUES (?, ?, ?, ?, ?)`,
);
const insertTx = db.prepare(
  `INSERT INTO transactions (user_id, date, category, merchant, amount) VALUES (?, ?, ?, ?, ?)`,
);
const deleteTx = db.prepare(`DELETE FROM transactions WHERE user_id = ?`);

// ── 페르소나 A: CSV 기반 ──
function seedPersonaA() {
  const csvPath = path.join(process.cwd(), 'sample-data', 'persona_A_transactions.csv');
  const csvContent = fs.readFileSync(csvPath, 'utf-8');
  const parsed = Papa.parse<{ date: string; category: string; merchant: string; amount: string }>(
    csvContent,
    { header: true, skipEmptyLines: true },
  );

  const now = Date.now();
  insertUser.run('persona-a', '소확행러', 2800000, 5000000, now);
  deleteTx.run('persona-a');

  const insertMany = db.transaction((rows: typeof parsed.data) => {
    for (const row of rows) {
      const amount = Number(row.amount);
      if (!row.date || isNaN(amount) || amount <= 0) continue;
      insertTx.run('persona-a', row.date, row.category, row.merchant, amount);
    }
  });

  insertMany(parsed.data);
  console.log(`[seed] persona-a: ${parsed.data.length}행 로드 완료`);
}

// ── 페르소나 B: 코드 생성 ──
function seedPersonaB() {
  const now = Date.now();
  insertUser.run('persona-b', '할부전사', 3500000, 2000000, now);
  deleteTx.run('persona-b');

  // 거래 데이터 직접 생성 (2025년 4월 기준)
  const txs: { date: string; category: string; merchant: string; amount: number }[] = [];

  // 전자기기 — 약 80만, 3행 (할부)
  txs.push({ date: '2025-04-05', category: '전자기기', merchant: '삼성 갤럭시 S25 (3/12회차)', amount: 412500 });
  txs.push({ date: '2025-04-10', category: '전자기기', merchant: '애플 에어팟 프로 (2/6회차)', amount: 165000 });
  txs.push({ date: '2025-04-15', category: '전자기기', merchant: 'LG 모니터 27인치 (4/10회차)', amount: 225000 });

  // 여행 — 약 60만, 4행 (할부 + 교통/숙박)
  txs.push({ date: '2025-04-12', category: '여행', merchant: '제주항공 서울-제주 (2/3회차)', amount: 183000 });
  txs.push({ date: '2025-04-12', category: '여행', merchant: '제주 호텔 숙박', amount: 180000 });
  txs.push({ date: '2025-04-13', category: '여행', merchant: '제주 렌터카 1일', amount: 85000 });
  txs.push({ date: '2025-04-13', category: '여행', merchant: '제주 맛집 흑돼지', amount: 152000 });

  // 구독료 — 약 12만, 6행
  txs.push({ date: '2025-04-01', category: '구독료', merchant: '넷플릭스', amount: 17000 });
  txs.push({ date: '2025-04-01', category: '구독료', merchant: '유튜브 프리미엄', amount: 14900 });
  txs.push({ date: '2025-04-01', category: '구독료', merchant: '스포티파이', amount: 10900 });
  txs.push({ date: '2025-04-01', category: '구독료', merchant: '어도비 크리에이티브 클라우드', amount: 36300 });
  txs.push({ date: '2025-04-01', category: '구독료', merchant: 'iCloud 200GB', amount: 3900 });
  txs.push({ date: '2025-04-02', category: '구독료', merchant: '헬스장 월회비', amount: 39000 });

  // 카페 — 약 15만, 15행
  const cafeMerchants = [
    '스타벅스 강남점', '투썸플레이스 역삼점', '컴포즈커피 선릉점', '메가커피 삼성역점',
    '이디야 역삼점', '할리스 테헤란로점', '블루보틀 삼청동', '스타벅스 삼성점',
  ];
  const cafeDates = [
    '2025-04-01', '2025-04-02', '2025-04-03', '2025-04-04', '2025-04-07',
    '2025-04-08', '2025-04-09', '2025-04-11', '2025-04-14', '2025-04-15',
    '2025-04-17', '2025-04-18', '2025-04-22', '2025-04-24', '2025-04-28',
  ];
  const cafeAmounts = [
    5800, 6500, 3500, 4500, 5800, 6500, 7200, 5800,
    4500, 3500, 5800, 6500, 4500, 5800, 7200,
  ]; // 합계 ~93,600 → 조정 필요
  // 목표 약 15만이므로 일부 단가 높이기
  const cafeAmountsAdj = [
    8500, 9500, 7500, 8800, 12000, 9800, 11500, 10200,
    9800, 8500, 12000, 9500, 10500, 11200, 10700,
  ]; // 합계 = 150,000
  for (let i = 0; i < 15; i++) {
    txs.push({
      date: cafeDates[i],
      category: '카페',
      merchant: cafeMerchants[i % cafeMerchants.length],
      amount: cafeAmountsAdj[i],
    });
  }

  // 배달 — 약 45만, 15행
  const deliveryMerchants = [
    '배달의민족(BBQ)', '쿠팡이츠(맥도날드)', '배달의민족(교촌치킨)', '쿠팡이츠(피자헛)',
    '배달의민족(BHC)', '배달의민족(엽기떡볶이)', '쿠팡이츠(KFC)', '배달의민족(굽네치킨)',
  ];
  const deliveryDates = [
    '2025-04-01', '2025-04-03', '2025-04-05', '2025-04-06', '2025-04-08',
    '2025-04-10', '2025-04-12', '2025-04-14', '2025-04-16', '2025-04-18',
    '2025-04-20', '2025-04-22', '2025-04-24', '2025-04-27', '2025-04-29',
  ];
  const deliveryAmounts = [
    28000, 32000, 26500, 35000, 24500, 31000, 28000, 33000,
    29500, 27000, 34000, 30000, 26000, 32500, 33000,
  ]; // 합계 = 450,000
  for (let i = 0; i < 15; i++) {
    txs.push({
      date: deliveryDates[i],
      category: '배달',
      merchant: deliveryMerchants[i % deliveryMerchants.length],
      amount: deliveryAmounts[i],
    });
  }

  // 식비 — 약 25만, 15행
  const foodMerchants = [
    '회사식당', '회사식당', '회사식당', '회사식당', '회사식당',
    '회사식당', '회사식당', '회사식당', '회사식당', '회사식당',
    '한솥 선릉점', '김밥천국 역삼점', '본죽 삼성점', '이삭토스트', '서브웨이 강남점',
  ];
  const foodDates = [
    '2025-04-01', '2025-04-02', '2025-04-03', '2025-04-04', '2025-04-07',
    '2025-04-08', '2025-04-09', '2025-04-10', '2025-04-11', '2025-04-14',
    '2025-04-16', '2025-04-18', '2025-04-21', '2025-04-23', '2025-04-25',
  ];
  const foodAmounts = [
    7000, 7000, 7000, 7000, 7000, 7000, 7000, 7000, 7000, 7000,
    35000, 28000, 18000, 42000, 62000,
  ]; // 합계 = 255,000 ≈ 25만
  for (let i = 0; i < 15; i++) {
    txs.push({
      date: foodDates[i],
      category: '식비',
      merchant: foodMerchants[i],
      amount: foodAmounts[i],
    });
  }

  // 교통 — 약 12만, 10행
  const transportDates = [
    '2025-04-01', '2025-04-02', '2025-04-03', '2025-04-04', '2025-04-07',
    '2025-04-08', '2025-04-14', '2025-04-18', '2025-04-22', '2025-04-25',
  ];
  const transportMerchants = [
    '지하철', '지하철', '지하철', '지하철', '지하철',
    '지하철', '카카오T 택시', '지하철', '카카오T 택시', '지하철',
  ];
  const transportAmounts = [
    1550, 1550, 1550, 1550, 1550, 1550, 48000, 1550, 52000, 9150,
  ]; // 합계 = 120,000
  for (let i = 0; i < 10; i++) {
    txs.push({
      date: transportDates[i],
      category: '교통',
      merchant: transportMerchants[i],
      amount: transportAmounts[i],
    });
  }

  // 술자리 — 약 40만, 5행
  txs.push({ date: '2025-04-04', category: '술자리', merchant: '강남 이자카야', amount: 65000 });
  txs.push({ date: '2025-04-11', category: '술자리', merchant: '홍대 포장마차', amount: 82000 });
  txs.push({ date: '2025-04-18', category: '술자리', merchant: '강남 와인바', amount: 95000 });
  txs.push({ date: '2025-04-23', category: '술자리', merchant: '삼성역 호프집', amount: 78000 });
  txs.push({ date: '2025-04-29', category: '술자리', merchant: '역삼 소맥집', amount: 80000 });

  // 쇼핑 — 약 20만, 5행
  txs.push({ date: '2025-04-06', category: '쇼핑', merchant: '무신사', amount: 52000 });
  txs.push({ date: '2025-04-10', category: '쇼핑', merchant: '29CM', amount: 38000 });
  txs.push({ date: '2025-04-17', category: '쇼핑', merchant: 'ABC마트 강남점', amount: 42000 });
  txs.push({ date: '2025-04-22', category: '쇼핑', merchant: '유니클로 삼성점', amount: 35000 });
  txs.push({ date: '2025-04-28', category: '쇼핑', merchant: '무신사', amount: 33000 });

  const insertMany = db.transaction((rows: typeof txs) => {
    for (const row of rows) {
      insertTx.run('persona-b', row.date, row.category, row.merchant, row.amount);
    }
  });

  insertMany(txs);
  console.log(`[seed] persona-b: ${txs.length}행 생성 완료`);
}

// ── 실행 ──
seedPersonaA();
seedPersonaB();

// 검증
const userCount = (db.prepare('SELECT COUNT(*) as cnt FROM users').get() as { cnt: number }).cnt;
const txCountA = (db.prepare('SELECT COUNT(*) as cnt FROM transactions WHERE user_id = ?').get('persona-a') as { cnt: number }).cnt;
const txCountB = (db.prepare('SELECT COUNT(*) as cnt FROM transactions WHERE user_id = ?').get('persona-b') as { cnt: number }).cnt;

console.log(`\n[검증]`);
console.log(`  users: ${userCount}명`);
console.log(`  persona-a transactions: ${txCountA}행`);
console.log(`  persona-b transactions: ${txCountB}행`);

db.close();
console.log('\n[seed] 완료!');
