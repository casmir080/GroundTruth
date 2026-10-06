from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_key: str
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-plus"
    api_key: str = Field(default="", validation_alias="GROUNDTRUTH_API_KEY")  # required to call protected routes; see .env.example
    slack_webhook_url: str = ""  # optional; alerts print to stdout if unset
    frontend_origin: str = "http://localhost:3000"  # CORS allowance for the dashboard


settings = Settings()
