import os
import logging
import requests
from typing import Dict, Any, List

class SlackManager:
    """Manager for Slack Bot API operations and direct message formatting"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    

    
    def send_direct_message(self, message: str, user_id: str, slack_token: str) -> bool:
        """Send direct message to a specific user using conversations.open API"""
        if not user_id or not slack_token:
            self.logger.warning("User ID or Slack token not provided, skipping direct message")
            return False
        
        try:
            # First, open a conversation with the user
            open_conversation_url = "https://slack.com/api/conversations.open"
            open_payload = {"users": user_id}
            open_headers = {
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json"
            }
            
            open_response = requests.post(open_conversation_url, headers=open_headers, json=open_payload, timeout=10)
            open_response.raise_for_status()
            open_data = open_response.json()
            
            if not open_data.get("ok"):
                self.logger.error(f"Failed to open conversation: {open_data.get('error')}")
                return False
            
            channel_id = open_data["channel"]["id"]
            
            # Then, send the message to the opened conversation
            post_message_url = "https://slack.com/api/chat.postMessage"
            message_payload = {
                "channel": channel_id,
                "text": message
            }
            
            message_response = requests.post(post_message_url, headers=open_headers, json=message_payload, timeout=10)
            message_response.raise_for_status()
            message_data = message_response.json()
            
            if not message_data.get("ok"):
                self.logger.error(f"Failed to send message: {message_data.get('error')}")
                return False
            
            self.logger.info(f"Direct message sent to user {user_id} successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send direct message to user {user_id}: {e}")
            return False
    
    def format_sprint_report(self, report_data: Dict[str, Any]) -> str:
        """Format report data for Slack message"""
        sprint_name = report_data["sprint_name"]
        total_records = report_data["total_records"]
        
        message = f"*📊 SPRINT REPORT [{sprint_name}]*\n"
        message += f"*📈 Total records: {total_records}*\n\n"
        
        # Get all records and sort by status
        all_records = []
        for status, records in report_data["status_groups"].items():
            for record in records:
                all_records.append({
                    **record,
                    "status": status
                })
        
        # Sort by status
        all_records.sort(key=lambda x: x["status"])
        
        # Format each record
        for record in all_records:
            ticket_link = f"<{record['jira_url']}|{record['ticket_id']}>"
            message += f"• {ticket_link}: {record['title']} `{record['status']}`\n"
        
        return message
    
    def _extract_active_sprints(self, jira_data: List[Dict[str, Any]]) -> set:
        """Extract active sprints from Jira data"""
        active_sprints = set()
        for ticket in jira_data:
            if ticket.get("active_sprints"):
                active_sprints.update(ticket["active_sprints"])
        return active_sprints
    
    def _filter_sprint_records(self, notion_records: List[Dict[str, Any]], sprint_name: str, owner: str) -> List[Dict[str, Any]]:
        """Filter notion records for a specific sprint and owner"""
        filtered_records = [
            record for record in notion_records 
            if record.get("sprint") == sprint_name and record.get("owner") == owner
        ]
        
        self.logger.info(f"Filtered {len(filtered_records)} records for sprint '{sprint_name}' and owner '{owner}'")
        return filtered_records
    
    def _group_records_by_status(self, records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group records by status"""
        status_groups = {}
        for record in records:
            status = record["status"]
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(record)
        return status_groups
    
    def _create_report_data(self, sprint_name: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create report data structure"""
        status_groups = self._group_records_by_status(records)
        
        report_data = {
            "sprint_name": sprint_name,
            "total_records": len(records),
            "status_groups": {}
        }
        
        # Group records by status
        for status in sorted(status_groups.keys()):
            report_data["status_groups"][status] = []
            status_records = status_groups[status]
            
            for record in status_records:
                report_data["status_groups"][status].append({
                    "ticket_id": record['jiraId'],
                    "title": record['title'],
                    "status": record['status'],
                    "jira_url": record['jiraUrl'],
                    "tags": record.get('tags', [])
                })
        
        return report_data
    
    def _log_sprint_report(self, report_data: Dict[str, Any], owner: str):
        """Log sprint report information"""
        sprint_name = report_data["sprint_name"]
        total_records = report_data["total_records"]
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"📊 SPRINT REPORT {sprint_name} - Owner: {owner}")
        self.logger.info(f"📈 Total records: {total_records}")
        self.logger.info(f"{'='*80}")
        
        # Get all records and sort by status
        all_records = []
        for status, records in report_data["status_groups"].items():
            for record in records:
                all_records.append({
                    **record,
                    "status": status
                })
        
        # Sort by status
        all_records.sort(key=lambda x: x["status"])
        
        # Log each record
        for record in all_records:
            self.logger.info(f"  • {record['ticket_id']}: {record['title']} `{record['status']}`")
    
    def send_sprint_report(self, report_data: Dict[str, Any], user_id: str, slack_token: str) -> bool:
        """Send sprint report to Slack via direct message"""
        message = self.format_sprint_report(report_data)
        
        if user_id and slack_token:
            return self.send_direct_message(message, user_id, slack_token)
        else:
            self.logger.warning("No user ID or Slack token provided, skipping Slack notification")
            return False
    
    def send_report(self, jira_data: List[Dict[str, Any]], notion_records: List[Dict[str, Any]], 
                   jira_users: List[Dict[str, Any]], slack_token: str) -> List[Dict[str, Any]]:
        """Send sprint reports for all users based on provided data from other managers"""
        self.logger.info("Starting sprint report processing for all users...")
        
        all_report_data = []
        
        # Get active sprints from Jira data first
        active_sprints = self._extract_active_sprints(jira_data)
        
        if not active_sprints:
            self.logger.info("No active sprints found in Jira data")
            return []
        
        self.logger.info(f"Active sprints found: {sorted(active_sprints)}")
        
        # Process each user
        for user_config in jira_users:
            jira_user_id = user_config.get("jira_user_id")
            slack_user_id = user_config.get("slack_user_id")
            owner = user_config.get("name", "unknown")
            
            # Skip if jira_user_id is missing or slack_user_id is empty
            if not jira_user_id or not slack_user_id:
                self.logger.info(f"Skipping user {owner} - missing jira_user_id or slack_user_id")
                continue
                
            try:
                self.logger.info(f"Processing reports for user: {owner}")
                
                # Process each active sprint for this user
                for sprint_name in sorted(active_sprints):
                    try:
                        # Filter notion records for this sprint and owner
                        sprint_records = self._filter_sprint_records(notion_records, sprint_name, owner)
                        
                        # Only proceed if filtered records count > 0
                        if sprint_records and len(sprint_records) > 0:
                            self.logger.info(f"\n{'='*60}")
                            self.logger.info(f"Processing Sprint: {sprint_name} for user: {owner}")
                            self.logger.info(f"{'='*60}")
                            self.logger.info(f"Found {len(sprint_records)} records in Notion for sprint '{sprint_name}', proceeding with report...")
                            
                            # Create report data
                            report_data = self._create_report_data(sprint_name, sprint_records)
                            
                            # Log sprint report
                            self._log_sprint_report(report_data, owner)
                            
                            # Send to Slack via direct message
                            self.send_sprint_report(report_data, user_id=slack_user_id, slack_token=slack_token)
                            
                            all_report_data.append(report_data)
                            
                        # No logging for sprints with no records
                            
                    except Exception as e:
                        self.logger.error(f"Error getting records for sprint '{sprint_name}' for user {owner}: {e}")
                
            except Exception as e:
                self.logger.error(f"Failed to process reports for user {owner}: {e}")
                continue
        
        self.logger.info("Sprint report processing completed for all users")
        return all_report_data
