import datetime
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader
import json

from src.parser import APISpec
from src.test_analyzer import TestAnalysisResult

# --- Pydantic Models for Report Summary ---

class ReportSummary(BaseModel):
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float

# --- Report Generator Class ---

class ReportGenerator:
    def __init__(self, template_dir: Path, output_dir: Path):
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        output_dir.mkdir(parents=True, exist_ok=True) # Ensure output directory exists

        # Add json filter to Jinja2 environment for pretty printing JSON in templates
        self.env.filters['tojson'] = lambda obj, indent=None: json.dumps(obj, indent=indent, ensure_ascii=False)


    def generate_api_docs(self, api_spec: APISpec, output_filename: str = "api_documentation.md"):
        """
        Generates API documentation from the parsed APISpec.
        """
        template = self.env.get_template("api_docs_template.md")
        rendered_content = template.render(spec=api_spec)
        output_path = self.output_dir / output_filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_content)
        print(f"API documentation generated at: {output_path}")
        return output_path

    def generate_test_report(self, test_results: List[TestAnalysisResult], output_filename: str = "test_report.html"):
        """
        Generates a test report from a list of TestAnalysisResult.
        """
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.passed)
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0

        report_summary = ReportSummary(
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            pass_rate=round(pass_rate, 2)
        )

        template = self.env.get_template("test_report_template.html")
        rendered_content = template.render(report_summary=report_summary, test_results=test_results)
        output_path = self.output_dir / output_filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_content)
        print(f"Test report generated at: {output_path}")
        return output_path

if __name__ == '__main__':
    from src.parser import OpenAPIParser, APISpec
    from src.test_executor import TestExecutionResult
    from src.test_case_generator import TestCaseExpectedResponse

    # Setup paths
    base_dir = Path(__file__).parent.parent
    template_dir = base_dir / "templates"
    output_dir = base_dir / "reports"
    output_dir.mkdir(exist_ok=True)

    generator = ReportGenerator(template_dir, output_dir)

    # --- Dummy APISpec for API Docs ---
    dummy_spec_content = """
    openapi: 3.0.0
    info:
      title: Dummy API
      version: 1.0.0
      description: This is a dummy API for demonstration purposes.
    paths:
      /users:
        get:
          summary: Get all users
          operationId: getUsers
          responses:
            '200':
              description: A list of users
              content:
                application/json:
                  schema:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: integer
                        name:
                          type: string
      /products/{productId}:
        get:
          summary: Get product by ID
          operationId: getProductById
          parameters:
            - name: productId
              in: path
              required: true
              schema:
                type: integer
          responses:
            '200':
              description: Product details
    """
    dummy_spec_path = output_dir / "dummy_api_spec.yaml"
    with open(dummy_spec_path, "w", encoding="utf-8") as f:
        f.write(dummy_spec_content)

    parser = OpenAPIParser(dummy_spec_path)
    api_spec = parser.parse()

    print("\n--- Generating API Documentation ---")
    doc_path = generator.generate_api_docs(api_spec)

    # Clean up dummy spec file
    dummy_spec_path.unlink()


    # --- Dummy TestAnalysisResults for Test Report ---
    expected_success = TestCaseExpectedResponse(
        status_code=200,
        json_schema={"type": "object", "properties": {"message": {"type": "string"}}},
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
    result_success = TestAnalysisResult(
        test_case_name="Successful Test Case",
        passed=True,
        execution_details=execution_success,
        expected_response=expected_success
    )

    expected_fail = TestCaseExpectedResponse(status_code=201)
    execution_fail = TestExecutionResult(
        request_method="POST",
        request_url="http://example.com/api/create",
        response_status_code=200,
        response_body={"id": 1},
        response_time_ms=100.0,
        success=True
    )
    result_fail = TestAnalysisResult(
        test_case_name="Failed Status Code Test",
        passed=False,
        failure_reason="Status code mismatch. Expected: 201, Got: 200",
        execution_details=execution_fail,
        expected_response=expected_fail
    )

    test_results_list = [result_success, result_fail]

    print("\n--- Generating Test Report ---")
    report_path = generator.generate_test_report(test_results_list)

    print("\nDemonstration complete. Check the 'reports' directory for generated files.")
