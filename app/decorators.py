import time
import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

def track_youtube_job(stage_name: str):
    """YouTube 작업 추적 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                
                # 메트릭 업데이트
                try:
                    from app.metrics import youtube_job_total, youtube_job_duration
                    youtube_job_total.labels(status='completed').inc()
                    youtube_job_duration.labels(stage=stage_name).observe(time.time() - start_time)
                except ImportError:
                    logger.warning("YouTube 메트릭 모듈을 가져올 수 없습니다")
                except Exception as e:
                    logger.warning(f"YouTube 메트릭 업데이트 실패: {e}")
                
                return result
            except Exception as e:
                # 실패 메트릭 업데이트
                try:
                    from app.metrics import youtube_job_total
                    youtube_job_total.labels(status='failed').inc()
                except:
                    pass
                    
                logger.error(f"YouTube 작업 실패 ({stage_name}): {e}")
                raise
        return wrapper
    return decorator

def track_llm_call(agent_name: str):
    """LLM 호출 추적 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                
                # 성공 메트릭 업데이트
                try:
                    from app.metrics import llm_call_total, llm_call_duration
                    llm_call_total.labels(agent=agent_name, status='success').inc()
                    llm_call_duration.labels(agent=agent_name).observe(time.time() - start_time)
                except ImportError:
                    logger.warning("LLM 메트릭 모듈을 가져올 수 없습니다")
                except Exception as e:
                    logger.warning(f"LLM 메트릭 업데이트 실패: {e}")
                
                return result
            except Exception as e:
                # 실패 메트릭 업데이트
                try:
                    from app.metrics import llm_call_total
                    llm_call_total.labels(agent=agent_name, status='error').inc()
                except:
                    pass
                    
                logger.error(f"LLM 호출 실패 ({agent_name}): {e}")
                raise
        return wrapper
    return decorator

def track_api_performance(endpoint_name: str):
    """API 성능 추적 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                
                # 성공 메트릭 업데이트
                try:
                    from app.metrics import api_request_duration, api_request_count
                    duration = time.time() - start_time
                    api_request_duration.labels(
                        method="POST", 
                        endpoint=endpoint_name, 
                        status_code="200"
                    ).observe(duration)
                    api_request_count.labels(
                        method="POST",
                        endpoint=endpoint_name,
                        status_code="200"
                    ).inc()
                except Exception as e:
                    logger.warning(f"API 메트릭 업데이트 실패: {e}")
                
                return result
            except Exception as e:
                # 실패 메트릭 업데이트
                try:
                    from app.metrics import api_request_count
                    api_request_count.labels(
                        method="POST",
                        endpoint=endpoint_name,
                        status_code="500"
                    ).inc()
                except:
                    pass
                    
                logger.error(f"API 호출 실패 ({endpoint_name}): {e}")
                raise
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                
                # 성공 메트릭 업데이트
                try:
                    from app.metrics import api_request_duration, api_request_count
                    duration = time.time() - start_time
                    api_request_duration.labels(
                        method="GET", 
                        endpoint=endpoint_name, 
                        status_code="200"
                    ).observe(duration)
                    api_request_count.labels(
                        method="GET",
                        endpoint=endpoint_name,
                        status_code="200"
                    ).inc()
                except Exception as e:
                    logger.warning(f"API 메트릭 업데이트 실패: {e}")
                
                return result
            except Exception as e:
                # 실패 메트릭 업데이트
                try:
                    from app.metrics import api_request_count
                    api_request_count.labels(
                        method="GET",
                        endpoint=endpoint_name,
                        status_code="500"
                    ).inc()
                except:
                    pass
                    
                logger.error(f"API 호출 실패 ({endpoint_name}): {e}")
                raise
        
        # 함수가 async인지 확인
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator