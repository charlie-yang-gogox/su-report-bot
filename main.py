import os
import logging
from dotenv import load_dotenv
from lib.notion_manager import NotionManager
from lib.jira_manager import JiraManager
from lib.logger import setup_logger

# Initialize logger configuration
setup_logger()

# Load environment variables from .env file
load_dotenv()

# Environment variables
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_USER_NAME = os.getenv("JIRA_USER_NAME")
JIRA_USER_IDS = os.getenv("JIRA_USER_IDS")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

TYPES_DATABASE_ID = os.getenv("TYPES_DATABASE_ID")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting SU Report Bot")
    
    # Initialize managers
    jira_manager = JiraManager(JIRA_USER_IDS, JIRA_USER_NAME, JIRA_API_TOKEN)
    notion_manager = NotionManager(
        notion_token=NOTION_TOKEN,
        database_id=DATABASE_ID,
        jira_user_name=JIRA_USER_NAME,
        jira_token=JIRA_API_TOKEN
    )

    # Get jira data
    jira_data = jira_manager.get_tickets()
    jira_data = jira_manager.filter_data(jira_data)

    # Sync status from Jira and update notion
    notion_manager.update(jira_data)

    logger.info("SU Report Bot completed")

if __name__ == "__main__":
    main()
