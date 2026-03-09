import os
import logging
import json
from dotenv import load_dotenv
from lib.notion_manager import NotionManager
from lib.linear_manager import LinearManager
from lib.slack_manager import SlackManager
from lib.logger import setup_logger

setup_logger()
load_dotenv()

LINEAR_API_TOKEN = os.getenv("LINEAR_API_TOKEN")
LINEAR_ORG_SLUG = os.getenv("LINEAR_ORG_SLUG")

LINEAR_USERS_JSON = os.getenv("LINEAR_USERS", "[]")
try:
    LINEAR_USERS = json.loads(LINEAR_USERS_JSON)
except (json.JSONDecodeError, TypeError) as e:
    logging.error(f"Failed to parse LINEAR_USERS JSON: {e}")
    LINEAR_USERS = []

NOTION_TOKEN = os.getenv("LINEAR_NOTION_TOKEN") or os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("LINEAR_NOTION_DATABASE_ID")

SLACK_TOKEN = os.getenv("SLACK_TOKEN")


def send_error_to_slack(error_message: str, slack_manager: SlackManager, slack_token: str):
    try:
        if LINEAR_USERS:
            admin_user_id = LINEAR_USERS[0].get("slack_user_id")
            if admin_user_id:
                error_msg = f"🚨 *Linear Report Bot Error*\n\n{error_message}"
                slack_manager.send_direct_message(error_msg, admin_user_id, slack_token)
                logging.info("Error notification sent to Slack")
    except Exception as e:
        logging.error(f"Failed to send error notification to Slack: {e}")


def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting Linear Report Bot")

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

        # Fetch Linear data
        logger.info("Fetching Linear data...")
        linear_data = linear_manager.get_tickets()
        linear_data = linear_manager.filter_data(linear_data)
        logger.info(f"Retrieved {len(linear_data)} Linear issues")

        # Sync to Notion
        logger.info("Syncing Linear data to Notion...")
        notion_manager.update(linear_data)
        logger.info("Notion sync completed")

        # Fetch all Notion records for report
        logger.info("Fetching Notion records...")
        notion_records = notion_manager.get_all_records()
        logger.info(f"Retrieved {len(notion_records)} Notion records")

        # Send reports via Slack
        logger.info("Sending reports to Slack...")
        users = [{**u, "issue_user_id": u["linear_user_id"]} for u in LINEAR_USERS]
        slack_manager.send_report(linear_data, notion_records, users, slack_token)
        logger.info("Reports sent successfully")

        logger.info("Linear Report Bot completed successfully")

    except Exception as e:
        error_message = (
            f"Error occurred in Linear Report Bot:\n\n"
            f"*Error Type:* {type(e).__name__}\n"
            f"*Error Message:* {str(e)}\n"
            f"*Timestamp:* {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}"
        )
        logger.error(f"Linear Report Bot failed: {e}", exc_info=True)

        if slack_manager and slack_token:
            send_error_to_slack(error_message, slack_manager, slack_token)

        raise


if __name__ == "__main__":
    main()
