class Settings:
    API_V1_STR = "/api/v1"
    PROJECT_NAME = "Tools Platform"
    BACKEND_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
    DATABASE_URL = "postgresql+psycopg2://user:pass@localhost:5432/dbname"  # 占位；实际以 backend/.env 为准
    SECRET_KEY = "your-strong-secret-key"  # 生产环境必须修改
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    FIRST_SUPERUSER = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD = "admin123"

settings = Settings()
