from main import run_agent
from src.config import Config
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Ensure environment variables are loaded if this script is run directly
    # (though main.py already calls load_dotenv)
    # from dotenv import load_dotenv
    # load_dotenv()

    # Create a dummy API spec if it doesn't exist for easy testing
    dummy_spec_created = False
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
        dummy_spec_created = True

    try:
        logger.info(f"Running agent with API Spec: {Config.API_SPEC_PATH} and Base URL: {Config.API_BASE_URL}")
        run_agent(Config.API_SPEC_PATH, Config.API_BASE_URL)
        logger.info("Agent execution finished.")
    except Exception as e:
        logger.error(f"Error during agent execution: {e}", exc_info=True)
    finally:
        if dummy_spec_created and Config.API_SPEC_PATH.exists():
            Config.API_SPEC_PATH.unlink()
            logger.info(f"Cleaned up dummy API spec at {Config.API_SPEC_PATH}.")
