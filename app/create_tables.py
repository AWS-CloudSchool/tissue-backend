#!/usr/bin/env python3
"""
데이터베이스 테이블 생성 스크립트
"""

from app.database.core.database import engine
from app.database.core.database import Base

def create_tables():
    """모든 테이블 생성"""
    print("데이터베이스 테이블 생성 중...")
    Base.metadata.create_all(bind=engine)
    print("✅ 테이블 생성 완료!")
    
    print("\n생성된 테이블:")
    print("- user_analysis_jobs")
    print("- user_reports") 
    print("- user_audio_files")

if __name__ == "__main__":
    create_tables()