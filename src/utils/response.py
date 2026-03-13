"""API response wrapper utilities."""
from typing import Any, Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[dict] = None


def success_response(data: Any = None, message: str = None) -> dict:
    """Create a success response.
    
    Args:
        data: The response data
        message: Optional success message
        
    Returns:
        dict: Standard API response
    """
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    return response


def error_response(message: str, code: str = "error", details: Any = None) -> dict:
    """Create an error response.
    
    Args:
        message: Error message
        code: Error code
        details: Optional error details
        
    Returns:
        dict: Standard error API response
    """
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        response["error"]["details"] = details
    return response
