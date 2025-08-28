import os
import logging
import json
from dotenv import load_dotenv
from lib.notion_manager import NotionManager
from lib.jira_manager import JiraManager
from lib.slack_manager import SlackManager
from lib.logger import setup_logger

# Initialize logger configuration
setup_logger()

# Load environment variables from .env file
load_dotenv()

# Environment variables
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_USER_NAME = os.getenv("JIRA_USER_NAME")

# Parse JIRA_USERS from JSON string
JIRA_USERS_JSON = os.getenv("JIRA_USERS", "[]")
try:
    JIRA_USERS = json.loads(JIRA_USERS_JSON)
except (json.JSONDecodeError, ImportError) as e:
    logging.error(f"Failed to parse JIRA_USERS JSON: {e}")
    JIRA_USERS = []

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

TYPES_DATABASE_ID = os.getenv("TYPES_DATABASE_ID")

# Slack Configuration
SLACK_TOKEN = os.getenv("SLACK_TOKEN")

def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting SU Report Bot")
    
    # Initialize managers
    jira_manager = JiraManager(JIRA_USERS, JIRA_USER_NAME, JIRA_API_TOKEN)
    notion_manager = NotionManager(
        notion_token=NOTION_TOKEN,
        database_id=DATABASE_ID,
        jira_user_name=JIRA_USER_NAME,
        jira_token=JIRA_API_TOKEN
    )
    slack_manager = SlackManager()

    # # Get jira data
    jira_data = jira_manager.get_tickets()
    jira_data = jira_manager.filter_data(jira_data)

    # Sync status from Jira and update notion
    notion_manager.update(jira_data)

    # Get all records from Notion for report generation
    notion_records = notion_manager.get_all_records()
    
    # Send reports for all users
    slack_manager.send_report(jira_data, notion_records, JIRA_USERS, SLACK_TOKEN)

    logger.info("SU Report Bot completed")

if __name__ == "__main__":
    main()
