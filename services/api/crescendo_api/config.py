from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load environment variables and local .env values. Real environment variables
    # take precedence. Ignore unrelated keys shared with the frontend setup.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo"
    # Required: there is no built-in API credential. SecretStr masks normal string
    # representations; it is not encryption and must still be kept out of logs.
    dev_api_token: SecretStr = Field(min_length=32)

    @field_validator("dev_api_token")
    @classmethod
    def reject_placeholder(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value().startswith("replace-with-"):
            raise ValueError("Generate a random DEV_API_TOKEN before starting the API")
        return value


@lru_cache
def get_settings() -> Settings:
    # Read/validate once per process. Restart the API after changing configuration.
    return Settings()

