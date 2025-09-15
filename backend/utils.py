from functools import wraps
import logging
import traceback
from flask import jsonify, current_app
from config import StatusCode, Messages
from mysql.connector import Error as MySQLError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def api_response(success=True, message="", data=None, status_code=StatusCode.SUCCESS):
    response = {
        "success": success,
        "message": message,
        "data": data
    }
    if not success:
        logger.error(f"API Error: {message}")
    return jsonify(response), status_code

def handle_api_error(error_type="QUERY_ERROR"):
    """
    API错误处理装饰器
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except MySQLError as e:
                logger.error(f"Database error in {f.__name__}: {str(e)}")
                logger.debug(traceback.format_exc())
                return api_response(
                    success=False,
                    message=f"数据库错误: {str(e)}",
                    status_code=StatusCode.INTERNAL_ERROR
                )
            except ValueError as e:
                logger.warning(f"Validation error in {f.__name__}: {str(e)}")
                return api_response(
                    success=False,
                    message=str(e),
                    status_code=StatusCode.BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
                logger.error(traceback.format_exc())
                message = getattr(Messages, error_type, Messages.QUERY_ERROR)
                return api_response(
                    success=False,
                    message=f"{message}: {str(e)}",
                    status_code=StatusCode.INTERNAL_ERROR
                )
        return decorated_function
    return decorator
