import requests
import logging

logger = logging.getLogger(__name__)

LINEAR_API_URL = "https://api.linear.app/graphql"

GET_ACTIVE_ISSUES_QUERY = """
query GetActiveIssues($userIds: [ID!]!) {
  issues(
    filter: {
      assignee: { id: { in: $userIds } }
      cycle: { isActive: { eq: true } }
    }
    first: 100
  ) {
    nodes {
      identifier
      title
      state { name }
      assignee { displayName }
      estimate
      labels { nodes { name } }
      cycle { id name number isActive }
      parent { identifier title }
      url
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

GET_MORE_ACTIVE_ISSUES_QUERY = """
query GetMoreActiveIssues($userIds: [ID!]!, $cursor: String!) {
  issues(
    filter: {
      assignee: { id: { in: $userIds } }
      cycle: { isActive: { eq: true } }
    }
    first: 100
    after: $cursor
  ) {
    nodes {
      identifier
      title
      state { name }
      assignee { displayName }
      estimate
      labels { nodes { name } }
      cycle { id name number isActive }
      parent { identifier title }
      url
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

GET_ISSUE_BY_ID_QUERY = """
query GetIssue($id: String!) {
  issue(id: $id) {
    identifier
    title
    state { name }
    assignee { displayName }
    estimate
    cycle { name number isActive }
    url
  }
}
"""


class LinearManager:
    def __init__(self, users, token):
        """Initialize LinearManager with user list and API token.

        Args:
            users: list of dicts with keys: linear_user_id, slack_user_id, name
            token: Linear personal API key
        """
        if isinstance(users, list):
            self.user_ids = [u.get("linear_user_id") for u in users if u.get("linear_user_id")]
        else:
            self.user_ids = []

        self.token = token
        self._headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }

    def _graphql(self, query: str, variables: dict) -> dict:
        """Execute a GraphQL query against the Linear API."""
        payload = {"query": query, "variables": variables}
        response = requests.post(LINEAR_API_URL, headers=self._headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            logger.error(f"Linear GraphQL errors: {data['errors']}")
            raise ValueError(f"Linear API error: {data['errors']}")

        return data

    @staticmethod
    def _cycle_display_name(cycle: dict) -> str:
        """Return a display name for a cycle. Uses name if set, else 'Cycle {number}'."""
        return cycle.get("name") or f"Cycle {cycle.get('number', '?')}"

    def get_tickets(self) -> dict:
        """Fetch all issues assigned to tracked users in active cycles."""
        all_nodes = []

        data = self._graphql(GET_ACTIVE_ISSUES_QUERY, {"userIds": self.user_ids})
        issues_data = data["data"]["issues"]
        all_nodes.extend(issues_data["nodes"])

        page_info = issues_data["pageInfo"]
        while page_info.get("hasNextPage"):
            cursor = page_info["endCursor"]
            data = self._graphql(GET_MORE_ACTIVE_ISSUES_QUERY, {"userIds": self.user_ids, "cursor": cursor})
            issues_data = data["data"]["issues"]
            all_nodes.extend(issues_data["nodes"])
            page_info = issues_data["pageInfo"]

        active_cycles = set()
        for node in all_nodes:
            if node.get("cycle"):
                active_cycles.add(self._cycle_display_name(node["cycle"]))

        logger.info("=" * 50)
        logger.info(f"Active Cycles: {sorted(active_cycles)}")
        logger.info(f"Total Issues: {len(all_nodes)}")
        logger.info("=" * 50)

        return {"issues": all_nodes}

    def filter_data(self, data: dict) -> list:
        """Normalize Linear issue nodes into the standard filtered-issues format."""
        filtered_issues = []

        for node in data.get("issues", []):
            if not isinstance(node, dict):
                logger.warning(f"Skipping unexpected node format: {node}")
                continue

            key = node.get("identifier", "")
            summary = node.get("title", "")
            status = (node.get("state") or {}).get("name", "Unknown")
            owner = (node.get("assignee") or {}).get("displayName", "Unassigned")
            story_points = node.get("estimate") or 0

            cycle = node.get("cycle")
            active_sprints = [self._cycle_display_name(cycle)] if cycle else []

            parent = None
            if node.get("parent"):
                parent = {
                    "key": node["parent"]["identifier"],
                    "summary": node["parent"]["title"],
                }

            labels = [lbl["name"] for lbl in (node.get("labels") or {}).get("nodes", [])]
            tag = self.__get_tag(labels, parent)
            issue_type = labels[0] if labels else "Issue"

            filtered_issues.append({
                "key": key,
                "summary": summary,
                "status": status,
                "type": issue_type,
                "owner": owner,
                "story_points": story_points,
                "active_sprints": active_sprints,
                "parent": parent,
                "tag": tag,
                "url": node.get("url", ""),
            })

        logger.debug("=" * 50)
        logger.debug(f"Filtered Issues: {len(filtered_issues)}")
        logger.debug("=" * 50)

        return filtered_issues

    def get_history_ticket(self, key: str) -> dict | None:
        """Fetch a single Linear issue by its identifier (e.g. 'CAF-123').
        Used by NotionManager to sync history tickets.
        """
        try:
            data = self._graphql(GET_ISSUE_BY_ID_QUERY, {"id": key})
            node = data["data"].get("issue")
            if not node:
                logger.warning(f"Linear issue not found: {key}")
                return None

            cycle = node.get("cycle")
            active_sprints = [self._cycle_display_name(cycle)] if (cycle and cycle.get("isActive")) else []

            return {
                "key": node["identifier"],
                "summary": node.get("title", ""),
                "status": (node.get("state") or {}).get("name", "Unknown"),
                "story_points": node.get("estimate") or 0,
                "active_sprints": active_sprints,
                "owner": (node.get("assignee") or {}).get("displayName", "Unassigned"),
            }
        except Exception as e:
            logger.error(f"Failed to get Linear issue {key}: {e}")
            return None

    @staticmethod
    def __get_tag(labels: list, parent: dict | None) -> str:
        """Derive tag from labels and parent."""
        if parent:
            return f"Feat - {parent['summary']}"
        return labels[0] if labels else ""
