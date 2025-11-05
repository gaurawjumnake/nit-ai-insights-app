from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:root@localhost:5434/organizationmanagement"

    class Config:
        env_file = "../.env"
        extra = "ignore"

settings = Settings()
