import requests
import base64
import logging

logger = logging.getLogger(__name__)

# Constants
NOTION_API_VERSION = "2021-05-13"
NOTION_BASE_URL = "https://api.notion.com/v1"
JIRA_BASE_URL = "https://gogotech.atlassian.net"

# Property names
PROPERTY_NAMES = {
    "TICKET": "Ticket",
    "TITLE": "Title",
    "SP": "SP",
    "OWNER": "Owner",
    "STATUS": "Status",
    "SPRINT": "Sprint",
    "TAGS": "Tags"
}

class NotionManager:
    def __init__(self, notion_token, database_id, jira_user_name, jira_token):
        """Initialize NotionManager with authentication and configuration details"""
        self.notion_token = notion_token
        self.database_id = database_id
        self.jira_user_name = jira_user_name
        self.jira_token = jira_token
        self.notion_headers = {
            "Authorization": notion_token,
            "Content-Type": "application/json",
            "Notion-Version": NOTION_API_VERSION
        }
        self.jira_headers = {
            "Authorization": "Basic " + base64.b64encode(f"{jira_user_name}:{jira_token}".encode()).decode(),
            "Content-Type": "application/json"
        }

    def get_notion_work_record(self, sprint_name):
        """Get work records from Notion database for a specific sprint"""
        logger.info(f"Getting work records for sprint: {sprint_name}")
        notion_query_url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        
        search_payload = {
            "filter": {
                "property": "Sprint",
                "select": {"equals": sprint_name}
            }
        }
        
        response = requests.post(notion_query_url, headers=self.notion_headers, json=search_payload)
        response.raise_for_status()
        return self.__format_record(response.json())

    def __format_record(self, work_record):
        """Format Notion work record into a standardized format"""
        formatted_work_records = []
        for record in work_record["results"]:
            jira_id = record["properties"]["Jira Id"]["rich_text"][0]["text"]["content"]
            title = record["properties"]["Title"]["title"][0]["text"]["content"]
            status = record["properties"]["Status"]["select"]["name"]
            jira_url = f"https://gogotech.atlassian.net/browse/{jira_id}"

            formatted_work_records.append({
                "jiraId": jira_id,
                "title": title,
                "status": status,
                "jiraUrl": jira_url
            })

        formatted_work_records.sort(key=lambda x: x["status"])
        return formatted_work_records

    def __handle_api_error(self, operation, key, error):
        """Handle API errors consistently"""
        error_msg = f"Failed to {operation} {key}"
        if hasattr(error, 'response') and hasattr(error.response, 'text'):
            error_msg += f"\nError details: {error.response.text}"
        logger.error(error_msg)

    def __create_notion_page(self, key, properties):
        """Create a new page in Notion database"""
        notion_url = f"{NOTION_BASE_URL}/pages"
        request_data = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }
        
        try:
            response = requests.post(notion_url, headers=self.notion_headers, json=request_data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.__handle_api_error("create", key, e)
            raise

    def __update_notion_page(self, page_id, key, properties):
        """Update a Notion page with given properties"""
        update_url = f"{NOTION_BASE_URL}/pages/{page_id}"
        update_data = {"properties": properties}
        
        try:
            response = requests.patch(update_url, headers=self.notion_headers, json=update_data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.__handle_api_error("update", key, e)
            raise

    def __create_properties(self, key, summary, status, story_points, sprint, owner, url, tag=None):
        """Create Notion properties dictionary with common fields"""
        properties = {
            PROPERTY_NAMES["TICKET"]: {"title": [{"text": {"content": key, "link": {"url": url}}}]},
            PROPERTY_NAMES["TITLE"]: {"rich_text": [{"text": {"content": summary}}]},
            PROPERTY_NAMES["SP"]: {"number": story_points if story_points is not None else 0},
            PROPERTY_NAMES["OWNER"]: {"select": {"name": owner}},
            PROPERTY_NAMES["STATUS"]: {"select": {"name": status}}
        }
        
        # Handle sprint based on its type
        if isinstance(sprint, list) and sprint:  # Jira sprint list
            properties[PROPERTY_NAMES["SPRINT"]] = {"select": {"name": sprint[0]}}
        elif isinstance(sprint, dict) and sprint.get("select"):  # Notion sprint structure
            properties[PROPERTY_NAMES["SPRINT"]] = sprint
        else:
            properties[PROPERTY_NAMES["SPRINT"]] = {"select": None}
            
        if tag:
            properties[PROPERTY_NAMES["TAGS"]] = {"select": {"name": tag}}
            
        return properties

    def __get_jira_ticket(self, key):
        """Get ticket details from Jira API"""
        try:
            response = requests.get(
                f"{JIRA_BASE_URL}/rest/api/3/issue/{key}",
                headers=self.jira_headers
            )
            response.raise_for_status()
            data = response.json()
            
            # Get sprint information
            sprints = data["fields"].get("customfield_10008", [])
            active_sprints = [sprint["name"] for sprint in sprints if sprint["state"] == "active"]
            
            return {
                "key": key,
                "summary": data["fields"]["summary"],
                "status": data["fields"]["status"]["name"],
                "story_points": data["fields"].get("customfield_10027", 0),
                "active_sprints": active_sprints,
                "owner": data["fields"].get("assignee", {}).get("displayName", "Unassigned")
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get JIRA ticket {key}: {e}")
            return None

    def __sync_current_tickets(self, current_pages, jira_data):
        """Sync Notion pages with current sprint data from Jira"""
        # Create a dictionary of current sprint tickets for quick lookup
        current_tickets = {ticket["key"]: ticket for ticket in jira_data}
        
        # Process existing pages
        for key, page in current_pages.items():
            ticket = current_tickets[key]
            url = f"{JIRA_BASE_URL}/browse/{key}"
            
            logger.info(f"Updating ticket in current sprint: {key}")
            
            # Get existing tags from page
            existing_tags = page["properties"].get(PROPERTY_NAMES["TAGS"], {}).get("multi_select", [])
            
            # Create base properties
            properties = self.__create_properties(
                key,
                ticket["summary"],
                ticket["status"],
                ticket["story_points"],
                ticket["active_sprints"],  # Pass Jira sprint list
                page["properties"][PROPERTY_NAMES["OWNER"]]["select"]["name"],  # Keep existing owner
                url,
                ticket["tag"]  # Add tag parameter
            )
            
            # Preserve existing tags
            if existing_tags:
                properties[PROPERTY_NAMES["TAGS"]] = {"multi_select": existing_tags}
            
            # Update page
            self.__update_notion_page(page["id"], key, properties)
        
        # Create new pages for tickets that don't exist in Notion
        for key, ticket in current_tickets.items():
            if key not in current_pages:
                logger.info(f"Creating new ticket: {key}")
                url = f"{JIRA_BASE_URL}/browse/{key}"
                properties = self.__create_properties(
                    key,
                    ticket["summary"],
                    ticket["status"],
                    ticket["story_points"],
                    ticket["active_sprints"],  # Pass Jira sprint list
                    ticket["owner"],
                    url,
                    ticket["tag"]
                )
                
                self.__create_notion_page(key, properties)

    def __sync_history_tickets(self, history_pages, jira_data):
        """Sync Notion pages that are not in current sprint with Jira data"""
        # Create a dictionary of current sprint tickets for quick lookup
        current_tickets = {ticket["key"]: ticket for ticket in jira_data}
        
        for key, page in history_pages.items():
            url = f"{JIRA_BASE_URL}/browse/{key}"
            
            # Get ticket from Jira API
            ticket = self.__get_jira_ticket(key)
            if ticket is None:
                logger.info(f"Skipping update for {key}: Failed to get JIRA status")
                continue
            
            logger.info(f"Updating history ticket: {key}")
            
            # Get existing tags from page
            existing_tags = page["properties"].get(PROPERTY_NAMES["TAGS"], {}).get("multi_select", [])
            
            # Create base properties
            properties = self.__create_properties(
                key,
                ticket["summary"],
                ticket["status"],
                ticket["story_points"],
                page["properties"][PROPERTY_NAMES["SPRINT"]],  # Keep existing sprint
                page["properties"][PROPERTY_NAMES["OWNER"]]["select"]["name"],  # Keep existing owner
                url
            )
            
            # Preserve existing tags
            if existing_tags:
                properties[PROPERTY_NAMES["TAGS"]] = {"multi_select": existing_tags}
            
            # Update page
            self.__update_notion_page(page["id"], key, properties)

    def update(self, jira_data):
        """Main function to sync Jira and Notion data"""
        logger.info("Starting sync process...")
        
        try:
            # Get all existing pages from Notion
            notion_query_url = f"{NOTION_BASE_URL}/databases/{self.database_id}/query"
            response = requests.post(notion_query_url, headers=self.notion_headers, json={})
            response.raise_for_status()
            notion_pages = response.json()
            
            # Create sets of current sprint and history pages
            current_sprint_tickets = {ticket["key"] for ticket in jira_data}
            current_pages = {}
            history_pages = {}
            
            for page in notion_pages.get("results", []):
                # 安全地獲取 ticket key
                ticket_property = page["properties"].get(PROPERTY_NAMES["TICKET"])
                if not ticket_property or "title" not in ticket_property:
                    logger.warning(f"Skipping page {page.get('id', 'unknown')}: Missing ticket property")
                    continue
                
                title_array = ticket_property["title"]
                if not title_array or len(title_array) == 0:
                    logger.warning(f"Skipping page {page.get('id', 'unknown')}: Empty title array")
                    continue
                
                key = title_array[0]["text"]["content"]
                if key in current_sprint_tickets:
                    current_pages[key] = page
                else:
                    history_pages[key] = page
            
            # Sync with current sprint data
            self.__sync_current_tickets(current_pages, jira_data)
            
            # Sync remaining pages with Jira API
            self.__sync_history_tickets(history_pages, jira_data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to sync with Notion: {e}")
        
        logger.info("Sync process completed")

