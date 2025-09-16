import os
import json
import logging
from dotenv import load_dotenv
from lib.notion_manager import NotionManager
from lib.slack_manager import SlackManager
from lib.jira_manager import JiraManager
from lib.logger import setup_logger

setup_logger()
load_dotenv()

JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_USER_NAME = os.getenv("JIRA_USER_NAME")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")

JIRA_USERS_JSON = os.getenv("JIRA_USERS", "[]")
try:
    JIRA_USERS = json.loads(JIRA_USERS_JSON)
except (json.JSONDecodeError, TypeError) as e:
    logging.error(f"Failed to parse JIRA_USERS: {e}")
    JIRA_USERS = []

def _format_records(records):
    lines = []
    for record in records:
        ticket_link = f"<{record['jiraUrl']}|{record['jiraId']}>"
        status = record.get("status", "")
        lines.append(f"• {ticket_link} {record['title']} `{status}`")
    return "\n".join(lines)

def _build_report(sprint_names, ongoing, completed):
    message = f"*🏃 Sprint:* {sprint_names}\n\n"
    message += "*🔄 Ongoing:*\n"
    if ongoing:
        message += _format_records(ongoing)
    message += "\n\n*✅ Completed:*\n"
    if completed:
        message += _format_records(completed)
    message += "\n\n*📝 Summary:*\n"
    return message

def send_error_to_slack(error_message: str, slack_manager: SlackManager, slack_token: str):
    """Send error message to Slack"""
    try:
        # Send error to first available user or admin
        if JIRA_USERS and len(JIRA_USERS) > 0:
            admin_user_id = JIRA_USERS[0].get("slack_user_id")
            if admin_user_id:
                error_msg = f"🚨 *Weekly Report Bot Error*\n\n{error_message}"
                slack_manager.send_direct_message(error_msg, admin_user_id, slack_token)
                logging.info("Error notification sent to Slack")
    except Exception as e:
        logging.error(f"Failed to send error notification to Slack: {e}")

def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting Weekly Report Bot")
    
    slack_manager = None
    slack_token = SLACK_TOKEN
    
    try:
        notion_manager = NotionManager(
            notion_token=NOTION_TOKEN,
            database_id=DATABASE_ID,
            jira_user_name=JIRA_USER_NAME,
            jira_token=JIRA_API_TOKEN
        )
        slack_manager = SlackManager()
        jira_manager = JiraManager(JIRA_USERS, JIRA_USER_NAME, JIRA_API_TOKEN)

        # Get Notion records
        logger.info("Fetching Notion records...")
        notion_records = notion_manager.get_all_records()
        logger.info(f"Retrieved {len(notion_records)} Notion records")

        # Get active sprints from Jira
        logger.info("Fetching active sprints from Jira...")
        jira_raw = jira_manager.get_tickets()
        jira_filtered = jira_manager.filter_data(jira_raw)
        active_sprints = slack_manager._extract_active_sprints(jira_filtered)
        logger.info(f"Found {len(active_sprints)} active sprints")

        # Process each user
        logger.info("Processing weekly reports for all users...")
        for user_config in JIRA_USERS:
            owner = user_config.get("name")
            slack_user_id = user_config.get("slack_user_id")
            if not owner or not slack_user_id:
                logger.warning(f"Skipping user {owner} - missing name or slack_user_id")
                continue

            logger.info(f"Processing weekly report for user: {owner}")
            
            user_records = [
                r for r in notion_records
                if r.get("owner") == owner and r.get("sprint") in active_sprints
            ]
            ongoing = [
                r for r in user_records
                if r.get("status") not in ("Done", "Completed", "Closed")
            ]
            completed = [
                r for r in user_records
                if r.get("status") in ("Done", "Completed", "Closed")
            ]

            user_sprints = sorted({r.get("sprint") for r in user_records if r.get("sprint")})
            sprint_names = ", ".join(user_sprints) if user_sprints else ", ".join(sorted(active_sprints))
            message = _build_report(sprint_names, ongoing, completed)
            
            success = slack_manager.send_direct_message(message, slack_user_id, slack_token)
            if success:
                logger.info(f"Weekly report sent successfully to {owner}")
            else:
                logger.warning(f"Failed to send weekly report to {owner}")

        logger.info("Weekly Report Bot completed successfully")

    except Exception as e:
        error_message = f"Error occurred in Weekly Report Bot:\n\n*Error Type:* {type(e).__name__}\n*Error Message:* {str(e)}\n*Timestamp:* {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}"
        
        logger.error(f"Weekly Report Bot failed: {e}", exc_info=True)
        
        # Send error notification to Slack
        if slack_manager and slack_token:
            send_error_to_slack(error_message, slack_manager, slack_token)
        
        # Re-raise the exception to ensure proper exit code
        raise

if __name__ == "__main__":
    main()
