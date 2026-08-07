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
# Placeholders only. Real account ids and Slack ids belong in .env / repository
# secrets, never in a tracked file.
JIRA_USERS=[
  {
    "name": "first.user",
    "jira_user_id": "<atlassian-account-id>",
    "slack_user_id": "<slack-member-id>"
  },
  {
    "name": "second.user",
    "jira_user_id": "<atlassian-account-id>",
    "slack_user_id": "<slack-member-id>"
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

# Logging (optional) - stdout verbosity, default INFO. See "Logging" below.
LOG_LEVEL=INFO
```

### Logging

Report content — ticket titles, owner names, and API response bodies — is logged at
`DEBUG`. `INFO` carries only counts and stage markers, so a normal run reads
`Sent report to 4 users, 46 tickets` rather than listing the sprint.

This split exists because stdout becomes the GitHub Actions run log, which is visible to
everyone with repository access. `LOG_LEVEL` controls the stdout stream only; the log file
under `logs/` always records `DEBUG`, so local debugging keeps full detail without widening
what CI prints.

To get that detail in CI, dispatch the workflow manually with its `debug` input enabled.
That run's log will contain the full sprint, so delete it afterwards. Scheduled runs cannot
set the input.

### Configuration Details

#### Jira Users Structure
Each user in `JIRA_USERS` should contain:
- `name`: Human-readable name for identification
- `jira_user_id`: Jira user ID (from Jira profile or API)
- `slack_user_id`: Slack member ID (starts with `U`, found in the member's profile)

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

## Scheduled runs (GitHub Actions)

`.github/workflows/report.yml` runs `scripts/run_reports.sh` on a schedule. In CI
there is no `.env` — every value comes from repo Actions secrets.

| Cadence | cron (UTC) | Asia/Taipei | Scripts |
|---|---|---|---|
| daily | `3 1 * * 1-5` | weekdays 09:03 | `main.py` + `main_linear.py` |
| weekly | `7 10 * * 5` | Friday 18:07 | `gen_weekly_report.py` + `gen_weekly_report_linear.py` |

Both trackers always run and their exit codes are captured independently, so a
Jira outage cannot swallow the Linear team's report.

### Enabling the schedule

Scheduled runs are gated on a repo variable and are **off by default**:

```bash
gh variable set REPORT_SCHEDULE_ENABLED --body true
```

The gate exists because this repository is public while the report scripts log
ticket ids and titles to stdout — enabling the schedule on a public repo
publishes the team's sprint contents in the run log, which anyone can read. Make
the repository private first, or accept that trade-off deliberately.

### Manual run / re-send

Actions → Report → Run workflow, choosing `daily` or `weekly`. Or:

```bash
gh workflow run report.yml -f mode=daily
```

A manual dispatch always runs, regardless of the gate.

### Operational notes

- **60-day dormancy**: GitHub disables scheduled workflows after 60 days without
  repository activity and emails the owner. This repo's commits are sparse, so
  treat a periodic re-enable as expected maintenance rather than assuming the
  schedule runs forever.
- **Punctuality**: GitHub does not guarantee scheduled workflows fire on time and
  delays cluster on the hour, which is why both crons use off-minutes.
- **Failure reporting**: each script DMs its own error to the first user in
  `JIRA_USERS` / `LINEAR_USERS`, and the runner exits non-zero so the Actions run
  is marked failed.
- **Rotating a credential**: `gh secret set <NAME>` — the workflow needs no edit.
- **History sync window** (`HISTORY_SYNC_DAYS`, default 90): archived Notion pages
  created longer ago than this are not re-synced. Without it every run re-fetched
  and re-wrote every archived page — measured at 733 + 820 pages and roughly 19 of
  a 20 minute run, for records no report reads. Set `HISTORY_SYNC_DAYS=0` to sync
  everything. The cutoff deliberately reads Notion's `created_time`, not
  `last_edited_time`: the sync itself rewrites those pages, so `last_edited_time`
  is always "today" and gating on it skips nothing.
- **Editing the user list**: `JIRA_USERS` / `LINEAR_USERS` are single-line JSON.
  If the JSON fails to parse, the scripts fall back to an empty list and silently
  send nothing, so re-check formatting after any edit.

## Known issues

### Jira integration is unauthenticated — open, parked 2026-08-04

The Jira half of the bot has produced nothing since **2026-07-23 22:25 UTC**. The
Linear half is unaffected: separate credentials, running normally.

**Cause.** Jira rejects the configured `JIRA_USER_NAME` + `JIRA_API_TOKEN` pair.
`GET /rest/api/3/myself` returns 401 with header `X-Seraph-Loginreason:
AUTHENTICATED_FAILED` — identical to what a deliberately wrong password returns,
while a request sent with no credentials at all omits that header entirely. The
email is correct and the token is a well-formed 192-character `ATATT3…` value, so
the token itself is expired or revoked. The `JIRA_*` secrets currently in GitHub
Actions were loaded from a local `.env` and carry that same dead token.

**Why a week of runs looked fine.** Jira answers unauthorized *searches* with 200
and an empty result set rather than 401:

| request | response |
|---|---|
| `POST /rest/api/3/search/jql` (what the bot sends) | 200, 0 issues |
| `project = CET` with no other clause | 200, 0 issues |
| `GET /rest/api/3/issue/{key}` | 404 |
| `GET /rest/api/3/myself` | 401 |

So `get_tickets()` raises nothing, no active sprint is found, `send_report()`
returns early, and the script exits 0. Every run since 2026-07-24 has reported
success while sending nothing. The history lookups that return `None` on every run
have the same single cause.

**To unblock**

1. Mint a new API token at
   <https://id.atlassian.com/manage-profile/security/api-tokens>. The old one
   should show as expired or absent there, which independently confirms the cause.
2. `gh secret set JIRA_API_TOKEN` — plus `JIRA_USER_NAME` if the account changes.
3. Trigger a manual `daily` run and look for a non-zero `Retrieved N JIRA tickets`.
4. Do not bother mining Codemagic's `mobile` environment group for a replacement:
   pushes on 2026-07-29 and 2026-07-30 would have fired its push-triggered builds
   and no Jira write followed, so its token is very likely the same dead one.

**Fix to make once unblocked.** Have `JiraManager` call `/rest/api/3/myself` once
at construction and fail loudly on anything but 200. That endpoint 401s under
exactly this failure while the search endpoint does not, which converts a silent
week into a same-day Slack error. Gating on "zero issues across every configured
user" is weaker — a sprint boundary legitimately produces zero.

### Four of five Jira users cannot be messaged — open

`slack_user_id` is an empty string for four of the five entries in `JIRA_USERS`,
and `send_report` skips any user missing it. Even with a working token, only one
user would receive a Jira report. One of the four has an id recoverable from the
matching `LINEAR_USERS` entry; the other three need a Slack lookup. This is a
secret/config edit, not a code change.

### One synced owner is never reported to — open

An owner of 123 pages in the Jira Notion database is absent from `JIRA_USERS`.
Adding them needs their Atlassian account id, which cannot be resolved while the
credential above is dead: user search returns empty and their tickets 404.

## Project Structure

```
su-report-bot/
├── .github/workflows/
│   └── report.yml           # Scheduled + manual report runs
├── lib/
│   ├── notion_manager.py    # Notion API integration
│   ├── jira_manager.py      # Jira API integration
│   ├── linear_manager.py    # Linear API integration
│   ├── slack_manager.py     # Slack Bot API integration
│   └── logger.py            # Logging configuration
├── scripts/
│   └── run_reports.sh       # Single entry point for every run
├── main.py                  # Daily report — Jira
├── main_linear.py           # Daily report — Linear
├── gen_weekly_report.py     # Weekly report — Jira
├── gen_weekly_report_linear.py  # Weekly report — Linear
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