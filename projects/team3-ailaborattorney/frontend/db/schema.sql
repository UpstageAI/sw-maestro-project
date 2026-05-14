CREATE TABLE IF NOT EXISTS contracts (
  id TEXT PRIMARY KEY,
  file_path TEXT NOT NULL,
  original_name TEXT,
  parsed_data TEXT,        -- JSON: ContractData
  rule_result TEXT,        -- JSON: { violations: [...] }
  ai_result TEXT,          -- JSON: { summary, items }
  user_info TEXT,          -- JSON: { weekly_hours, age }
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS qa_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contract_id TEXT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (contract_id) REFERENCES contracts(id)
);
