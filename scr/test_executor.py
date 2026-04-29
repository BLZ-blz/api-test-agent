import requests
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel
from src.test_case_generator import TestCaseRequest # Import the request model

# --- Pydantic Models for Test Execution Results ---

class TestExecutionResult(BaseModel):
    request_method: str
    request_url: str
    request_headers: Optional[Dict[str, str]] = None
    request_body: Optional[Any] = None
    response_status_code: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_body: Optional[Any] = None
    response_time_ms: float
    success: bool = False
    error_message: Optional[str] = None

# --- Test Executor Class ---

class TestExecutor:
    def __init__(self, base_url: str):
        if not base_url.endswith('/'):
            base_url += '/'
        self.base_url = base_url

    def execute_request(self, test_case_request: TestCaseRequest) -> TestExecutionResult:
        """
        Executes a single API request based on the provided TestCaseRequest.
        """
        full_url = self.base_url.rstrip('/') + test_case_request.path

        # Handle path parameters if present
        if test_case_request.path_params:
            for param, value in test_case_request.path_params.items():
                full_url = full_url.replace(f"{{{param}}}", str(value))

        headers = test_case_request.headers or {}
        params = test_case_request.query_params
        json_body = test_case_request.body if test_case_request.body else None
        data_body = None

        start_time = time.time()
        try:
            response = requests.request(
                method=test_case_request.method,
                url=full_url,
                headers=headers,
                params=params,
                json=json_body,
                data=data_body, # Use data for form-encoded or raw body if needed
                timeout=30 # seconds
            )
            response_time_ms = (time.time() - start_time) * 1000

            return TestExecutionResult(
                request_method=test_case_request.method,
                request_url=full_url,
                request_headers=headers,
                request_body=json_body,
                response_status_code=response.status_code,
                response_headers=dict(response.headers),
                response_body=response.json() if response.headers.get('Content-Type') == 'application/json' else response.text,
                response_time_ms=response_time_ms,
                success=True
            )
        except requests.exceptions.Timeout:
            response_time_ms = (time.time() - start_time) * 1000
            return TestExecutionResult(
                request_method=test_case_request.method,
                request_url=full_url,
                request_headers=headers,
                request_body=json_body,
                response_time_ms=response_time_ms,
                success=False,
                error_message="Request timed out."
            )
        except requests.exceptions.RequestException as e:
            response_time_ms = (time.time() - start_time) * 1000
            return TestExecutionResult(
                request_method=test_case_request.method,
                request_url=full_url,
                request_headers=headers,
                request_body=json_body,
                response_time_ms=response_time_ms,
                success=False,
                error_message=f"Request failed: {e}"
            )
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return TestExecutionResult(
                request_method=test_case_request.method,
                request_url=full_url,
                request_headers=headers,
                request_body=json_body,
                response_time_ms=response_time_ms,
                success=False,
                error_message=f"An unexpected error occurred: {e}"
            )

if __name__ == '__main__':
    # Example usage
    # Note: This requires a running API server at http://localhost:8000
    # For demonstration, we'll create a dummy request that would typically go to a real server.
    # To test this fully, you would need a mock server or a real API.

    # Example: Simulating a GET request
    get_request = TestCaseRequest(
        method="GET",
        path="/users/123",
        query_params={"status": "active"},
        headers={"Accept": "application/json"}
    )

    # Example: Simulating a POST request
    post_request = TestCaseRequest(
        method="POST",
        path="/users",
        body={"name": "Test User", "email": "test@example.com"},
        headers={"Content-Type": "application/json"}
    )

    # Replace with your actual API's base URL
    # For local testing, you might use a simple mock server.
    # For now, this will likely result in a connection error if no server is running.
    executor = TestExecutor(base_url="http://localhost:8000")

    print("Executing GET request...")
    get_result = executor.execute_request(get_request)
    print(f"GET Result: {get_result.model_dump_json(indent=2)}")

    print("\nExecuting POST request...")
    post_result = executor.execute_request(post_request)
    print(f"POST Result: {post_result.model_dump_json(indent=2)}")
