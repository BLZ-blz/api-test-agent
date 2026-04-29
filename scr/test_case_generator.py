import os
from pathlib import Path
from typing import Dict, Any, List, Literal, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Load environment variables
load_dotenv()

# --- Pydantic Models for Generated Test Cases ---

class TestCaseRequest(BaseModel):
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    path: str
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, Any]] = None
    path_params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None

class TestCaseExpectedResponse(BaseModel):
    status_code: int
    json_schema: Optional[Dict[str, Any]] = None
    contains_text: Optional[str] = None
    # Add more assertion types as needed

class TestCase(BaseModel):
    name: str
    description: str
    scenario_type: Literal["normal", "edge", "error"]
    request: TestCaseRequest
    expected_response: TestCaseExpectedResponse

# --- Test Case Generator Class ---

class AITestCaseGenerator:
    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.7):
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature, api_key=os.getenv("OPENAI_API_KEY"))
        self.output_parser = JsonOutputParser(pydantic_object=List[TestCase]) # Expecting a list of test cases

        # Define the prompt template
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", """
                 你是一个专业的API测试用例生成助手。
                 你的任务是根据提供的API接口定义，生成针对正常、异常和边界场景的测试用例。
                 每个测试用例应包含请求的详细信息（方法、路径、header、查询参数、路径参数、请求体）和预期的响应（状态码、JSON Schema 或包含文本）。
                 请确保生成的测试用例是 JSON 格式，并且符合以下 Pydantic 模型定义：
                 {format_instructions}
                 """),
                ("human", """
                 请为以下 API 接口定义生成测试用例：
                 API Path: {api_path}
                 HTTP Method: {http_method}
                 Operation Summary: {operation_summary}
                 Request Body Schema: {request_body_schema}
                 Parameters: {parameters}
                 Responses: {responses}

                 请生成至少一个正常场景、一个边界场景和一个异常场景的测试用例。
                 ")
            ]
        )
        self.chain = self.prompt_template | self.llm | self.output_parser

    def generate_test_cases(
        self,
        api_path: str,
        http_method: str,
        operation_summary: str,
        request_body_schema: Dict[str, Any],
        parameters: List[Dict[str, Any]],
        responses: Dict[str, Any]
    ) -> List[TestCase]:
        """
        Generates test cases for a given API endpoint using LLM.
        """
        format_instructions = self.output_parser.get_format_instructions()
        try:
            test_cases = self.chain.invoke({
                "api_path": api_path,
                "http_method": http_method,
                "operation_summary": operation_summary,
                "request_body_schema": json.dumps(request_body_schema) if request_body_schema else "{}",
                "parameters": json.dumps(parameters),
                "responses": json.dumps(responses),
                "format_instructions": format_instructions
            })
            return test_cases
        except Exception as e:
            print(f"Error generating test cases with LLM: {e}")
            return []

if __name__ == '__main__':
    # Example usage with dummy data
    generator = AITestCaseGenerator()

    dummy_request_body_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "age": {"type": "integer"}
        },
        "required": ["name", "email"]
    }

    dummy_parameters = [
        {"name": "user_id", "in": "path", "schema": {"type": "integer"}, "required": True},
        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["active", "inactive"]}, "required": False}
    ]

    dummy_responses = {
        "200": {
            "description": "User details",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "email": {"type": "string"}
                        }
                    }
                }
            }
        },
        "404": {
            "description": "User not found"
        }
    }

    print("Generating test cases for /users/{user_id} POST...")
    test_cases_post = generator.generate_test_cases(
        api_path="/users",
        http_method="POST",
        operation_summary="Create a new user",
        request_body_schema=dummy_request_body_schema,
        parameters=[], # No path or query params for this example, body in request_body_schema
        responses=dummy_responses
    )

    for tc in test_cases_post:
        print(f"\n--- Test Case: {tc.name} ({tc.scenario_type}) ---")
        print(f"Request Method: {tc.request.method}")
        print(f"Request Path: {tc.request.path}")
        print(f"Request Body: {tc.request.body}")
        print(f"Expected Status: {tc.expected_response.status_code}")
        # print(tc.json(indent=2))

    print("\nGenerating test cases for /users/{user_id} GET...")
    test_cases_get = generator.generate_test_cases(
        api_path="/users/{user_id}",
        http_method="GET",
        operation_summary="Get user by ID",
        request_body_schema={},
        parameters=dummy_parameters,
        responses=dummy_responses
    )

    for tc in test_cases_get:
        print(f"\n--- Test Case: {tc.name} ({tc.scenario_type}) ---")
        print(f"Request Method: {tc.request.method}")
        print(f"Request Path: {tc.request.path}")
        print(f"Query Params: {tc.request.query_params}")
        print(f"Path Params: {tc.request.path_params}")
        print(f"Expected Status: {tc.expected_response.status_code}")
        # print(tc.json(indent=2))
