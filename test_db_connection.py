#!/usr/bin/env python3
"""
데이터베이스 연결 테스트 스크립트
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """데이터베이스 연결을 테스트합니다."""
    try:
        from app.database.core.database import engine
        from sqlalchemy import text
        
        print("🔍 데이터베이스 연결 테스트 중...")
        
        with engine.connect() as conn:
            # 간단한 쿼리 실행
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            
            if row and row.test == 1:
                print("✅ 데이터베이스 연결 성공!")
                
                # MySQL 버전 확인
                version_result = conn.execute(text("SELECT VERSION() as version"))
                version_row = version_result.fetchone()
                print(f"📊 MySQL 버전: {version_row.version}")
                
                # 데이터베이스 이름 확인
                db_result = conn.execute(text("SELECT DATABASE() as database_name"))
                db_row = db_result.fetchone()
                print(f"🗄️  현재 데이터베이스: {db_row.database_name}")
                
                return True
            else:
                print("❌ 데이터베이스 연결 실패: 예상치 못한 결과")
                return False
                
    except Exception as e:
        print(f"❌ 데이터베이스 연결 오류: {str(e)}")
        print("\n🔧 문제 해결 방법:")
        print("1. .env 파일에서 데이터베이스 설정을 확인하세요")
        print("2. AWS RDS 인스턴스가 실행 중인지 확인하세요")
        print("3. 보안 그룹에서 3306 포트가 열려있는지 확인하세요")
        print("4. 사용자명과 비밀번호가 올바른지 확인하세요")
        return False

def test_table_creation():
    """테이블 생성 테스트"""
    try:
        from app.database.core.database import Base, engine
        from app.database.models.database_models import UserAnalysisJob, UserReport, UserAudioFile
        
        print("\n🔍 테이블 생성 테스트 중...")
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        print("✅ 테이블 생성 성공!")
        
        # 테이블 목록 확인
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 생성된 테이블: {', '.join(tables)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테이블 생성 오류: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 데이터베이스 연결 테스트 시작\n")
    
    # 연결 테스트
    if test_database_connection():
        # 테이블 생성 테스트
        test_table_creation()
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("\n💥 테스트가 실패했습니다. 위의 문제 해결 방법을 확인하세요.")
        sys.exit(1) 