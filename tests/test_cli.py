from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from wealthgrabber.cli import app

runner = CliRunner()


@patch("wealthgrabber.cli.get_authenticated_client")
def test_login_command_success(mock_get_auth):
    """Test login command success path."""
    mock_get_auth.return_value = MagicMock()

    result = runner.invoke(app, ["login"])

    assert result.exit_code == 0
    assert "Login routine completed successfully" in result.stdout
    mock_get_auth.assert_called_with(force_login=False, username=None, verbose=False)


@patch("wealthgrabber.cli.get_authenticated_client")
def test_login_command_force(mock_get_auth):
    """Test login command with force flag."""
    mock_get_auth.return_value = MagicMock()

    result = runner.invoke(app, ["login", "--force"])

    assert result.exit_code == 0
    mock_get_auth.assert_called_with(force_login=True, username=None, verbose=False)


@patch("wealthgrabber.cli.get_authenticated_client")
def test_login_command_with_username(mock_get_auth):
    """Test login command with explicit username."""
    mock_get_auth.return_value = MagicMock()

    result = runner.invoke(app, ["login", "--username", "user@example.com"])

    assert result.exit_code == 0
    mock_get_auth.assert_called_with(
        force_login=False, username="user@example.com", verbose=False
    )


@patch("wealthgrabber.cli.get_authenticated_client")
def test_login_command_all_options(mock_get_auth):
    """Test login command with all options."""
    mock_get_auth.return_value = MagicMock()

    result = runner.invoke(app, ["login", "-f", "-u", "user@example.com"])

    assert result.exit_code == 0
    mock_get_auth.assert_called_with(
        force_login=True, username="user@example.com", verbose=False
    )


@patch("wealthgrabber.cli.get_authenticated_client")
def test_login_command_failure(mock_get_auth):
    """Test login command failure."""
    mock_get_auth.return_value = None

    result = runner.invoke(app, ["login"])

    assert result.exit_code == 1
    assert "Login routine failed" in result.stdout


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_accounts")
def test_list_accounts_success(mock_print, mock_get_auth):
    """Test list accounts command success."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        show_zero_balances=True,
        liquid_only=False,
        not_liquid=False,
        output_format="table",
        verbose=False,
    )  # Defaults in CLI


@patch("wealthgrabber.cli.get_authenticated_client")
def test_list_accounts_auth_fail(mock_get_auth):
    """Test list accounts authentication failure."""
    mock_get_auth.return_value = None

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 1
    assert "Could not authenticate" in result.stdout


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_accounts")
def test_list_command_full_flow(mock_print, mock_get_auth):
    """Test complete flow: auth → print_accounts."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["list"])

    # Verify command succeeded
    assert result.exit_code == 0

    # Verify print_accounts was called with correct parameters
    mock_print.assert_called_once_with(
        mock_ws,
        show_zero_balances=True,
        liquid_only=False,
        not_liquid=False,
        output_format="table",
        verbose=False,
    )


