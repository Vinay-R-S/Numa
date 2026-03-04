
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Settings(BaseModel):
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "") # Optional depending on socket mode, but good to have
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MONITOR_CHANNELS: str = os.getenv("MONITOR_CHANNELS", "")
    CHECK_INTERVAL_MINUTES: int = int(os.getenv("CHECK_INTERVAL_MINUTES", "15"))
    NOTIFICATION_USER_ID: str = os.getenv("NOTIFICATION_USER_ID", "")
    
    # Email Settings
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_RECIPIENT: str = os.getenv("EMAIL_RECIPIENT", "")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    
    def validate_keys(self):
        if not self.SLACK_BOT_TOKEN.startswith("xoxb-"):
            logger.error("Invalid SLACK_BOT_TOKEN. Must start with 'xoxb-'.")
            raise ValueError("Invalid SLACK_BOT_TOKEN")
            
        if not self.GROQ_API_KEY.startswith("gsk_"):
            logger.error("Invalid GROQ_API_KEY. Must start with 'gsk_'.")
            raise ValueError("Invalid GROQ_API_KEY")

try:
    settings = Settings()
    settings.validate_keys()
except ValueError as e:
    logger.critical(f"Configuration validation failed: {e}")
    # We don't exit here to allow for testing, but in production this should probably crash
