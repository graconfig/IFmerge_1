"""应用配置（从可写数据目录的 .env 加载/写回）——对应 analyzer.config.AppConfig。"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv, set_key

from analyzer.runtime import app_data_dir, resource_path

# .env 位于可写数据目录:开发态= 仓库根;打包后= 可执行文件同级目录(可持久化)。
_ENV_PATH = app_data_dir() / ".env"


@dataclass
class Settings:
    # 路径
    input_dir: str = "input"
    output_dir: str = "output"
    template_path: str = "reference/IF抽出_新フォーマット.xlsx"
    reference_path: str = "reference/本社EBS現行IF一覧.xlsx"

    # AI 分析参数
    phase1_head_rows: int = 30
    max_chunk_rows: int = 100

    # SAP AI Core
    aicore_auth_url: str = ""
    aicore_client_id: str = ""
    aicore_client_secret: str = ""
    aicore_base_url: str = ""
    aicore_resource_group: str = "default"
    aicore_deployment_id: str = ""

    # 运行
    log_level: str = "INFO"

    @classmethod
    def load(cls) -> "Settings":
        # override=True:.env 为权威来源，覆盖残留系统环境变量。
        load_dotenv(_ENV_PATH, override=True)
        # 默认值锚定到可写/资源目录的绝对路径，避免打包后相对当前工作目录解析失败。
        return cls(
            input_dir=os.getenv("INPUT_DIR", str(app_data_dir() / "input")),
            output_dir=os.getenv("OUTPUT_DIR", str(app_data_dir() / "output")),
            template_path=os.getenv(
                "TEMPLATE_PATH",
                str(resource_path("reference", "IF抽出_新フォーマット.xlsx"))),
            reference_path=os.getenv(
                "REFERENCE_PATH",
                str(resource_path("reference", "本社EBS現行IF一覧.xlsx"))),
            phase1_head_rows=int(os.getenv("PHASE1_HEAD_ROWS", "30")),
            max_chunk_rows=int(os.getenv("MAX_CHUNK_ROWS", "100")),
            aicore_auth_url=os.getenv("AICORE_AUTH_URL", ""),
            aicore_client_id=os.getenv("AICORE_CLIENT_ID", ""),
            aicore_client_secret=os.getenv("AICORE_CLIENT_SECRET", ""),
            aicore_base_url=os.getenv("AICORE_BASE_URL", ""),
            aicore_resource_group=os.getenv("AICORE_RESOURCE_GROUP", "default"),
            aicore_deployment_id=os.getenv("AICORE_DEPLOYMENT_ID", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def save(self) -> str:
        """逐键写回 .env（保留其它内容），返回写入的文件路径。"""
        path = str(_ENV_PATH)
        if not _ENV_PATH.exists():
            _ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
            _ENV_PATH.touch()
        pairs = {
            "INPUT_DIR": self.input_dir,
            "OUTPUT_DIR": self.output_dir,
            "TEMPLATE_PATH": self.template_path,
            "REFERENCE_PATH": self.reference_path,
            "PHASE1_HEAD_ROWS": str(self.phase1_head_rows),
            "MAX_CHUNK_ROWS": str(self.max_chunk_rows),
            "AICORE_AUTH_URL": self.aicore_auth_url,
            "AICORE_CLIENT_ID": self.aicore_client_id,
            "AICORE_CLIENT_SECRET": self.aicore_client_secret,
            "AICORE_BASE_URL": self.aicore_base_url,
            "AICORE_RESOURCE_GROUP": self.aicore_resource_group,
            "AICORE_DEPLOYMENT_ID": self.aicore_deployment_id,
            "LOG_LEVEL": self.log_level,
        }
        for key, value in pairs.items():
            set_key(path, key, value or "")
        return path
