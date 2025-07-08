import time
import functools
from app.metrics import youtube_job_total, youtube_job_duration, llm_call_total, llm_call_duration

def track_youtube_job(stage_name):
    """YouTube 작업 추적"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                youtube_job_total.labels(status='completed').inc()
                youtube_job_duration.labels(stage=stage_name).observe(time.time() - start_time)
                return result
            except Exception:
                youtube_job_total.labels(status='failed').inc()
                raise
        return wrapper
    return decorator

def track_llm_call(agent_name):
    """LLM 호출 추적"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                llm_call_total.labels(agent=agent_name, status='success').inc()
                llm_call_duration.labels(agent=agent_name).observe(time.time() - start_time)
                return result
            except Exception:
                llm_call_total.labels(agent=agent_name, status='error').inc()
                raise
        return wrapper
    return decorator