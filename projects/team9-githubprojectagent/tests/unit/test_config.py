"""config 모듈 단위 테스트."""
import pytest
from src import config


class TestConfigTypes:
    def test_max_refine_iter_is_int(self):
        assert isinstance(config.MAX_REFINE_ITER, int)

    def test_max_refine_iter_is_positive(self):
        assert config.MAX_REFINE_ITER >= 1

    def test_score_threshold_is_int(self):
        assert isinstance(config.SCORE_THRESHOLD, int)

    def test_score_threshold_in_valid_range(self):
        assert 0 <= config.SCORE_THRESHOLD <= 100

    def test_model_name_is_string(self):
        assert isinstance(config.MODEL_NAME, str)
        assert len(config.MODEL_NAME) > 0

    def test_effort_fast_is_string(self):
        assert isinstance(config.EFFORT_FAST, str)

    def test_effort_deep_is_string(self):
        assert isinstance(config.EFFORT_DEEP, str)


class TestConfigPaths:
    def test_root_path_exists(self):
        assert config.ROOT.exists()

    def test_output_dir_created(self):
        assert config.OUTPUT_DIR.exists()
        assert config.OUTPUT_DIR.is_dir()

    def test_cache_dir_created(self):
        assert config.CACHE_DIR.exists()
        assert config.CACHE_DIR.is_dir()

    def test_output_dir_is_under_root(self):
        assert config.ROOT in config.OUTPUT_DIR.parents or config.OUTPUT_DIR == config.ROOT


class TestRepoSizeGuards:
    def test_max_commits_fetch_is_positive(self):
        assert config.MAX_COMMITS_FETCH > 0

    def test_max_files_fetch_is_positive(self):
        assert config.MAX_FILES_FETCH > 0

    def test_max_file_size_kb_is_positive(self):
        assert config.MAX_FILE_SIZE_KB > 0

    def test_core_dirs_is_list(self):
        assert isinstance(config.CORE_DIRS, list)
        assert len(config.CORE_DIRS) > 0

    def test_core_files_includes_readme(self):
        assert "README.md" in config.CORE_FILES

    def test_core_files_includes_dockerfile(self):
        assert "Dockerfile" in config.CORE_FILES