# Activities command tests


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_activities")
def test_activities_command_success(mock_print, mock_get_auth):
    """Test activities command success path."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["activities"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        dividends_only=False,
        limit=50,
        output_format="table",
        verbose=False,
        account_number=None,
        activity_type=None,
        since=None,
        until=None,
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_activities")
@patch("wealthgrabber.cli.get_account_id_by_number")
def test_activities_command_with_account(mock_get_account, mock_print, mock_get_auth):
    """Test activities command with account filter."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws
    mock_get_account.return_value = "acc-123"

    result = runner.invoke(app, ["activities", "--account", "TFSA-001"])

    assert result.exit_code == 0
    mock_get_account.assert_called_with(mock_ws, "TFSA-001")
    mock_print.assert_called_with(
        mock_ws,
        account_id="acc-123",
        dividends_only=False,
        limit=50,
        output_format="table",
        verbose=False,
        account_number="TFSA-001",
        activity_type=None,
        since=None,
        until=None,
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.get_account_id_by_number")
def test_activities_command_account_not_found(mock_get_account, mock_get_auth):
    """Test activities command when account not found."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws
    mock_get_account.return_value = None

    result = runner.invoke(app, ["activities", "--account", "INVALID-999"])

    assert result.exit_code == 1
    assert "not found" in result.stdout


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_activities")
def test_activities_command_dividends_only(mock_print, mock_get_auth):
    """Test activities command with dividends flag."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["activities", "--dividends"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        dividends_only=True,
        limit=50,
        output_format="table",
        verbose=False,
        account_number=None,
        activity_type=None,
        since=None,
        until=None,
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_activities")
def test_activities_command_with_limit(mock_print, mock_get_auth):
    """Test activities command with custom limit."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["activities", "--limit", "25"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        dividends_only=False,
        limit=25,
        output_format="table",
        verbose=False,
        account_number=None,
        activity_type=None,
        since=None,
        until=None,
    )


@patch("wealthgrabber.cli.get_authenticated_client")
def test_activities_command_auth_fail(mock_get_auth):
    """Test activities command authentication failure."""
    mock_get_auth.return_value = None

    result = runner.invoke(app, ["activities"])

    assert result.exit_code == 1
    assert "Could not authenticate" in result.stdout


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_activities")
def test_activities_command_api_error(mock_print, mock_get_auth):
    """Test activities command handles API errors."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws
    mock_print.side_effect = Exception("API Error")

    result = runner.invoke(app, ["activities"])

    assert result.exit_code == 1
    assert "Error fetching activities" in result.stdout


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_activities")
def test_activities_command_short_flags(mock_print, mock_get_auth):
    """Test activities command with short flag aliases."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["activities", "-d", "-n", "10"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        dividends_only=True,
        limit=10,
        output_format="table",
        verbose=False,
        account_number=None,
        activity_type=None,
        since=None,
        until=None,
    )


# Logout command tests


@patch("wealthgrabber.cli.auth_logout")
def test_logout_command_defaults(mock_logout):
    """Test logout command with default options."""
    result = runner.invoke(app, ["logout"])

    assert result.exit_code == 0
    mock_logout.assert_called_with(username=None, clear_email=False)


@patch("wealthgrabber.cli.auth_logout")
def test_logout_command_with_username(mock_logout):
    """Test logout command with explicit username."""
    result = runner.invoke(app, ["logout", "--username", "user@example.com"])

    assert result.exit_code == 0
    mock_logout.assert_called_with(username="user@example.com", clear_email=False)


@patch("wealthgrabber.cli.auth_logout")
def test_logout_command_clear_email(mock_logout):
    """Test logout command with clear-email flag."""
    result = runner.invoke(app, ["logout", "--clear-email"])

    assert result.exit_code == 0
    mock_logout.assert_called_with(username=None, clear_email=True)


@patch("wealthgrabber.cli.auth_logout")
def test_logout_command_all_options(mock_logout):
    """Test logout command with all options."""
    result = runner.invoke(app, ["logout", "-u", "user@example.com", "-c"])

    assert result.exit_code == 0
    mock_logout.assert_called_with(username="user@example.com", clear_email=True)


# Assets command tests


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_assets")
def test_assets_command_success(mock_print, mock_get_auth):
    """Test assets command success path."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["assets"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        by_account=False,
        output_format="table",
        verbose=False,
        pnl_filter=None,
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_assets")
def test_assets_command_with_profits_flag(mock_print, mock_get_auth):
    """Test assets command with --profits flag."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["assets", "--profits"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        by_account=False,
        output_format="table",
        verbose=False,
        pnl_filter="profit",
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_assets")
def test_assets_command_with_losses_flag(mock_print, mock_get_auth):
    """Test assets command with --losses flag."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["assets", "--losses"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        by_account=False,
        output_format="table",
        verbose=False,
        pnl_filter="loss",
    )


@patch("wealthgrabber.cli.get_authenticated_client")
def test_assets_command_both_profits_and_losses_flags(mock_get_auth):
    """Test assets command errors when both --profits and --losses are specified."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["assets", "--profits", "--losses"])

    assert result.exit_code != 0
    assert (
        "cannot be used together" in result.stdout.lower()
        or "mutually exclusive" in result.stdout.lower()
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_assets")
def test_assets_command_profits_with_short_flag(mock_print, mock_get_auth):
    """Test assets command with short -p flag for profits."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["assets", "-p"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        by_account=False,
        output_format="table",
        verbose=False,
        pnl_filter="profit",
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_assets")
def test_assets_command_losses_with_short_flag(mock_print, mock_get_auth):
    """Test assets command with short -l flag for losses."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["assets", "-l"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        by_account=False,
        output_format="table",
        verbose=False,
        pnl_filter="loss",
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_assets")
def test_assets_command_profits_with_by_account(mock_print, mock_get_auth):
    """Test assets command with --profits and --by-account flags together."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["assets", "--profits", "--by-account"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        by_account=True,
        output_format="table",
        verbose=False,
        pnl_filter="profit",
    )


