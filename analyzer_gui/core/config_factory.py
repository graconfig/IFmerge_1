"""用 GUI Settings 构造 analyzer 的 AppConfig(使设置成为权威来源)。"""

from analyzer.config import AppConfig

from analyzer_gui.config.settings import Settings


def build_config(settings: Settings) -> AppConfig:
    """根据 settings 构造 analyzer.config.AppConfig。

    与 analyzer.config.load_config() 等价,但取值来自 GUI 设置而非环境变量,
    使设定弹窗的修改即时生效。
    """
    return AppConfig(
        auth_url=settings.aicore_auth_url,
        client_id=settings.aicore_client_id,
        client_secret=settings.aicore_client_secret,
        base_url=settings.aicore_base_url,
        resource_group=settings.aicore_resource_group or "default",
        deployment_id=settings.aicore_deployment_id,
        input_dir=settings.input_dir,
        output_dir=settings.output_dir,
        phase1_head_rows=settings.phase1_head_rows,
        max_chunk_rows=settings.max_chunk_rows,
        template_path=settings.template_path,
        reference_path=settings.reference_path,
    )
