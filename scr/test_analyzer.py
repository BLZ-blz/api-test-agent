from typing import Any, Dict, Optional, List
from pydantic import BaseModel
from src.test_case_generator import TestCaseExpectedResponse
from src.test_executor import TestExecutionResult
from jsonschema import validate, ValidationError
import json

# --- Pydantic Models for Test Analysis Results ---

class TestAnalysisResult(BaseModel):
    test_case_name: str
    passed: bool
    failure_reason: Optional[str] = None
    execution_details: TestExecutionResult
    expected_response: TestCaseExpectedResponse

# --- Test Analyzer Class ---

class TestAnalyzer:
    def analyze_result(
        self,
        test_case_name: str,
        expected_response: TestCaseExpectedResponse,
        execution_result: TestExecutionResult
    ) -> TestAnalysisResult:
        """
        Analyzes the test execution result against the expected response.
        """
        passed = True
        failure_reasons: List[str] = []

        if not execution_result.success:
            passed = False
            failure_reasons.append(f"Request execution failed: {execution_result.error_message}")
            return TestAnalysisResult(
                test_case_name=test_case_name,
                passed=passed,
                failure_reason="; ".join(failure_reasons),
                execution_details=execution_result,
                expected_response=expected_response
            )

        # 1. Check status code
        if execution_result.response_status_code != expected_response.status_code:
            passed = False
            failure_reasons.append(
                f"Status code mismatch. Expected: {expected_response.status_code}, "
                f"Got: {execution_result.response_status_code}"
            )

        # 2. Check JSON Schema (if provided)
        if expected_response.json_schema and execution_result.response_body is not None:
            try:
                # Ensure response_body is parsed as JSON if it's a string
                body_to_validate = execution_result.response_body
                if isinstance(body_to_validate, str):
                    try:
                        body_to_validate = json.loads(body_to_validate)
                    except json.JSONDecodeError:
                        passed = False
                        failure_reasons.append("Expected JSON response but body was not valid JSON.")

                if passed: # Only validate if body was successfully parsed as JSON
                    validate(instance=body_to_validate, schema=expected_response.json_schema)
            except ValidationError as e:
                passed = False
                failure_reasons.append(f"JSON schema validation failed: {e.message}")
            except Exception as e:
                passed = False
                failure_reasons.append(f"An error occurred during JSON schema validation: {e}")

        # 3. Check for specific text in response body (if provided)
        if expected_response.contains_text and execution_result.response_body is not None:
            if expected_response.contains_text not in str(execution_result.response_body):
                passed = False
                failure_reasons.append(f"Response body does not contain expected text: '{expected_response.contains_text}'")

        return TestAnalysisResult(
            test_case_name=test_case_name,
            passed=passed,
            failure_reason="; ".join(failure_reasons) if not passed else None,
            execution_details=execution_result,
            expected_response=expected_response
        )

if __name__ == '__main__':
    # Dummy data for demonstration
    analyzer = TestAnalyzer()

    # --- Test Case 1: Success ---
    expected_success = TestCaseExpectedResponse(
        status_code=200,
        json_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"]
        },
        contains_text="success"
    )
    execution_success = TestExecutionResult(
        request_method="GET",
        request_url="http://example.com/api/test",
        response_status_code=200,
        response_body={"message": "Operation success!"},
        response_time_ms=50.0,
        success=True
    )
    result_success = analyzer.analyze_result("Successful Test", expected_success, execution_success)
    print(f"\n--- Test Case: Successful Test ---")
    print(f"Passed: {result_success.passed}")
    print(f"Reason: {result_success.failure_reason}")

    # --- Test Case 2: Status Code Mismatch ---
    expected_status_mismatch = TestCaseExpectedResponse(status_code=201)
    execution_status_mismatch = TestExecutionResult(
        request_method="POST",
        request_url="http://example.com/api/create",
        response_status_code=200, # Expected 201, got 200
        response_body={"id": 1},
        response_time_ms=100.0,
        success=True
    )
    result_status_mismatch = analyzer.analyze_result("Status Code Mismatch", expected_status_mismatch, execution_status_mismatch)
    print(f"\n--- Test Case: Status Code Mismatch ---")
    print(f"Passed: {result_status_mismatch.passed}")
    print(f"Reason: {result_status_mismatch.failure_reason}")

    # --- Test Case 3: JSON Schema Validation Failure ---
    expected_schema_fail = TestCaseExpectedResponse(
        status_code=200,
        json_schema={
            "type": "object",
            "properties": {"data": {"type": "string"}},
            "required": ["data"]
        }
    )
    execution_schema_fail = TestExecutionResult(
        request_method="GET",
        request_url="http://example.com/api/data",
        response_status_code=200,
        response_body={"info": "some data"}, # 'data' field is missing
        response_time_ms=75.0,
        success=True
    )
    result_schema_fail = analyzer.analyze_result("JSON Schema Fail", expected_schema_fail, execution_schema_fail)
    print(f"\n--- Test Case: JSON Schema Fail ---")
    print(f"Passed: {result_schema_fail.passed}")
    print(f"Reason: {result_schema_fail.failure_reason}")

    # --- Test Case 4: Text Not Found ---
    expected_text_fail = TestCaseExpectedResponse(
        status_code=200,
        contains_text="expected_phrase"
    )
    execution_text_fail = TestExecutionResult(
        request_method="GET",
        request_url="http://example.com/api/message",
        response_status_code=200,
        response_body="This is some response.",
        response_time_ms=60.0,
        success=True
    )
    result_text_fail = analyzer.analyze_result("Text Not Found", expected_text_fail, execution_text_fail)
    print(f"\n--- Test Case: Text Not Found ---")
    print(f"Passed: {result_text_fail.passed}")
    print(f"Reason: {result_text_fail.failure_reason}")

    # --- Test Case 5: Request Execution Failure ---
    expected_req_fail = TestCaseExpectedResponse(status_code=200)
    execution_req_fail = TestExecutionResult(
        request_method="GET",
        request_url="http://invalid.url",
        response_time_ms=0.0,
        success=False,
        error_message="DNS lookup failed"
    )
    result_req_fail = analyzer.analyze_result("Request Execution Failure", expected_req_fail, execution_req_fail)
    print(f"\n--- Test Case: Request Execution Failure ---")
    print(f"Passed: {result_req_fail.passed}")
    print(f"Reason: {result_req_fail.failure_reason}")
