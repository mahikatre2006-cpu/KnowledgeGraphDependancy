import os
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "Knowledge Dependency Graph API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"


settings = Settings()
