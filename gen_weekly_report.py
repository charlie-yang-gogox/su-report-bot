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
    jira_manager = JiraManager(JIRA_USERS, JIRA_USER_NAME, JIRA_API_TOKEN)

    try:
        notion_records = notion_manager.get_all_records()
    except Exception as e:
        logger.error(f"Failed to get records from Notion: {e}")
        return

    # Get active sprints from Jira
    try:
        jira_raw = jira_manager.get_tickets()
        jira_filtered = jira_manager.filter_data(jira_raw)
        active_sprints = slack_manager._extract_active_sprints(jira_filtered)
    except Exception as e:
        logger.error(f"Failed to get active sprints from Jira: {e}")
        active_sprints = set()

    for user_config in JIRA_USERS:
        owner = user_config.get("name")
        slack_user_id = user_config.get("slack_user_id")
        if not owner or not slack_user_id:
            continue

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
        slack_manager.send_direct_message(message, slack_user_id, SLACK_TOKEN)

    logger.info("Notion task notifier completed")

if __name__ == "__main__":
    main()
