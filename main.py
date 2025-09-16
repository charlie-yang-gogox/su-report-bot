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

def send_error_to_slack(error_message: str, slack_manager: SlackManager, slack_token: str):
    """Send error message to Slack"""
    try:
        # Send error to first available user or admin
        if JIRA_USERS and len(JIRA_USERS) > 0:
            admin_user_id = JIRA_USERS[0].get("slack_user_id")
            if admin_user_id:
                error_msg = f"🚨 *SU Report Bot Error*\n\n{error_message}"
                slack_manager.send_direct_message(error_msg, admin_user_id, slack_token)
                logging.info("Error notification sent to Slack")
    except Exception as e:
        logging.error(f"Failed to send error notification to Slack: {e}")

def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting SU Report Bot")
    
    slack_manager = None
    slack_token = SLACK_TOKEN
    
    try:
        # Initialize managers
        jira_manager = JiraManager(JIRA_USERS, JIRA_USER_NAME, JIRA_API_TOKEN)
        notion_manager = NotionManager(
            notion_token=NOTION_TOKEN,
            database_id=DATABASE_ID,
            jira_user_name=JIRA_USER_NAME,
            jira_token=JIRA_API_TOKEN
        )
        slack_manager = SlackManager()

        # Get jira data
        logger.info("Fetching JIRA data...")
        jira_data = jira_manager.get_tickets()
        jira_data = jira_manager.filter_data(jira_data)
        logger.info(f"Retrieved {len(jira_data)} JIRA tickets")

        # Sync status from Jira and update notion
        logger.info("Syncing JIRA data to Notion...")
        notion_manager.update(jira_data)
        logger.info("Notion sync completed")

        # Get all records from Notion for report generation
        logger.info("Fetching Notion records...")
        notion_records = notion_manager.get_all_records()
        logger.info(f"Retrieved {len(notion_records)} Notion records")
        
        # Send reports for all users
        logger.info("Sending reports to Slack...")
        slack_manager.send_report(jira_data, notion_records, JIRA_USERS, slack_token)
        logger.info("Reports sent successfully")

        logger.info("SU Report Bot completed successfully")

    except Exception as e:
        error_message = f"Error occurred in SU Report Bot:\n\n*Error Type:* {type(e).__name__}\n*Error Message:* {str(e)}\n*Timestamp:* {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}"
        
        logger.error(f"SU Report Bot failed: {e}", exc_info=True)
        
        # Send error notification to Slack
        if slack_manager and slack_token:
            send_error_to_slack(error_message, slack_manager, slack_token)
        
        # Re-raise the exception to ensure proper exit code
        raise

if __name__ == "__main__":
    main()
