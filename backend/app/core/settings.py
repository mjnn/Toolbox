class Settings:
    API_V1_STR = "/api/v1"
    PROJECT_NAME = "Tools Platform"
    BACKEND_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
    DATABASE_URL = "sqlite:///./app.db"  # 实际运行以 backend/.env 的 DATABASE_URL 为准（生产多为 PostgreSQL）
    SECRET_KEY = "your-strong-secret-key"  # 生产环境必须修改
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    FIRST_SUPERUSER = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD = "admin123"

settings = Settings()
