import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError
from openapi_spec_validator import validate_v3_spec # For OpenAPI 3.x validation

# --- Pydantic Models for API Structure ---

class Parameter(BaseModel):
    name: str
    in_: str = Field(..., alias="in")
    description: Optional[str] = None
    required: bool = False
    schema_: Dict[str, Any] = Field(..., alias="schema")

class RequestBody(BaseModel):
    content: Dict[str, Any]
    required: bool = False

class Response(BaseModel):
    description: str
    content: Optional[Dict[str, Any]] = None

class Operation(BaseModel):
    operationId: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Parameter] = []
    requestBody: Optional[RequestBody] = None
    responses: Dict[str, Response] # e.g., "200", "400"

class PathItem(BaseModel):
    get: Optional[Operation] = None
    post: Optional[Operation] = None
    put: Optional[Operation] = None
    delete: Optional[Operation] = None
    # Add other HTTP methods as needed

class APIEndpoint(BaseModel):
    path: str
    methods: PathItem

class APISpec(BaseModel):
    openapi: str
    info: Dict[str, Any]
    paths: Dict[str, PathItem]
    components: Optional[Dict[str, Any]] = None

# --- Parser Class ---

class OpenAPIParser:
    def __init__(self, spec_path: Path):
        self.spec_path = spec_path
        self.raw_spec: Dict[str, Any] = {}
        self.api_spec: Optional[APISpec] = None

    def _load_spec(self) -> Dict[str, Any]:
        """Loads the OpenAPI/Swagger specification from the given path."""
        if not self.spec_path.exists():
            raise FileNotFoundError(f"API specification file not found at {self.spec_path}")

        with open(self.spec_path, 'r', encoding='utf-8') as f:
            if self.spec_path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            elif self.spec_path.suffix == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {self.spec_path.suffix}. Must be .yaml, .yml, or .json.")

    def parse(self) -> APISpec:
        """Parses and validates the OpenAPI specification."""
        self.raw_spec = self._load_spec()

        try:
            # Validate against OpenAPI 3.x schema
            validate_v3_spec(self.raw_spec)
            print(f"OpenAPI spec at {self.spec_path} is valid.")
        except Exception as e:
            print(f"Warning: OpenAPI spec validation failed: {e}")
            # Depending on strictness, you might want to raise this error

        try:
            self.api_spec = APISpec(**self.raw_spec)
            print("API specification successfully parsed into Pydantic models.")
            return self.api_spec
        except ValidationError as e:
            raise ValueError(f"Error parsing API spec into Pydantic models: {e}")

    def get_endpoints(self) -> List[APIEndpoint]:
        """Extracts and returns a list of API endpoints with their methods."""
        if not self.api_spec:
            raise ValueError("API specification not parsed yet. Call .parse() first.")

        endpoints: List[APIEndpoint] = []
        for path, path_item in self.api_spec.paths.items():
            endpoints.append(APIEndpoint(path=path, methods=path_item))
        return endpoints

if __name__ == '__main__':
    # Example usage (assuming an example.yaml or example.json exists)
    # For a real run, you'd provide an actual OpenAPI spec file.
    # Create a dummy spec file for demonstration
    dummy_spec_content = """
    openapi: 3.0.0
    info:
      title: Dummy API
      version: 1.0.0
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
                        name:                          type: string
        post:
          summary: Create a new user
          operationId: createUser
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    name:
                      type: string
                  required:
                    - name
          responses:
            '201':
              description: User created
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      id:
                        type: integer
                      name:
                        type: string
    """
    dummy_spec_path = Path("D:\\cshi\\ai_api_agent\\example_api_spec.yaml")
    with open(dummy_spec_path, "w", encoding="utf-8") as f:
        f.write(dummy_spec_content)

    try:
        parser = OpenAPIParser(dummy_spec_path)
        parsed_spec = parser.parse()
        endpoints = parser.get_endpoints()

        print("\n--- Parsed Endpoints ---")
        for endpoint in endpoints:
            print(f"Path: {endpoint.path}")
            if endpoint.methods.get:
                print(f"  GET: {endpoint.methods.get.summary} (Operation ID: {endpoint.methods.get.operationId})")
            if endpoint.methods.post:
                print(f"  POST: {endpoint.methods.post.summary} (Operation ID: {endpoint.methods.post.operationId})")
            # You can inspect the structure more deeply here
            # print(endpoint.json(indent=2))

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
    finally:
        # Clean up dummy spec file
        if dummy_spec_path.exists():
            dummy_spec_path.unlink()
