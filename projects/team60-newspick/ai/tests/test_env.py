import pytest

from newspick_ai.env import MissingEnvironmentError, load_environment, require_environment


def test_load_environment_reads_root_and_ai_env_without_overwriting_existing_values(
    tmp_path,
    monkeypatch,
):
    root_dir = tmp_path
    ai_dir = tmp_path / "ai"
    ai_dir.mkdir()
    (root_dir / ".env").write_text(
        "\ufeffUPSTAGE_API_KEY=root-key\nROOT_ONLY=enabled\n",
        encoding="utf-8",
    )
    (ai_dir / ".env").write_text(
        "DATABASE_URL=postgresql://newspick:test@localhost:5432/newspick\n"
        "UPSTAGE_API_KEY=ai-key\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("UPSTAGE_API_KEY", "injected-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ROOT_ONLY", raising=False)

    load_environment(root_dir=root_dir, ai_dir=ai_dir)

    assert require_environment(
        ("UPSTAGE_API_KEY", "DATABASE_URL", "ROOT_ONLY"),
        root_dir=root_dir,
        ai_dir=ai_dir,
    ) == {
        "UPSTAGE_API_KEY": "injected-key",
        "DATABASE_URL": "postgresql://newspick:test@localhost:5432/newspick",
        "ROOT_ONLY": "enabled",
    }


def test_require_environment_raises_friendly_error_when_required_value_is_missing(
    tmp_path,
    monkeypatch,
):
    ai_dir = tmp_path / "ai"
    ai_dir.mkdir()
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)

    with pytest.raises(MissingEnvironmentError) as exc:
        require_environment(("UPSTAGE_API_KEY",), root_dir=tmp_path, ai_dir=ai_dir)

    assert str(exc.value) == "AI 설정을 읽지 못해 재수집을 완료하지 못했어요."
