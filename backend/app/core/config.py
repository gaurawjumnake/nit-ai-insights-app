from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
POOLER_HOST = os.getenv("host")

DATABASE_URL=f"postgresql://{USER}:{PASSWORD}@{POOLER_HOST}:5432/postgres"

class Settings(BaseSettings):
    DATABASE_URL: str = DATABASE_URL

    class Config:
        env_file = "../.env"
        extra = "ignore"

settings = Settings()
