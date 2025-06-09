import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get Gemini API key
# Try to get from environment variable first, then fallback to the direct value
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable not set.")
    logger.error("Please create a .env file in the backend directory with your API key.")
    logger.error("Example: GEMINI_API_KEY=your-api-key-here")
elif GEMINI_API_KEY == "your-api-key-here":
    logger.error("GEMINI_API_KEY is set to the default placeholder value.")
    logger.error("Please replace it with a valid API key from https://makersuite.google.com/app/apikey")

# Additional configuration variables can be added here
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
