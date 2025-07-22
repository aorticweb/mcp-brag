import traceback

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from common.log import get_logger
from server.error import MCPError

logger = get_logger(__name__)


class MCPErrorMiddleware(BaseHTTPMiddleware):
    """Middleware to catch and handle MCPError exceptions in custom routes only.
    This does not apply to tool calls.
    By convention, all custom routes should be prefixed with "/manual/".
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except MCPError as e:
            if e.code == 500:
                logger.error(f"Internal server error: {e.error_message}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
            return e.as_starlette_response()
        except Exception as e:
            logger.error(f"Internal server error: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return MCPError("Unexpected error server error", 500).as_starlette_response()
