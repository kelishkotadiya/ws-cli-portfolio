from enum import Enum
from typing import Optional

import typer

from .accounts import print_accounts
from .activities import get_account_id_by_number, print_activities
from .assets import print_assets
from .auth import get_authenticated_client
from .auth import logout as auth_logout
from .dividends import print_dividends
from .networth import print_networth
from .performance import print_performance

app = typer.Typer(help="Wealthsimple Account Viewer CLI", no_args_is_help=True)


class OutputFormat(str, Enum):
    """Output format options."""

    table = "table"
    json = "json"
    csv = "csv"


class NetWorthScope(str, Enum):
    """Net worth account scope."""

    household = "household"
    own = "own"


def version_callback(value: bool | None) -> None:
    """Print version and exit when --version or -V is passed (eager)."""
    if value:
        from . import __version__

        typer.echo(f"wealthgrabber version {__version__}")
        raise typer.Exit()


@app.command()
def login(
    ctx: typer.Context,
    force: bool = typer.Option(
        False, "--force", "-f", help="Force a new login even if a valid session exists."
    ),
    username: Optional[str] = typer.Option(
        None,
        "--username",
        "-u",
        help="Email address to login with. If not provided, uses cached email or prompts.",
    ),
):
    """
    Authenticate with Wealthsimple and save the session.
    """
    verbose = ctx.obj.get("verbose") if ctx.obj else False
    ws = get_authenticated_client(force_login=force, username=username, verbose=verbose)
    if ws:
        print("Login routine completed successfully.")
    else:
        print("Login routine failed.")
        raise typer.Exit(code=1)


@app.command()
def logout(
    username: Optional[str] = typer.Option(
        None,
        "--username",
        "-u",
        help="Email address to clear session for. If not provided, uses cached email.",
    ),
    clear_email: bool = typer.Option(
        False, "--clear-email", "-c", help="Also clear the cached email address."
    ),
):
    """
    Clear stored session and optionally cached email.
    """
    auth_logout(username=username, clear_email=clear_email)


@app.command(name="list")
def list_accounts_cmd(
    ctx: typer.Context,
    show_zero_balances: bool = typer.Option(
        True, "--show-zero", "-z", help="Show accounts with zero balance."
    ),
    liquid_only: bool = typer.Option(
        False,
        "--liquid-only",
        "-l",
        help="Show only liquid accounts (excludes RRSP, LIRA, Private Equity, Private Credit).",
    ),
    not_liquid: bool = typer.Option(
        False,
        "--not-liquid",
        "-n",
        help="Show only non-liquid accounts (RRSP, LIRA, Private Equity, Private Credit).",
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format."
    ),
):
    """
    List all accounts with their numbers and current values.
    """
    verbose = ctx.obj.get("verbose") if ctx.obj else False
    ws = get_authenticated_client(verbose=verbose)
    if not ws:
        print("Could not authenticate.")
        raise typer.Exit(code=1)

    try:
        print_accounts(
            ws,
            show_zero_balances=show_zero_balances,
            liquid_only=liquid_only,
            not_liquid=not_liquid,
            output_format=output_format.value,
            verbose=verbose,
        )
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        raise typer.Exit(code=1)


@app.command()
def activities(
    ctx: typer.Context,
    account: Optional[str] = typer.Option(
        None, "--account", "-a", help="Filter by account number (e.g., 'TFSA-001')."
    ),
    dividends_only: bool = typer.Option(
        False, "--dividends", "-d", help="Show only dividend transactions."
    ),
    limit: int = typer.Option(
        50, "--limit", "-n", help="Maximum number of activities per account."
    ),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Start date YYYY-MM-DD."
    ),
    until: Optional[str] = typer.Option(None, "--until", help="End date YYYY-MM-DD."),
    activity_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by activity type substring (e.g. DIY_BUY)."
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format."
    ),
):
    """
    List activities/transactions for your accounts.
    """
    verbose = ctx.obj.get("verbose") if ctx.obj else False
    ws = get_authenticated_client(verbose=verbose)
    if not ws:
        print("Could not authenticate.")
        raise typer.Exit(code=1)

    try:
        account_id = None
        if account:
            account_id = get_account_id_by_number(ws, account)
            if not account_id:
                print(f"Account '{account}' not found.")
                raise typer.Exit(code=1)

        print_activities(
            ws,
            account_id=account_id,
            dividends_only=dividends_only,
            limit=limit,
            output_format=output_format.value,
            verbose=verbose,
            account_number=account,
            activity_type=activity_type,
            since=since,
            until=until,
        )
    except typer.Exit:
        raise
    except Exception as e:
        print(f"Error fetching activities: {e}")
        raise typer.Exit(code=1)


