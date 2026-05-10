from dotenv import load_dotenv

load_dotenv()


def pytest_configure(config):
    config.addinivalue_line("markers", "kpi: KPI 시나리오 테스트 (pytest -m kpi)")
