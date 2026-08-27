from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    # DATABASE_URL: str = "sqlite:///database.db"  # for docker/sqlite  # only needed if no .env i suppose
    DATABASE_URL: str

    @property
    def COOKIE_DOMAIN(self) -> str:
        if self.ENVIRONMENT == "production":
            return ".kaiser-workingground.ru"
        return "localhost"

    @property
    def COOKIE_SECURE(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def COOKIE_HTTPONLY(self) -> bool:
        return self.ENVIRONMENT == "production"

    class Config:
        env_file = ".env"

settings = Settings()
