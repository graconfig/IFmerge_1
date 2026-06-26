"""analyzer.runtime 路径解析测试(开发态 + 模拟打包态)。"""

from analyzer import runtime


def test_not_frozen_in_dev():
    assert runtime.is_frozen() is False


def test_resource_path_points_to_repo_root_in_dev():
    root = runtime.resource_path()
    # 仓库根应存在这些标志性文件/目录。
    assert (root / "prompts.yaml").exists()
    assert (root / "reference").is_dir()


def test_bundled_resources_resolve_to_existing_files_in_dev():
    assert runtime.resource_path("prompts.yaml").exists()
    assert runtime.resource_path(
        "reference", "IF抽出_新フォーマット.xlsx").exists()
    assert runtime.resource_path(
        "reference", "本社EBS現行IF一覧.xlsx").exists()
    assert runtime.resource_path(
        "analyzer_gui", "i18n", "locales", "zh.json").exists()


def test_app_data_dir_is_repo_root_in_dev():
    assert runtime.app_data_dir() == runtime.resource_path()


def test_resource_path_uses_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert runtime.resource_path("prompts.yaml") == tmp_path / "prompts.yaml"


def test_app_data_dir_uses_executable_dir_when_frozen(monkeypatch, tmp_path):
    fake_exe = tmp_path / "IFAnalyzer.exe"
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime.sys, "executable", str(fake_exe), raising=False)
    assert runtime.app_data_dir() == tmp_path
