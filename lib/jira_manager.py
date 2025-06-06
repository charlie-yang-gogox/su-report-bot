import requests
import base64
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TYPE_TO_TAG_MAPPING = {
    "Bug": "Fix"
}

class JiraManager:
    def __init__(self, ids, user_name, token):
        """Initialize JiraManager with authentication details"""
        self.user_ids = json.loads(ids)
        self.user_name = user_name
        self.token = token
        self._headers = {
            "Authorization": "Basic " + base64.b64encode(f"{user_name}:{token}".encode()).decode(),
            "Content-Type": "application/json"
        }
        
    def get_tickets(self):
        """Get tickets from Jira API using custom JQL query"""
        jira_api_url = "https://gogotech.atlassian.net/rest/api/3/search"
        
        # Construct JQL query using user_ids
        user_ids_str = " OR ".join([f'assignee = "{user_id}"' for user_id in self.user_ids])
        jql = f'({user_ids_str}) AND sprint in openSprints() AND type != Sub-task ORDER BY created DESC'
        
        params = {"jql": jql}
        
        response = requests.get(jira_api_url, headers=self._headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Get unique active sprints from the response
        active_sprints = set()
        for issue in data["issues"]:
            sprints = issue["fields"].get("customfield_10008", [])
            for sprint in sprints:
                if sprint["state"] == "active":
                    active_sprints.add(sprint["name"])
        
        # Log outputs
        logger.info("="*50)
        logger.debug(f"JQL Query: {jql}")
        logger.info(f"Active Sprints: {sorted(active_sprints)}")
        logger.info(f"Total Issues: {len(data['issues'])}")
        logger.info("="*50)
        
        return data
    
    def filter_data(self, data):
        """Filter and format Jira data for Notion sync"""
        filtered_issues = []
        
        for issue in data["issues"]:
            fields = issue["fields"]
            key = issue["key"]
            summary = fields["summary"]
            status = fields["status"]["name"]
            issue_type = fields["issuetype"]["name"]
            tag = self.__get_tag_from_issue(issue)
            
            # Get assignee information
            owner = fields.get("assignee", {}).get("displayName", "Unassigned")
            
            # Get story points
            story_points = fields.get("customfield_10027", 0)
            
            # Get sprint information
            sprints = fields.get("customfield_10008", [])
            active_sprints = [sprint["name"] for sprint in sprints if sprint["state"] == "active"]
            
            # Get parent information for stories
            parent = None
            if "parent" in fields:
                parent = {
                    "key": fields["parent"]["key"],
                    "summary": fields["parent"]["fields"]["summary"]
                }
            
            filtered_issue = {
                "key": key,
                "summary": summary,
                "status": status,
                "type": issue_type,
                "owner": owner,
                "story_points": story_points,
                "active_sprints": active_sprints,
                "parent": parent,
                "tag": tag
            }
            
            filtered_issues.append(filtered_issue)
            
        # Log filtered data
        logger.debug("="*50)
        logger.debug("Filtered Issues Summary:")
        logger.debug(f"Total Issues: {len(filtered_issues)}")
        logger.debug("Issue Types:")
        issue_types = {}
        for issue in filtered_issues:
            issue_types[issue["type"]] = issue_types.get(issue["type"], 0) + 1
        for type_name, count in issue_types.items():
            logger.debug(f"- {type_name}: {count}")
        logger.debug("="*50)
        
        # Print detailed information for each issue
        logger.debug("\nDetailed Issue Information:")
        for idx, issue in enumerate(filtered_issues, 1):
            logger.debug(f"\n{idx}. {issue['key']} - {issue['summary']}")
            logger.debug(f"   Type: {issue['type']}")
            logger.debug(f"   Status: {issue['status']}")
            logger.debug(f"   Owner: {issue['owner']}")
            logger.debug(f"   Tag: {issue['tag']}")
            if issue['story_points']:
                logger.debug(f"   Story Points: {issue['story_points']}")
            if issue['active_sprints']:
                logger.debug(f"   Active Sprints: {', '.join(issue['active_sprints'])}")
            if issue['parent']:
                logger.debug(f"   Parent: {issue['parent']['key']} - {issue['parent']['summary']}")
            logger.debug("-" * 50)
        
        return filtered_issues
        
    def __get_tag_from_issue(self, issue):
        """Get tag from issue based on its type and parent"""
        fields = issue["fields"]
        if fields["issuetype"]["name"] == "Story":
            return f"Feat - {fields['parent']['fields']['summary']}" if "parent" in fields else ""

        return TYPE_TO_TAG_MAPPING.get(fields["issuetype"]["name"], fields["issuetype"]["name"])
