# AWS RDS MySQL 데이터베이스 설정 가이드

## 1. AWS RDS MySQL 인스턴스 생성

### 1.1 AWS 콘솔에서 RDS 인스턴스 생성
1. AWS RDS 콘솔 접속
2. "데이터베이스 생성" 클릭
3. MySQL 선택 (8.0 이상 권장)
4. 설정:
   - 인스턴스 크기: db.t3.micro (테스트용) 또는 db.t3.small (프로덕션용)
   - 스토리지: 20GB (필요에 따라 조정)
   - 다중 AZ: 필요에 따라 선택
   - 백업 보존: 7일 (권장)

### 1.2 보안 그룹 설정
- 인바운드 규칙 추가:
  - Type: MySQL/Aurora (3306)
  - Source: 애플리케이션 서버 IP 또는 0.0.0.0/0 (개발용)

### 1.3 데이터베이스 생성
```sql
CREATE DATABASE IF NOT EXISTS tissue_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 2. 환경 변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```bash
# AWS RDS MySQL 설정
MYSQL_HOST=your-rds-endpoint.region.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=tissue_db

# 또는 전체 DATABASE_URL 사용
# DATABASE_URL=mysql+pymysql://username:password@host:port/tissue_db?charset=utf8mb4

# AWS 설정
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-west-2
AWS_S3_BUCKET=your_s3_bucket_name
```

## 3. 테이블 생성

### 3.1 자동 생성 (권장)
```bash
cd tissue-backend
python -m app.create_tables
```

### 3.2 수동 생성
제공된 SQL 스크립트를 사용하여 테이블을 수동으로 생성할 수 있습니다.

## 4. 연결 테스트

```bash
# Python에서 연결 테스트
python -c "
from app.database.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('✅ 데이터베이스 연결 성공!')
"
```

## 5. 주의사항

1. **보안**: 프로덕션 환경에서는 보안 그룹을 엄격하게 설정하세요
2. **백업**: 자동 백업을 활성화하세요
3. **모니터링**: CloudWatch를 사용하여 데이터베이스 성능을 모니터링하세요
4. **SSL**: 프로덕션에서는 SSL 연결을 사용하세요

## 6. 문제 해결

### 연결 오류
- 보안 그룹 설정 확인
- 엔드포인트 주소 확인
- 사용자명/비밀번호 확인

### 문자 인코딩 문제
- 데이터베이스가 utf8mb4로 설정되었는지 확인
- 연결 문자열에 `charset=utf8mb4` 포함

### 성능 문제
- 인스턴스 크기 업그레이드 고려
- 인덱스 최적화
- 쿼리 최적화 