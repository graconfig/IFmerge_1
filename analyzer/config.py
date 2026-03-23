import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class AppConfig:
    auth_url: str
    client_id: str
    client_secret: str
    base_url: str
    resource_group: str
    deployment_id: str
    input_dir: str
    output_dir: str
    phase1_head_rows: int
    max_chunk_rows: int
    template_path: str
    reference_path: str


def load_config() -> AppConfig:
    """加载配置，缺少必要变量时抛出 ValueError"""
    load_dotenv()
    required = [
        'AICORE_AUTH_URL',
        'AICORE_CLIENT_ID',
        'AICORE_CLIENT_SECRET',
        'AICORE_BASE_URL',
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(f"缺少必要的环境变量: {', '.join(missing)}")
    return AppConfig(
        auth_url=os.getenv('AICORE_AUTH_URL'),
        client_id=os.getenv('AICORE_CLIENT_ID'),
        client_secret=os.getenv('AICORE_CLIENT_SECRET'),
        base_url=os.getenv('AICORE_BASE_URL'),
        resource_group=os.getenv('AICORE_RESOURCE_GROUP', 'default'),
        deployment_id=os.getenv('AICORE_DEPLOYMENT_ID', ''),
        input_dir=os.getenv('INPUT_DIR', 'input'),
        output_dir=os.getenv('OUTPUT_DIR', 'output'),
        phase1_head_rows=int(os.getenv('PHASE1_HEAD_ROWS', '30')),
        max_chunk_rows=int(os.getenv('MAX_CHUNK_ROWS', '100')),
        template_path=os.getenv('TEMPLATE_PATH', 'reference/IF抽出_新フォーマット.xlsx'),
        reference_path=os.getenv('REFERENCE_PATH', 'reference/本社EBS現行IF一覧.xlsx'),
    )
