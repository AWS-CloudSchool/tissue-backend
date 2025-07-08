"""
Prometheus 메트릭 정의
monitoring 모듈 내에서 중앙 관리
"""

from prometheus_client import Counter, Histogram, Gauge

# YouTube 작업 메트릭
youtube_job_total = Counter(
    'youtube_jobs_total',
    'Total number of YouTube analysis jobs',
    ['status']
)

youtube_job_duration = Histogram(
    'youtube_job_duration_seconds',
    'Time spent on YouTube job stages',
    ['stage']
)

# LLM 호출 메트릭
llm_call_total = Counter(
    'llm_calls_total',
    'Total number of LLM calls',
    ['agent', 'status']
)

llm_call_duration = Histogram(
    'llm_call_duration_seconds',
    'Time spent on LLM calls',
    ['agent']
)

# API 요청 메트릭
api_request_count = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'Time spent on API requests',
    ['method', 'endpoint', 'status_code']
)

# 시스템 메트릭
cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('memory_usage_percent', 'Memory usage percentage')
disk_usage = Gauge('disk_usage_percent', 'Disk usage percentage')

# 활성 작업 수
active_jobs = Gauge('active_jobs_count', 'Number of currently active jobs')

# S3 업로드 메트릭
s3_uploads_total = Counter(
    's3_uploads_total',
    'Total number of S3 uploads',
    ['status']
)

s3_upload_duration = Histogram(
    's3_upload_duration_seconds',
    'Time spent on S3 uploads'
)