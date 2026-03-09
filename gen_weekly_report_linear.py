import os
import json
import logging
from dotenv import load_dotenv
from lib.notion_manager import NotionManager
from lib.slack_manager import SlackManager
from lib.linear_manager import LinearManager
from lib.logger import setup_logger

setup_logger()
load_dotenv()

LINEAR_API_TOKEN = os.getenv("LINEAR_API_TOKEN")
LINEAR_ORG_SLUG = os.getenv("LINEAR_ORG_SLUG")

LINEAR_USERS_JSON = os.getenv("LINEAR_USERS", "[]")
try:
    LINEAR_USERS = json.loads(LINEAR_USERS_JSON)
except (json.JSONDecodeError, TypeError) as e:
    logging.error(f"Failed to parse LINEAR_USERS: {e}")
    LINEAR_USERS = []

NOTION_TOKEN = os.getenv("LINEAR_NOTION_TOKEN") or os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("LINEAR_NOTION_DATABASE_ID")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")


def _format_records(records):
    lines = []
    for record in records:
        ticket_link = f"<{record['jiraUrl']}|{record['jiraId']}>"
        status = record.get("status", "")
        lines.append(f"• {ticket_link} {record['title']} `{status}`")
    return "\n".join(lines)


def _build_report(sprint_names, ongoing, completed):
    message = f"*🏃 Cycle:* {sprint_names}\n\n"
    message += "*🔄 Ongoing:*\n"
    if ongoing:
        message += _format_records(ongoing)
    message += "\n\n*✅ Completed:*\n"
    if completed:
        message += _format_records(completed)
    message += "\n\n*📝 Summary:*\n"
    return message


def send_error_to_slack(error_message: str, slack_manager: SlackManager, slack_token: str):
    try:
        if LINEAR_USERS:
            admin_user_id = LINEAR_USERS[0].get("slack_user_id")
            if admin_user_id:
                error_msg = f"🚨 *Linear Weekly Report Bot Error*\n\n{error_message}"
                slack_manager.send_direct_message(error_msg, admin_user_id, slack_token)
                logging.info("Error notification sent to Slack")
    except Exception as e:
        logging.error(f"Failed to send error notification to Slack: {e}")


def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting Linear Weekly Report Bot")

    slack_manager = None
    slack_token = SLACK_TOKEN

    try:
        linear_manager = LinearManager(LINEAR_USERS, LINEAR_API_TOKEN)

        issue_base_url = f"https://linear.app/{LINEAR_ORG_SLUG}/issue" if LINEAR_ORG_SLUG else "https://linear.app"

        notion_manager = NotionManager(
            notion_token=NOTION_TOKEN,
            database_id=DATABASE_ID,
            issue_base_url=issue_base_url,
            history_ticket_fetcher=linear_manager.get_history_ticket,
        )
        slack_manager = SlackManager()

        # Fetch Notion records
        logger.info("Fetching Notion records...")
        notion_records = notion_manager.get_all_records()
        logger.info(f"Retrieved {len(notion_records)} Notion records")

        # Fetch active cycles from Linear
        logger.info("Fetching active cycles from Linear...")
        linear_raw = linear_manager.get_tickets()
        linear_filtered = linear_manager.filter_data(linear_raw)
        active_sprints = slack_manager._extract_active_sprints(linear_filtered)
        logger.info(f"Found {len(active_sprints)} active cycles")

        # Process each user
        logger.info("Processing weekly reports for all users...")
        for user_config in LINEAR_USERS:
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
                if r.get("status") not in ("Done", "Completed", "Closed", "Cancelled")
            ]
            completed = [
                r for r in user_records
                if r.get("status") in ("Done", "Completed", "Closed", "Cancelled")
            ]

            user_sprints = sorted({r.get("sprint") for r in user_records if r.get("sprint")})
            sprint_names = ", ".join(user_sprints) if user_sprints else ", ".join(sorted(active_sprints))
            message = _build_report(sprint_names, ongoing, completed)

            success = slack_manager.send_direct_message(message, slack_user_id, slack_token)
            if success:
                logger.info(f"Weekly report sent successfully to {owner}")
            else:
                logger.warning(f"Failed to send weekly report to {owner}")

        logger.info("Linear Weekly Report Bot completed successfully")

    except Exception as e:
        error_message = (
            f"Error occurred in Linear Weekly Report Bot:\n\n"
            f"*Error Type:* {type(e).__name__}\n"
            f"*Error Message:* {str(e)}\n"
            f"*Timestamp:* {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}"
        )
        logger.error(f"Linear Weekly Report Bot failed: {e}", exc_info=True)

        if slack_manager and slack_token:
            send_error_to_slack(error_message, slack_manager, slack_token)

        raise


if __name__ == "__main__":
    main()