@app.command()
def assets(
    ctx: typer.Context,
    account: Optional[str] = typer.Option(
        None, "--account", "-a", help="Filter by account number (e.g., 'TFSA-001')."
    ),
    by_account: bool = typer.Option(
        False,
        "--by-account",
        "-b",
        help="Show positions grouped by account instead of aggregated.",
    ),
    profits: bool = typer.Option(
        False,
        "--profits",
        "-p",
        help="Show only positions with profit (P&L > 0).",
    ),
    losses: bool = typer.Option(
        False,
        "--losses",
        "-l",
        help="Show only positions with loss (P&L < 0).",
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format."
    ),
):
    """
    List all asset positions across your accounts.
    """
    verbose = ctx.obj.get("verbose") if ctx.obj else False
    ws = get_authenticated_client(verbose=verbose)
    if not ws:
        print("Could not authenticate.")
        raise typer.Exit(code=1)

    # Validate that both flags are not used together
    if profits and losses:
        print("Error: --profits and --losses cannot be used together.")
        raise typer.Exit(code=1)

    try:
        account_id = None
        if account:
            account_id = get_account_id_by_number(ws, account)
            if not account_id:
                print(f"Account '{account}' not found.")
                raise typer.Exit(code=1)

        # Determine P&L filter value
        pnl_filter = None
        if profits:
            pnl_filter = "profit"
        elif losses:
            pnl_filter = "loss"

        print_assets(
            ws,
            account_id=account_id,
            by_account=by_account,
            output_format=output_format.value,
            verbose=verbose,
            pnl_filter=pnl_filter,
        )
    except typer.Exit:
        raise
    except Exception as e:
        print(f"Error fetching assets: {e}")
        raise typer.Exit(code=1)


@app.command()
def dividends(
    ctx: typer.Context,
    account: Optional[str] = typer.Option(
        None, "--account", "-a", help="Filter by account number (e.g., 'TFSA-001')."
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        "-s",
        help="Start date YYYY-MM-DD. Defaults to January 1 of this year.",
    ),
    currency: str = typer.Option(
        "CAD", "--currency", help="Currency for amounts and yield."
    ),
    no_upcoming: bool = typer.Option(
        False,
        "--no-upcoming",
        help="Skip the upcoming dividend calendar.",
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format."
    ),
):
    """
    Show dividend income and upcoming announced dates.
    """
    verbose = ctx.obj.get("verbose") if ctx.obj else False
    ws = get_authenticated_client(verbose=verbose)
    if not ws:
        print("Could not authenticate.")
        raise typer.Exit(code=1)

    try:
        account_id = None
        if account:
            account_id = get_account_id_by_number(ws, account)
            if not account_id:
                print(f"Account '{account}' not found.")
                raise typer.Exit(code=1)

        print_dividends(
            ws,
            account_id=account_id,
            since=since,
            currency=currency,
            include_upcoming=not no_upcoming,
            output_format=output_format.value,
            verbose=verbose,
            account_label=account,
        )
    except typer.Exit:
        raise
    except Exception as e:
        print(f"Error fetching dividends: {e}")
        raise typer.Exit(code=1)


@app.command()
def networth(
    ctx: typer.Context,
    scope: NetWorthScope = typer.Option(
        NetWorthScope.household,
        "--scope",
        help="HOUSEHOLD includes linked members; OWN is this identity only.",
    ),
    days: int = typer.Option(
        30, "--days", help="Number of days of history (default 30)."
    ),
    currency: str = typer.Option("CAD", "--currency", help="Currency for amounts."),
    include_accounts: bool = typer.Option(
        False,
        "--accounts",
        help="Also list Wealthsimple and linked external accounts.",
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format."
    ),
):
    """
    Show household or own net worth and recent history.
    """
    verbose = ctx.obj.get("verbose") if ctx.obj else False
    ws = get_authenticated_client(verbose=verbose)
    if not ws:
        print("Could not authenticate.")
        raise typer.Exit(code=1)

    try:
        print_networth(
            ws,
            scope=scope.value.upper(),
            currency=currency,
            days=days,
            include_accounts=include_accounts,
            output_format=output_format.value,
            verbose=verbose,
        )
    except Exception as e:
        print(f"Error fetching net worth: {e}")
        raise typer.Exit(code=1)


@app.command()
def performance(
    ctx: typer.Context,
    account: Optional[str] = typer.Option(
        None, "--account", "-a", help="Filter by account number (e.g., 'TFSA-001')."
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        "-s",
        help="Start date YYYY-MM-DD. Defaults to January 1 of this year.",
    ),
    currency: str = typer.Option("CAD", "--currency", help="Currency for amounts."),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format."
    ),
):
    """
    Show simple returns, realized gains, and unrealized P&L.
    """
    verbose = ctx.obj.get("verbose") if ctx.obj else False
    ws = get_authenticated_client(verbose=verbose)
    if not ws:
        print("Could not authenticate.")
        raise typer.Exit(code=1)

    try:
        account_id = None
        if account:
            account_id = get_account_id_by_number(ws, account)
            if not account_id:
                print(f"Account '{account}' not found.")
                raise typer.Exit(code=1)

        print_performance(
            ws,
            account_id=account_id,
            since=since,
            currency=currency,
            output_format=output_format.value,
            verbose=verbose,
            account_label=account,
        )
    except typer.Exit:
        raise
    except Exception as e:
        print(f"Error fetching performance: {e}")
        raise typer.Exit(code=1)


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed status messages during execution."
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show the version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """
    Wealthsimple Account Viewer CLI
    """
    ctx.obj = {"verbose": verbose}
