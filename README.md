# SU Report Bot

A Python-based automation tool that synchronizes Jira tickets with Notion database and generates weekly reports.

## Features

- 🔄 Automatic synchronization between Jira and Notion
  - Syncs current sprint tickets
  - Maintains historical tickets
  - Preserves tags and custom fields
- 📊 su report generation
  - Tracks story points
  - Monitors sprint progress
  - Records work logs

## Prerequisites

- Python 3.8 or higher
- Jira account with API access
- Notion account with API access
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/su-report-bot.git
cd su-report-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```
Edit `.env` with your credentials:
```
JIRA_USER_NAME=your-jira-username
JIRA_TOKEN=your-jira-api-token
NOTION_TOKEN=your-notion-api-token
NOTION_DATABASE_ID=your-notion-database-id
```

## Usage

### Running the Sync

To sync Jira tickets with Notion:
```bash
python main.py
```

## Configuration

### Jira Configuration
- The bot uses Jira's REST API v3
- Required fields:
  - Story Points (customfield_10027)
  - Sprint (customfield_10008)
  - Labels (for tags)

### Notion Configuration
- Database should have the following properties:
  - Ticket (Title)
  - Title (Rich Text)
  - SP (Number)
  - Owner (Select)
  - Status (Select)
  - Sprint (Select)
  - Tags (Multi-select)

## Project Structure

```
su-report-bot/
├── lib/
│   ├── notion_manager.py    # Notion API integration
│   └── jira_manager.py      # Jira API integration
├── main.py                  # Main entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Example environment variables
└── README.md               # This file
```

## Logging

- Log level can be configured in the code

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers. 