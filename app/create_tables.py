# create_tables.py
from app.database.core.database import Base, engine

# 모든 테이블을 MySQL에 생성
Base.metadata.create_all(bind=engine)
print("✅ 모든 테이블이 생성되었습니다!")