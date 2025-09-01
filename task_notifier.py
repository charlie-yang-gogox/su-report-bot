import os
import json
import logging
from dotenv import load_dotenv
from lib.notion_manager import NotionManager
from lib.slack_manager import SlackManager
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
        lines.append(f"{ticket_link} *{record['title']}*")
    return "\n".join(lines)

def _build_report(ongoing, completed):
    message = "*Ongoing:*\n"
    if ongoing:
        message += _format_records(ongoing)
    message += "\n\n*Completed:*\n"
    if completed:
        message += _format_records(completed)
    message += "\n\n*Summary:*\n"
    return message

def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting Notion task notifier")

    notion_manager = NotionManager(
        notion_token=NOTION_TOKEN,
        database_id=DATABASE_ID,
        jira_user_name=JIRA_USER_NAME,
        jira_token=JIRA_API_TOKEN
    )
    slack_manager = SlackManager()

    try:
        notion_records = notion_manager.get_all_records()
    except Exception as e:
        logger.error(f"Failed to get records from Notion: {e}")
        return

    for user_config in JIRA_USERS:
        owner = user_config.get("name")
        slack_user_id = user_config.get("slack_user_id")
        if not owner or not slack_user_id:
            continue

        user_records = [r for r in notion_records if r.get("owner") == owner]
        ongoing = [r for r in user_records if r.get("status") not in ("Done", "Completed")]
        completed = [r for r in user_records if r.get("status") in ("Done", "Completed")]

        message = _build_report(ongoing, completed)
        slack_manager.send_direct_message(message, slack_user_id, SLACK_TOKEN)

    logger.info("Notion task notifier completed")

if __name__ == "__main__":
    main()
