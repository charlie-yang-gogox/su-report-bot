# SU Report Bot

A Python-based automation tool that synchronizes Jira tickets with Notion database and generates personalized Sprint reports for team members via Slack direct messages.

## Features

- 🔄 **Automatic synchronization** between Jira and Notion
  - Syncs current sprint tickets
  - Maintains historical tickets
  - Preserves tags and custom fields
- 📊 **Personalized Sprint reports** generation
  - Individual reports for each team member
  - Tracks story points and sprint progress
  - Records work logs and status updates
- 💬 **Slack integration** via direct messages
  - Uses Slack Bot API for secure communication
  - Sends personalized reports to each user
  - Secure direct messaging via Slack Bot API

## Prerequisites

- Python 3.8 or higher
- Jira account with API access
- Notion account with API access
- Slack workspace with Bot App access
- Required Python packages (see `requirements.txt`)

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/su-report-bot.git
cd su-report-bot
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
```bash
cp .env.example .env
```

## Configuration

### Environment Variables

Edit `.env` with your credentials:

```env
# Jira Configuration
JIRA_USER_NAME=your-jira-username@company.com
JIRA_API_TOKEN=your-jira-api-token

# Jira Users Configuration (JSON format - single line)
JIRA_USERS=[
  {
    "name": "charlie.yang",
    "jira_user_id": "6324466fc7601c8e4ac07788",
    "slack_user_id": "U03H7Q5A0B0"
  },
  {
    "name": "eric.chien",
    "jira_user_id": "629044a7cf01a10069af1962",
    "slack_user_id": "U03H7Q5A0B1"
  },
  {
    "name": "fiona.shih",
    "jira_user_id": "630331b36acf9eeb443d6e27",
    "slack_user_id": "U03H7Q5A0B2"
  }
]

# Notion Configuration
NOTION_DATABASE_ID=your-notion-database-id
NOTION_TOKEN=your-notion-api-token

# GitHub Configuration (optional)
GITHUB_TOKEN=your-github-token
GITHUB_OWNER=your-github-username
GITHUB_REPO=your-github-repo

# Slack Configuration
SLACK_TOKEN=xoxb-your-slack-bot-token
```

### Configuration Details

#### Jira Users Structure
Each user in `JIRA_USERS` should contain:
- `name`: Human-readable name for identification
- `jira_user_id`: Jira user ID (from Jira profile or API)
- `slack_user_id`: Slack user ID (e.g., U03H7Q5A0B0)

#### Slack Bot Setup
1. Create a Slack App at [https://api.slack.com/apps](https://api.slack.com/apps)
2. Add required OAuth Scopes:
   - `chat:write`
   - `im:write`
   - `users:read`
   - `channels:read`
3. Install the app to your workspace
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

## Usage

### Running the Bot

To sync Jira tickets with Notion and send reports:
```bash
python main.py
```

### Report Generation

The bot will:
1. Fetch active sprints from Jira
2. Sync ticket data with Notion
3. Generate personalized reports for each user
4. Send reports via Slack direct messages

### Report Format

Reports are sent in the following format:
```
📊 SPRINT REPORT [Sprint Name]
📈 Total records: X

• TICKET-123: Title `Status`
• TICKET-456: Title `Status`
• TICKET-789: Title `Status`
```

## Project Structure

```
su-report-bot/
├── lib/
│   ├── notion_manager.py    # Notion API integration
│   ├── jira_manager.py      # Jira API integration
│   ├── slack_manager.py     # Slack Bot API integration
│   └── logger.py            # Logging configuration
├── main.py                  # Main entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Example environment variables
└── README.md               # This file
```

## Architecture

### Managers

- **JiraManager**: Handles Jira API calls and ticket data processing
- **NotionManager**: Manages Notion database operations and data formatting
- **SlackManager**: Handles Slack Bot API for direct message delivery

### Data Flow

1. **Jira** → Fetch active sprints and ticket data
2. **Notion** → Sync and store ticket information
3. **Slack** → Generate and send personalized reports to each user

## API Requirements

### Jira API
- REST API v3 access
- Required fields:
  - Story Points (customfield_10027)
  - Sprint (customfield_10008)
  - Labels (for tags)

### Notion API
- Database should have these properties:
  - Ticket (Title)
  - Title (Rich Text)
  - SP (Number)
  - Owner (Select)
  - Status (Select)
  - Sprint (Select)
  - Tags (Multi-select)

### Slack API
- Bot User OAuth Token
- Required scopes for direct messaging

## Logging

- Log level: INFO
- Format: `YYYY-MM-DD HH:MM:SS [LEVEL] Message`
- Logs include:
  - Sprint processing status
  - Record counts and filtering results
  - Slack message delivery status
  - Error details for troubleshooting

## Error Handling

The bot includes comprehensive error handling:
- API connection failures
- Missing or invalid data
- Slack message delivery issues
- Individual user processing failures

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

### Common Issues

1. **"not_allowed_token_type"**: Use Bot User OAuth Token (xoxb-...)
2. **"missing_scope"**: Add required OAuth scopes and reinstall app
3. **No records found**: Check Notion database structure and property names
4. **Slack message failed**: Verify bot token and user IDs

### Debug Mode

Enable debug logging by modifying the logger level in `lib/logger.py`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please:
1. Check the troubleshooting section
2. Review the logs for error details
3. Open an issue in the GitHub repository
4. Contact the maintainers

## Changelog

### v2.0.0
- Migrated to Slack Bot API for direct messaging
- Added personalized user reports
- Improved error handling and logging
- Restructured configuration format

### v1.0.0
- Initial release with basic functionality
- Basic Jira-Notion synchronization
- Simple report generation 