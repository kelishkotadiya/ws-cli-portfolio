# wealthgrabber

Wealthsimple Account Viewer CLI. Secure and simple tool to view your Wealthsimple account balances, transactions, and holdings from the command line.

## Features
- **Secure Authentication**: Uses system keyring to safely store credentials.
- **Account Listing**: Clear overview of all your accounts, deposits, and simple returns.
- **Transaction History**: View activities and transactions across your accounts.
- **Asset Positions**: Monitor your investment holdings with P&L tracking.
- **Dividend Income**: Totals and per-security income, plus upcoming announced dates.
- **Net Worth**: Household or own net worth with recent history and linked accounts.
- **Performance**: Simple returns, realized gains, and unrealized P&L.
- **Multiple Output Formats**: Table (default), JSON, and CSV output for easy integration.
- **Privacy Focused**: No data is stored externally; everything runs locally.

## Installation

This project is managed with `uv`.

### Quick Install

Install the application globally so you can run `wealthgrabber` directly:

```bash
# Clone the repository
git clone <your-repo-url>
cd wealthgrabber

# Install the application
make install
```

After installation, you can use `wealthgrabber` directly without the `uv run` prefix:

```bash
wealthgrabber --help
wealthgrabber login
wealthgrabber list
```

### Development Setup

For development, you can use `uv sync` to set up the environment:

```bash
# Install dependencies and sync environment
uv sync

# Run with uv (if not globally installed)
uv run wealthgrabber --help
```

## Usage

The CLI provides eight main commands: `login`, `logout`, `list`, `activities`, `assets`, `dividends`, `networth`, and `performance`.

All commands support the `--verbose/-v` flag for detailed status messages during execution.

### Authentication

#### Login
Authenticate with your Wealthsimple credentials. This supports 2FA and will cache your session securely.

```bash
wealthgrabber login
```

**Options:**
- `--force/-f`: Force a new login even if a valid session exists.
- `--username/-u EMAIL`: Email address to login with. If not provided, uses cached email or prompts.

#### Logout
Clear stored session and optionally cached email.

```bash
wealthgrabber logout
```

**Options:**
- `--username/-u EMAIL`: Email address to clear session for. If not provided, uses cached email.
- `--clear-email/-c`: Also clear the cached email address.

### Accounts

#### List Accounts
View a summary of your accounts with current values, net deposits, and simple returns.

```bash
wealthgrabber list
```

**Options:**
- `--show-zero/-z`: Show accounts with zero balance (default: true).
- `--liquid-only/-l`: Show only liquid accounts (excludes RRSP, LIRA, Private Equity, Private Credit).
- `--not-liquid/-n`: Show only non-liquid accounts (RRSP, LIRA, Private Equity, Private Credit).
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# View all accounts as table (default)
wealthgrabber list

# Show only liquid accounts in JSON format
wealthgrabber list --liquid-only --format json

# Show non-liquid accounts and hide zero balances
wealthgrabber list --not-liquid --no-show-zero
```

### Transactions

#### List Activities
View activities and transactions for your accounts.

```bash
wealthgrabber activities
```

**Options:**
- `--account/-a ACCOUNT_NUMBER`: Filter by account number (e.g., 'TFSA-001').
- `--dividends/-d`: Show only dividend transactions.
- `--limit/-n N`: Maximum number of activities per account (default: 50).
- `--since/-s YYYY-MM-DD`: Start date.
- `--until YYYY-MM-DD`: End date.
- `--type/-t TYPE`: Filter by activity type substring (e.g. `DIY_BUY`).
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# View recent activities as table (default)
wealthgrabber activities

# View only dividend transactions in JSON format
wealthgrabber activities --dividends --format json

# View last 100 activities from a specific account
wealthgrabber activities --account TFSA-001 --limit 100

# Buys since the start of the year
wealthgrabber activities --type DIY_BUY --since 2026-01-01

# Export activities to CSV
wealthgrabber activities --format csv > activities.csv
```

### Dividends

#### Dividend Income and Upcoming Dates
Show dividend income since the start of the year, then announced upcoming dates for current holdings.

```bash
wealthgrabber dividends
```

**Options:**
- `--account/-a ACCOUNT_NUMBER`: Filter by account number (e.g., 'TFSA-001').
- `--since/-s YYYY-MM-DD`: Start date for received income (default: January 1 of this year).
- `--currency CURRENCY`: Currency for amounts and yield (default: CAD).
- `--no-upcoming`: Skip the upcoming dividend calendar.
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# Year-to-date income plus upcoming dates
wealthgrabber dividends

# Income since a custom date, JSON export
wealthgrabber dividends --since 2025-01-01 --format json

# One account, skip the holdings calendar
wealthgrabber dividends --account TFSA-001 --no-upcoming
```

Per-transaction dividend history is still available via `wealthgrabber activities --dividends`.

### Net Worth

#### Household or Own Net Worth
Show current net worth, change over a recent window, and optionally the accounts that make it up.

```bash
wealthgrabber networth
```

**Options:**
- `--scope {household,own}`: HOUSEHOLD includes linked members (default: household).
- `--days N`: Number of days of history (default: 30).
- `--accounts`: Also list Wealthsimple and linked external accounts.
- `--currency CURRENCY`: Currency for amounts (default: CAD).
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# Last 30 days, household (default)
wealthgrabber networth

# Own identity only, 90-day history, JSON
wealthgrabber networth --scope own --days 90 --format json

# Include WS and linked external accounts
wealthgrabber networth --accounts
```

### Performance

#### Returns and P&L
Show net liquidation, net deposits, simple return, realized gains by security, and unrealized P&L by account.

```bash
wealthgrabber performance
```

**Options:**
- `--account/-a ACCOUNT_NUMBER`: Filter by account number (e.g., 'TFSA-001').
- `--since/-s YYYY-MM-DD`: Start date (default: January 1 of this year).
- `--currency CURRENCY`: Currency for amounts (default: CAD).
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# Year-to-date performance
wealthgrabber performance

# One account since a custom date
wealthgrabber performance --account TFSA-001 --since 2025-01-01 --format json
```

### Investments

#### List Asset Positions
View all asset positions across your accounts with profit/loss tracking.

```bash
wealthgrabber assets
```

**Options:**
- `--account/-a ACCOUNT_NUMBER`: Filter by account number (e.g., 'TFSA-001').
- `--by-account/-b`: Show positions grouped by account instead of aggregated.
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# View all positions aggregated (default)
wealthgrabber assets

# View positions grouped by account
wealthgrabber assets --by-account

# View positions for a specific account in JSON format
wealthgrabber assets --account TFSA-001 --format json

# Export all positions to CSV
wealthgrabber assets --format csv > positions.csv
```

## Output Formats

### Table Format (Default)
Human-readable ASCII tables with formatting, alignment, and totals where applicable.

### JSON Format
Structured JSON output suitable for programmatic processing.

### CSV Format
Comma-separated values for import into spreadsheets or other tools.

## Development

If you are an AI assistant or a developer looking to contribute, please refer to [CLAUDE.md](CLAUDE.md) for detailed guidelines.
