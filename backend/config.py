import os
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # EIA API Configuration
    eia_api_key: str = Field(..., env="EIA_API_KEY", description="EIA API key for carbon intensity data")
    
    # Hugging Face Configuration (optional)
    huggingface_token: Optional[str] = Field(None, env="HUGGINGFACE_TOKEN", description="Hugging Face API token")
    
    # Application Configuration
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS"
    )
    
    # API Configuration
    api_version: str = Field("v1", env="API_VERSION")
    max_request_size: str = Field("10MB", env="MAX_REQUEST_SIZE")
    
    # Cache Configuration
    cache_ttl_minutes: int = Field(30, env="CACHE_TTL_MINUTES")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Create global settings instance
try:
    settings = Settings()
except Exception as e:
    print(f"Error loading settings: {e}")
    # Create settings with environment variables directly as fallback
    settings = Settings(
        eia_api_key=os.getenv("EIA_API_KEY", ""),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        cors_origins=["http://localhost:3000"]
    )