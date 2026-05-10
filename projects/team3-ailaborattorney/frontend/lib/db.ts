import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";

const DB_PATH = path.join(process.cwd(), "data.db");
const SCHEMA_PATH = path.join(process.cwd(), "db", "schema.sql");

let _db: Database.Database | null = null;
export function getDb(): Database.Database {
  if (_db) return _db;
  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");
  if (fs.existsSync(SCHEMA_PATH)) {
    db.exec(fs.readFileSync(SCHEMA_PATH, "utf8"));
  }
  _db = db;
  return db;
}
