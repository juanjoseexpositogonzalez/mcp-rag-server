from dataclasses import dataclass
from decouple import config
from typing import Final


@dataclass
class Settings:
    # Scalekit Configuration
    SCALEKIT_ENVIRONMENT_URL: Final[str] = config("SCALEKIT_ENVIRONMENT_URL")
    SCALEKIT_CLIENT_ID: Final[str] = config("SCALEKIT_CLIENT_ID")
    SCALEKIT_CLIENT_SECRET: Final[str] = config("SCALEKIT_CLIENT_SECRET")
    SCALEKIT_RESOURCE_METADATA_URL: Final[str] = config("SCALEKIT_RESOURCE_METADATA_URL")
    SCALEKIT_AUDIENCE_NAME: Final[str] = config("SCALEKIT_AUDIENCE_NAME")
    METADATA_JSON_RESPONSE: Final[str] = config("METADATA_JSON_RESPONSE")
    PERSISTENT_DIR: Final[str] = "./chromadb"
    DATA_DIR: Final[str] = "./data"
    COLLECTION_NAME: Final[str] = "rag_mcp"

    # Llama API Key
    LLAMA_CLOUD_API_KEY: Final[str] = config("LLAMA_CLOUD_API_KEY")

    # Server Port
    PORT: Final[int] = config("PORT", default=10000, cast=int)

    def __post_init__(self):
        if not self.SCALEKIT_CLIENT_ID:
            raise ValueError("SCALEKIT_CLIENT_ID environment variable not set")
        if not self.SCALEKIT_CLIENT_SECRET:
            raise ValueError("SCALEKIT_CLIENT_SECRET environment variable not set")
        if not self.SCALEKIT_ENVIRONMENT_URL:
            raise ValueError("SCALEKIT_ENVIRONMENT_URL environment variable not set")
        if not self.SCALEKIT_RESOURCE_METADATA_URL:
            raise ValueError("SCALEKIT_RESOURCE_METADATA_URL environment variable not set")
        if not self.SCALEKIT_AUDIENCE_NAME:
            raise ValueError("SCALEKIT_AUDIENCE_NAME environment variable not set")
        if not self.LLAMA_CLOUD_API_KEY:
            raise ValueError("LLAMA_CLOUD_API_KEY environment variable not set")
        
settings = Settings()
