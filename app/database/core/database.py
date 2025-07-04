from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

def get_database_url():
    """MySQL 데이터베이스 URL 생성"""
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    
    # AWS RDS MySQL 연결 문자열 생성
    if all([settings.MYSQL_HOST, settings.MYSQL_USER, settings.MYSQL_PASSWORD, settings.MYSQL_DATABASE]):
        return f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}?charset=utf8mb4"
    
    raise ValueError("데이터베이스 연결 정보가 설정되지 않았습니다.")

# 데이터베이스 URL이 None이 아닌지 확인
database_url = get_database_url()
engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()