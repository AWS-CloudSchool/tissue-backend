# YouTube Analysis Backend API

AI 기반 YouTube 영상 분석 및 리포트 생성 백엔드 서비스

## 🚀 주요 기능

- **YouTube 영상 분석**: AI 기반 자막 추출, 요약, 시각화 생성
- **스마트 챗봇**: RAG 기반 대화형 AI 어시스턴트
- **음성 생성**: AWS Polly를 활용한 TTS 서비스
- **검색 서비스**: YouTube 콘텐츠 검색 및 필터링
- **파일 관리**: S3 기반 안전한 파일 저장소
- **사용자 인증**: AWS Cognito 기반 인증 시스템

## 🏗️ 아키텍처

```
├── app/
│   ├── analyze/          # YouTube 분석 워크플로우
│   ├── auth/            # 사용자 인증 (AWS Cognito)
│   ├── audio/           # 음성 생성 (AWS Polly)
│   ├── chatbot/         # AI 챗봇 (Bedrock + RAG)
│   ├── core/            # 공통 설정
│   ├── database/        # 데이터베이스 관리
│   ├── s3/              # 파일 저장소
│   ├── search/          # YouTube 검색
│   └── main.py          # FastAPI 애플리케이션
├── Dockerfile           # Docker 설정
├── requirements.txt     # Python 의존성
└── README.md
```

## 🛠️ 기술 스택

### Backend Framework
- **FastAPI**: 고성능 웹 프레임워크
- **Python 3.11**: 최신 Python 버전

### AI & ML
- **LangChain**: AI 워크플로우 오케스트레이션
- **LangGraph**: 복잡한 AI 에이전트 워크플로우
- **AWS Bedrock**: Claude 3.5 Sonnet 모델

### AWS Services
- **Bedrock**: AI 모델 서비스
- **Cognito**: 사용자 인증
- **S3**: 파일 저장소
- **Polly**: 텍스트 음성 변환

### Database
- **MySQL**: 메인 데이터베이스
- **SQLAlchemy**: ORM
- **Redis**: 캐시 및 세션 관리

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/AWS-CloudSchool/tissue-backend.git
cd tissue-backend

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 AWS 자격증명 등 설정
```

### 2. Docker로 실행 (권장)

```bash
# Docker 이미지 빌드
docker build -t youtube-analyzer .

# 컨테이너 실행
docker run -p 8000:8000 --env-file .env youtube-analyzer
```

### 3. 로컬 개발 환경

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 테이블 생성
python -m app.create_tables

# 데이터베이스 연결 테스트 (선택사항)
python test_db_connection.py

# 애플리케이션 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📋 환경변수 설정

`.env` 파일에 다음 변수들을 설정하세요:

### 데이터베이스 설정

AWS RDS MySQL을 사용하는 경우 다음 설정이 필요합니다:

1. **AWS RDS MySQL 인스턴스 생성** (자세한 내용은 `DATABASE_SETUP.md` 참조)
2. **환경 변수 설정**:

```env
# 데이터베이스
DATABASE_URL=mysql+pymysql://user:password@localhost/dbname
```

### 기타 설정

```env
# AWS 설정
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-west-2
AWS_S3_BUCKET=your_bucket_name

# Bedrock 설정
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_KB_ID=your_knowledge_base_id

# Cognito 설정
COGNITO_USER_POOL_ID=your_user_pool_id
COGNITO_CLIENT_ID=your_client_id

# API 키
VIDCAP_API_KEY=your_vidcap_api_key
YOUTUBE_API_KEY=your_youtube_api_key
```

## 📚 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 주요 엔드포인트

### 인증
- `POST /auth/signup` - 회원가입
- `POST /auth/login` - 로그인
- `GET /auth/me` - 사용자 정보

### YouTube 분석
- `POST /analyze/youtube` - YouTube 영상 분석 시작
- `GET /analyze/job/{job_id}` - 분석 진행률 확인
- `GET /analyze/report/{job_id}` - 분석 결과 조회

### 챗봇
- `POST /chat/message` - 챗봇과 대화
- `GET /chat/history` - 대화 기록

### 검색
- `GET /search/youtube` - YouTube 검색
- `GET /search/videos` - 비디오 검색

### 파일 관리
- `POST /s3/upload` - 파일 업로드
- `GET /s3/download/{file_key}` - 파일 다운로드

## 🧪 테스트

```bash
# 테스트 실행
pytest

# 커버리지 포함 테스트
pytest --cov=app tests/
```

## 🔄 개발 워크플로우

### Git Flow 전략
```bash
main (프로덕션)
├── dev (개발)
    ├── feature/docker-setup
    ├── feature/core-config
    ├── feature/analyze-workflow
    ├── feature/search-service
    ├── feature/chatbot-service
    ├── feature/audio-service
    └── feature/s3-service
```

### 새 기능 개발
```bash
# dev 브랜치에서 새 기능 브랜치 생성
git checkout dev
git checkout -b feature/new-feature

# 개발 완료 후 dev에 병합
git checkout dev
git merge feature/new-feature

# 최종적으로 main에 병합
git checkout main
git merge dev
```

## 📊 모니터링

- **로그**: 구조화된 로깅 시스템
- **헬스체크**: `/health` 엔드포인트
- **메트릭**: 성능 및 사용량 추적

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🆘 지원

문제가 발생하거나 질문이 있으시면:

- **Issues**: GitHub Issues 탭에서 버그 리포트 또는 기능 요청
- **Documentation**: API 문서 참조
- **Contact**: 프로젝트 관리자에게 연락

---

**Made with ❤️ by AWS CloudSchool Team**