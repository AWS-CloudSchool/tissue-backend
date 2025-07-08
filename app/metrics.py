app/metrics.py (새 파일)
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
import psutil

# API 메트릭
api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint', 'status_code']
)

api_request_count = Counter(
    'api_requests_total', 
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

# YouTube 처리 메트릭
youtube_job_total = Counter(
    'youtube_jobs_total',
    'YouTube jobs by status', 
    ['status']  # completed, failed
)

youtube_job_duration = Histogram(
    'youtube_job_duration_seconds',
    'YouTube job processing time',
    ['stage']  # caption, summary, report
)

# LLM 메트릭
llm_call_total = Counter(
    'llm_calls_total',
    'LLM API calls',
    ['agent', 'status']  # success, error
)

llm_call_duration = Histogram(
    'llm_call_duration_seconds', 
    'LLM call duration',
    ['agent']
)

# 시스템 메트릭
cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage')
memory_usage = Gauge('system_memory_usage_percent', 'Memory usage')

def update_system_metrics():
    """시스템 메트릭 업데이트"""
    cpu_usage.set(psutil.cpu_percent())
    memory_usage.set(psutil.virtual_memory().percent)
