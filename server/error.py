from starlette.responses import JSONResponse


class MCPError(Exception):
    error_message: str
    code: int

    def __init__(self, message: str, code: int = 400):
        """
        Initialize MCP error exception

        Args:
            message: Error message to display
            code: HTTP status code (default: 400)
        """
        self.error_message = message
        self.code = code

    def as_response(self) -> dict:
        """
        Convert error to response dictionary

        Returns:
            dict: Error response with status and message
        """
        return {
            "status": "error",
            "error": self.error_message,
        }

    def as_starlette_response(self) -> JSONResponse:
        """
        Convert error to Starlette JSON response

        Returns:
            JSONResponse: Starlette response with error status and content
        """
        return JSONResponse(status_code=self.code, content=self.as_response())
