import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

// ─── 싱글톤 DB ───
// Next.js dev 모드에서 HMR 시 모듈이 재로드되므로, globalThis에 캐싱해서
// DB 커넥션이 중복 생성되는 것을 방지.
declare global {
  // eslint-disable-next-line no-var
  var __db: Database.Database | undefined;
}

// DB 파일 경로: 프로젝트 루트/data/factpokmoney.db
const DB_PATH = path.join(process.cwd(), 'data', 'factpokmoney.db');

function getDb(): Database.Database {
  // 이미 연결된 DB가 있으면 재사용
  if (globalThis.__db) {
    return globalThis.__db;
  }

  // data/ 디렉토리 없으면 생성
  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  const db = new Database(DB_PATH);

  // WAL 모드: 읽기/쓰기 동시성 향상, foreign_keys: FK 제약 활성화
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  // ── 테이블 스키마 ──
  // users: 유저 정보 (월수입, 현재 저축액)
  // transactions: CSV에서 파싱된 거래 내역
  // missions: Coach가 제안한 절약 미션 (status: pending/accepted/rejected)
  // chat_history: 대화 이력 (Coach에게 맥락으로 제공, 최근 20건)
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
      status TEXT DEFAULT 'pending',
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

  globalThis.__db = db;
  return db;
}

export default getDb;
