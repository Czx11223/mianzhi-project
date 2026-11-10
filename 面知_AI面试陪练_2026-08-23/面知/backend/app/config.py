from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 大模型（默认 DeepSeek；无密钥时自动降级为内置 mock，保证可运行）
    model_name: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.7
    max_tokens: int = 2048
    # 备用大模型（当未配置 DeepSeek Key 时，回退到硅基流动 OpenAI 兼容端点，
    # 与 ASR 共用 MIANZHI_OPENAI_API_KEY / MIANZHI_OPENAI_BASE_URL）。
    llm_model: str = "deepseek-ai/DeepSeek-V3"

    # 数据库
    db_path: str = "data/mianzhi.db"
    # 只读种子库（FC 部署用）：代码包中的 SQLite 文件，启动时复制到可写目录。
    # 留空 = 本地开发模式，直接使用 db_path。
    db_seed: str = ""

    # 落地页里「前台/后台」链接的站点根地址（FC 上填 EdgeOne Pages 域名）
    web_url: str = ""

    # 是否启用 ChromaDB 向量检索（False 时退化为关键字匹配）
    use_vector: bool = False

    model_config = SettingsConfigDict(env_prefix="MIANZHI_", env_file=".env", extra="ignore")


settings = Settings()
