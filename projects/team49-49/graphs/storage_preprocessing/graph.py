from pathlib import Path

from app.core.config import Settings
from app.db.connection import resolve_sqlite_path
from app.repositories.sqlite import SQLiteRepository
from app.workflows.storage import StorageWorkflow


ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV = ROOT / ".env"

settings = Settings(_env_file=str(ROOT_ENV) if ROOT_ENV.exists() else None)
repository = SQLiteRepository(resolve_sqlite_path(settings.database_url))
repository.initialize()

graph = StorageWorkflow(repository).graph
