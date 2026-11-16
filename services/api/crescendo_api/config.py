# Import from functools: lru_cache (caches process-level settings or connection-manager
# construction).
from functools import lru_cache

# Import from pydantic: Field (specifies validation constraints and defaults); SecretStr (masks
# ordinary string representations; it is not encryption); field_validator (attaches custom
# normalization or validation to a schema field).
from pydantic import Field, SecretStr, field_validator
# Import from pydantic_settings: BaseSettings (loads and validates environment-based configuration);
# SettingsConfigDict (configures environment settings loading).
from pydantic_settings import BaseSettings, SettingsConfigDict


# Define Settings as a subclass of BaseSettings.
class Settings(BaseSettings):
    # Load environment variables and local .env values. Real environment variables
    # take precedence. Ignore unrelated keys shared with the frontend setup.
    # Set model_config to SettingsConfigDict(env_file='.env', extra='ignore').
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Set database_url to 'postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo'.
    database_url: str = "postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo"
    # Required: there is no built-in API credential. SecretStr masks normal string
    # representations; it is not encryption and must still be kept out of logs.
    # Define dev_api_token with these defaults and validation rules: min_length=32.
    dev_api_token: SecretStr = Field(min_length=32)

    # Register field validation/normalization to run during Pydantic model validation.
    @field_validator("dev_api_token")
    # Bind the method to the class (cls), rather than an instance (self).
    @classmethod
    # Define reject_placeholder with parameters cls, value.
    def reject_placeholder(cls, value: SecretStr) -> SecretStr:
        # Check whether value.get_secret_value().startswith('replace-with-').
        if value.get_secret_value().startswith("replace-with-"):
            # Raise ValueError('Generate a random DEV_API_TOKEN before starting the API') to stop
            # the normal path.
            raise ValueError("Generate a random DEV_API_TOKEN before starting the API")
        # Return value.
        return value


# Cache calls by arguments so settings/engine construction is reused within this process.
@lru_cache
# Define get_settings with no parameters.
def get_settings() -> Settings:
    # Read/validate once per process. Restart the API after changing configuration.
    # Return Settings().
    return Settings()