# Dividends command tests


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_dividends")
def test_dividends_command_success(mock_print, mock_get_auth):
    """Test dividends command success path."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["dividends"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        since=None,
        currency="CAD",
        include_upcoming=True,
        output_format="table",
        verbose=False,
        account_label=None,
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_dividends")
@patch("wealthgrabber.cli.get_account_id_by_number")
def test_dividends_command_with_account(mock_get_account, mock_print, mock_get_auth):
    """Test dividends command with account filter."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws
    mock_get_account.return_value = "acc-123"

    result = runner.invoke(
        app, ["dividends", "--account", "TFSA-001", "--since", "2025-01-01"]
    )

    assert result.exit_code == 0
    mock_get_account.assert_called_with(mock_ws, "TFSA-001")
    mock_print.assert_called_with(
        mock_ws,
        account_id="acc-123",
        since="2025-01-01",
        currency="CAD",
        include_upcoming=True,
        output_format="table",
        verbose=False,
        account_label="TFSA-001",
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.get_account_id_by_number")
def test_dividends_command_account_not_found(mock_get_account, mock_get_auth):
    """Test dividends command when account is not found."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws
    mock_get_account.return_value = None

    result = runner.invoke(app, ["dividends", "--account", "INVALID-999"])

    assert result.exit_code == 1
    assert "not found" in result.stdout


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_dividends")
def test_dividends_command_no_upcoming(mock_print, mock_get_auth):
    """Test dividends command with --no-upcoming."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["dividends", "--no-upcoming", "--format", "json"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        since=None,
        currency="CAD",
        include_upcoming=False,
        output_format="json",
        verbose=False,
        account_label=None,
    )


@patch("wealthgrabber.cli.get_authenticated_client")
def test_dividends_command_auth_failure(mock_get_auth):
    """Test dividends command authentication failure."""
    mock_get_auth.return_value = None

    result = runner.invoke(app, ["dividends"])

    assert result.exit_code == 1
    assert "Could not authenticate" in result.stdout


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_dividends")
def test_dividends_command_api_error(mock_print, mock_get_auth):
    """Test dividends command handles API errors."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws
    mock_print.side_effect = Exception("API Error")

    result = runner.invoke(app, ["dividends"])

    assert result.exit_code == 1
    assert "Error fetching dividends" in result.stdout


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_activities")
def test_activities_command_since_until_type(mock_print, mock_get_auth):
    """Test activities command date and type filters."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(
        app,
        [
            "activities",
            "--since",
            "2026-01-01",
            "--until",
            "2026-03-31",
            "--type",
            "DIY_BUY",
        ],
    )

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        dividends_only=False,
        limit=50,
        output_format="table",
        verbose=False,
        account_number=None,
        activity_type="DIY_BUY",
        since="2026-01-01",
        until="2026-03-31",
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_networth")
def test_networth_command_success(mock_print, mock_get_auth):
    """Test networth command success path."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(
        app, ["networth", "--scope", "own", "--days", "90", "--accounts"]
    )

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        scope="OWN",
        currency="CAD",
        days=90,
        include_accounts=True,
        output_format="table",
        verbose=False,
    )


@patch("wealthgrabber.cli.get_authenticated_client")
def test_networth_command_auth_failure(mock_get_auth):
    """Test networth command authentication failure."""
    mock_get_auth.return_value = None
    result = runner.invoke(app, ["networth"])
    assert result.exit_code == 1
    assert "Could not authenticate" in result.stdout


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_performance")
def test_performance_command_success(mock_print, mock_get_auth):
    """Test performance command success path."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws

    result = runner.invoke(app, ["performance", "--since", "2026-01-01"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id=None,
        since="2026-01-01",
        currency="CAD",
        output_format="table",
        verbose=False,
        account_label=None,
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.print_performance")
@patch("wealthgrabber.cli.get_account_id_by_number")
def test_performance_command_with_account(mock_get_account, mock_print, mock_get_auth):
    """Test performance command with account filter."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws
    mock_get_account.return_value = "acc-123"

    result = runner.invoke(app, ["performance", "--account", "TFSA-001"])

    assert result.exit_code == 0
    mock_print.assert_called_with(
        mock_ws,
        account_id="acc-123",
        since=None,
        currency="CAD",
        output_format="table",
        verbose=False,
        account_label="TFSA-001",
    )


@patch("wealthgrabber.cli.get_authenticated_client")
@patch("wealthgrabber.cli.get_account_id_by_number")
def test_performance_command_account_not_found(mock_get_account, mock_get_auth):
    """Test performance command when account is not found."""
    mock_ws = MagicMock()
    mock_get_auth.return_value = mock_ws
    mock_get_account.return_value = None

    result = runner.invoke(app, ["performance", "--account", "INVALID-999"])

    assert result.exit_code == 1
    assert "not found" in result.stdout


# Version option tests


def test_version_option():
    """Test --version prints version and exits successfully."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "wealthgrabber version" in result.stdout
    # Version comes from package metadata (0.1.2 in pyproject.toml)
    assert "0.1.2" in result.stdout or "unknown" in result.stdout


def test_version_short_option():
    """Test -V short flag for version also works."""
    result = runner.invoke(app, ["-V"])

    assert result.exit_code == 0
    assert "wealthgrabber version" in result.stdout
