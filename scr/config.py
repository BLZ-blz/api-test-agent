import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    # Base URL for the API to be tested
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

    # Path to the OpenAPI/Swagger specification file
    # Default to a dummy path for example, users should update this
    API_SPEC_PATH: Path = Path(os.getenv("API_SPEC_PATH", "./example_api_spec.yaml"))

    # OpenAI API Key (or other LLM provider API key)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Directory for templates
    TEMPLATES_DIR: Path = Path(__file__).parent.parent / "templates"

    # Directory for generated reports and documentation
    REPORTS_DIR: Path = Path(__file__).parent.parent / "reports"

    # LLM Model Name
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo")

    # LLM Temperature for creativity (0.0 - 1.0)
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", 0.7))

    # Ensure reports directory exists
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        if not cls.API_SPEC_PATH.exists():
            print(f"Warning: API_SPEC_PATH '{cls.API_SPEC_PATH}' does not exist. Please update .env or config.py")
        if not cls.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY is not set. LLM functionality may not work.")
        if not cls.TEMPLATES_DIR.exists():
            raise FileNotFoundError(f"Templates directory not found at {cls.TEMPLATES_DIR}")

Config.validate()
