import logging
from pathlib import Path
from typing import List, Optional

from src.config import Config
from src.parser import OpenAPIParser, APISpec, APIEndpoint, Operation
from src.test_case_generator import AITestCaseGenerator, TestCase
from src.test_executor import TestExecutor
from src.test_analyzer import TestAnalyzer, TestAnalysisResult
from src.report_generator import ReportGenerator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_agent(api_spec_path: Path, api_base_url: str):
    """
    Orchestrates the entire AI API Agent workflow.
    """
    logger.info("Starting AI API Agent workflow...")

    # 1. Initialize components
    parser = OpenAPIParser(api_spec_path)
    test_case_generator = AITestCaseGenerator(
        model_name=Config.LLM_MODEL_NAME,
        temperature=Config.LLM_TEMPERATURE
    )
    test_executor = TestExecutor(base_url=api_base_url)
    test_analyzer = TestAnalyzer()
    report_generator = ReportGenerator(
        template_dir=Config.TEMPLATES_DIR,
        output_dir=Config.REPORTS_DIR
    )

    all_test_analysis_results: List[TestAnalysisResult] = []
    api_spec: Optional[APISpec] = None

    try:
        # 2. Parse API Specification
        logger.info(f"Parsing API specification from {api_spec_path}...")
        api_spec = parser.parse()
        endpoints = parser.get_endpoints()
        logger.info(f"Found {len(endpoints)} API endpoints.")

        # Generate API documentation immediately after parsing
        report_generator.generate_api_docs(api_spec, output_filename="api_documentation.md")

        # 3. Iterate through endpoints and generate/execute/analyze test cases
        for endpoint in endpoints:
            logger.info(f"Processing endpoint: {endpoint.path}")
            for method, operation_dict in endpoint.methods.model_dump().items():
                if operation_dict: # Ensure operation is not None
                    operation = Operation(**operation_dict) # Re-parse into Pydantic model for easier access
                    logger.info(f"  Generating test cases for {method.upper()} {endpoint.path}...")

                    # Extract relevant info for test case generation
                    request_body_schema = operation.requestBody.content.get('application/json', {}).get('schema', {}) if operation.requestBody else {}
                    parameters = operation.parameters
                    responses = operation.responses

                    generated_test_cases: List[TestCase] = test_case_generator.generate_test_cases(
                        api_path=endpoint.path,
                        http_method=method.upper(),
                        operation_summary=operation.summary if operation.summary else 'N/A',
                        request_body_schema=request_body_schema,
                        parameters=[p.model_dump(by_alias=True) for p in parameters], # Convert Parameter Pydantic models to dicts for LLM input
                        responses={k: v.model_dump(by_alias=True) for k, v in responses.items()} # Convert Response Pydantic models to dicts for LLM input
                    )
                    logger.info(f"    Generated {len(generated_test_cases)} test cases for {method.upper()} {endpoint.path}.")

                    for test_case in generated_test_cases:
                        logger.info(f"      Executing test case: {test_case.name} ({test_case.scenario_type})")
                        # Adjust path for execution if it contains path parameters placeholder
                        request_path_for_execution = test_case.request.path
                        if test_case.request.path_params:
                            for param_name, param_value in test_case.request.path_params.items():
                                request_path_for_execution = request_path_for_execution.replace(f"{{{param_name}}}", str(param_value))
                            test_case.request.path = request_path_for_execution # Update for executor

                        execution_result = test_executor.execute_request(test_case.request)
                        analysis_result = test_analyzer.analyze_result(
                            test_case_name=test_case.name,
                            expected_response=test_case.expected_response,
                            execution_result=execution_result
                        )
                        all_test_analysis_results.append(analysis_result)

                        if analysis_result.passed:
                            logger.info(f"        Test case '{test_case.name}' PASSED.")
                        else:
                            logger.warning(f"        Test case '{test_case.name}' FAILED: {analysis_result.failure_reason}")

        # 4. Generate Test Report
        logger.info("Generating final test report...")
        report_generator.generate_test_report(all_test_analysis_results, output_filename="test_report.html")

        logger.info("AI API Agent workflow completed successfully!")

    except FileNotFoundError as e:
        logger.error(f"Configuration Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during agent execution: {e}", exc_info=True)


if __name__ == "__main__":
    # Example usage:
    # Ensure your .env file has API_SPEC_PATH and API_BASE_URL defined.
    # e.g., API_SPEC_PATH=./path/to/your/openapi.yaml
    #       API_BASE_URL=http://localhost:8080

    # For demonstration, create a dummy spec file if it doesn't exist
    if not Config.API_SPEC_PATH.exists():
        dummy_spec_content = """
        openapi: 3.0.0
        info:
          title: Dummy API Service
          version: 1.0.0
          description: A simple dummy API for demonstration purposes.
        paths:
          /hello:
            get:
              summary: Say hello
              operationId: sayHello
              responses:
                '200':
                  description: A greeting message
                  content:
                    application/json:
                      schema:
                        type: object
                        properties:
                          message:
                            type: string
          /users/{userId}:
            get:
              summary: Get user by ID
              operationId: getUserById
              parameters:
                - name: userId
                  in: path
                  required: true
                  schema:
                    type: integer
                    format: int64
              responses:
                '200':
                  description: User details
                  content:
                    application/json:
                      schema:
                        type: object
                        properties:
                          id:
                            type: integer
                          name:
                            type: string
                '404':
                  description: User not found
        """
        with open(Config.API_SPEC_PATH, "w", encoding="utf-8") as f:
            f.write(dummy_spec_content)
        logger.info(f"Created a dummy API spec at {Config.API_SPEC_PATH} for demonstration.")
        # If running this, remember to clean up dummy_spec_path after testing.

    try:
        run_agent(Config.API_SPEC_PATH, Config.API_BASE_URL)
    finally:
        if dummy_spec_created and Config.API_SPEC_PATH.exists():
            Config.API_SPEC_PATH.unlink()
            logger.info(f"Cleaned up dummy API spec at {Config.API_SPEC_PATH}.")

    # To run periodically, you can use APScheduler:
    # from apscheduler.schedulers.blocking import BlockingScheduler
    # scheduler = BlockingScheduler()
    # scheduler.add_job(run_agent, 'interval', minutes=60, args=[Config.API_SPEC_PATH, Config.API_BASE_URL])
    # logger.info("Agent scheduled to run every 60 minutes.")
    # scheduler.start()
