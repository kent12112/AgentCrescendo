# Learn: From functools, import lru_cache (caches process-level settings or connection-manager
# construction).
from functools import lru_cache

# Learn: From pydantic, import Field (specifies validation constraints and defaults); SecretStr (masks
# ordinary string representations; it is not encryption); field_validator (attaches custom normalization or
# validation to a schema field).
from pydantic import Field, SecretStr, field_validator
# Learn: From pydantic_settings, import BaseSettings (loads and validates environment-based configuration);
# SettingsConfigDict (configures environment settings loading).
from pydantic_settings import BaseSettings, SettingsConfigDict


# Learn: Define Settings inheriting BaseSettings. Indented methods and attributes belong to this class.
class Settings(BaseSettings):
    # Load environment variables and local .env values. Real environment variables
    # take precedence. Ignore unrelated keys shared with the frontend setup.
    # Learn: Set model_config to SettingsConfigDict(env_file='.env', extra='ignore').
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Learn: Set database_url to 'postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo'.
    database_url: str = "postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo"
    # Required: there is no built-in API credential. SecretStr masks normal string
    # representations; it is not encryption and must still be kept out of logs.
    # Learn: Set dev_api_token to Field(min_length=32). Set the Pydantic default and validation limits for
    # this field.
    dev_api_token: SecretStr = Field(min_length=32)

    # Learn: Register field validation/normalization to run during Pydantic model validation.
    @field_validator("dev_api_token")
    # Learn: Bind the method to the class (cls), rather than an instance (self).
    @classmethod
    # Learn: Define reject_placeholder(value). The body runs when called, not when defined.
    def reject_placeholder(cls, value: SecretStr) -> SecretStr:
        # Learn: Take this branch only if value.get_secret_value().startswith('replace-with-').
        if value.get_secret_value().startswith("replace-with-"):
            # Learn: Raise ValueError('Generate a random DEV_API_TOKEN before starting the API') to stop the
            # normal path.
            raise ValueError("Generate a random DEV_API_TOKEN before starting the API")
        # Learn: Return value to the caller and stop this function.
        return value


# Learn: Cache calls by arguments so settings/engine construction is reused within this process.
@lru_cache
# Learn: Define get_settings(). The body runs when called, not when defined.
def get_settings() -> Settings:
    # Read/validate once per process. Restart the API after changing configuration.
    # Learn: Return Settings() to the caller and stop this function.
    return Settings()

