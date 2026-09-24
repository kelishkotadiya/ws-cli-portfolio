import re
from datetime import datetime
from typing import Optional

from ws_api import WealthsimpleAPI

from .formatters import get_formatter
from .models import ActivityData

DIVIDEND_TYPES = {"DIY_DIVIDEND", "DIVIDEND", "DISTRIBUTION"}


def is_dividend_activity(activity: dict) -> bool:
    """Check if activity is a dividend."""
    act_type = activity.get("type", "").upper()
    description = activity.get("description", "").upper()
    return any(div in act_type or div in description for div in DIVIDEND_TYPES)


def get_account_id_by_number(ws: WealthsimpleAPI, account_number: str) -> Optional[str]:
    """Look up account ID by account number."""
    accounts = ws.get_accounts()
    for account in accounts:
        if account.get("number") == account_number:
            return account.get("id")
    return None


def _get_security_name(ws: WealthsimpleAPI, security_id: str, cache: dict) -> str:
    """Get name for a security, using cache to avoid redundant API calls."""
    if security_id in cache:
        return cache[security_id]

    name = security_id  # Fallback to ID if lookup fails

    if security_id:
        try:
            market_data = ws.get_security_market_data(security_id, use_cache=False)
            if market_data and market_data.get("stock"):
                stock = market_data["stock"]
                symbol = stock.get("symbol", "")
                stock_name = stock.get("name", "")
                # Prefer symbol if available, otherwise use name
                name = symbol if symbol else (stock_name if stock_name else security_id)
        except Exception:
            # Fallback for securities that can't be looked up
            pass

    cache[security_id] = name
    return name


def _enhance_description(
    ws: WealthsimpleAPI, activity: dict, security_cache: dict
) -> str:
    """Enhance activity description by replacing security IDs with names."""
    description = activity.get("description", "N/A")

    # First, check if the activity has a direct security reference
    security = activity.get("security")
    security_id = None

    if security:
        security_id = security.get("id") if isinstance(security, dict) else security

    # If no direct security reference, try to extract from description
    # Look for patterns like [sec-s-XXXX or sec-s-XXXX
    if not security_id:
        # Try to find security ID in description
        match = re.search(r"\[?(sec-[a-z]-[a-f0-9]+)", description)
        if match:
            security_id = match.group(1)

    if security_id:
        security_name = _get_security_name(ws, security_id, security_cache)
        # Replace the security ID with the name in the description
        description = re.sub(r"\[?(sec-[a-z]-[a-f0-9]+)\]?", security_name, description)

        # For DIY_BUY activities that might not have security in description,
        # append the security name
        if "DIY_BUY" in activity.get("type", "") and security_name not in description:
            # Extract the quantity if present
            qty_match = re.search(r"buy (\d+\.?\d*)", description)
            if qty_match:
                description = (
                    f"Dividend reinvestment: buy {qty_match.group(1)} {security_name}"
                )

    return description


def _optional_float(value: object) -> Optional[float]:
    """Parse an optional numeric/Money field."""
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        raw = value.get("amount")
        if raw is None:
            return None
        return float(raw)
    return float(value)


def _matches_activity_type(activity: dict, activity_type: str) -> bool:
    needle = activity_type.upper()
    return needle in (activity.get("type") or "").upper()


def _as_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d")


def _transform_activity(
    ws: WealthsimpleAPI,
    activity: dict,
    security_cache: dict,
    account_label: Optional[str] = None,
) -> ActivityData:
    """Transform raw activity dict to ActivityData.

    Args:
        ws: Authenticated WealthsimpleAPI client
        activity: Raw activity dict from API
        security_cache: Cache for security lookups
        account_label: Optional account label for grouping

    Returns:
        ActivityData object
    """
    date_str = _format_date(activity.get("occurredAt", ""))
    act_type = activity.get("type", "N/A")[:14]
    description = _enhance_description(ws, activity, security_cache)[:34]
    amount = float(activity.get("amount") or 0)
    currency = activity.get("currency", "CAD")
    sign = "+" if activity.get("amountSign") == "positive" else "-"

    return ActivityData(
        date=date_str,
        activity_type=act_type,
        description=description,
        amount=amount,
        currency=currency,
        sign=sign,
        account_label=account_label,
        fees=_optional_float(activity.get("fees")),
        fx_rate=_optional_float(activity.get("fxRate")),
        realized_pnl=_optional_float(activity.get("realizedPnl")),
        withholding_tax=_optional_float(activity.get("withholdingTaxAmount")),
        asset_symbol=activity.get("assetSymbol") or None,
        merchant=activity.get("spendMerchant") or None,
    )


def _fetch_raw_activities(
    ws: WealthsimpleAPI,
    account_id: str,
    limit: int,
    dividends_only: bool,
    activity_type: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> list:
    """Fetch and filter raw activities for one account."""
    kwargs: dict = {}
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date

    needs_filter = dividends_only or bool(activity_type)
    if needs_filter:
        kwargs["load_all"] = True
        activities = ws.get_activities(account_id, **kwargs)
        if dividends_only:
            activities = [a for a in activities if is_dividend_activity(a)]
        if activity_type:
            activities = [
                a for a in activities if _matches_activity_type(a, activity_type)
            ]
        return activities[:limit]

    kwargs["how_many"] = limit
    activities = ws.get_activities(account_id, **kwargs)
    return activities[:limit]


def _process_account_activities(
    ws: WealthsimpleAPI,
    account_id: str,
    account_label: Optional[str],
    security_cache: dict,
    dividends_only: bool,
    limit: int,
    activity_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list[ActivityData]:
    """Process activities for a single account.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Account ID to fetch activities for
        account_label: Optional label for grouping (e.g., "TFSA (ACC-001)")
        security_cache: Shared cache for security lookups
        dividends_only: Whether to filter for dividend activities only
        limit: Maximum number of activities to return
        activity_type: Optional substring filter on activity type
        start_date: Optional start datetime forwarded to the API
        end_date: Optional end datetime forwarded to the API

    Returns:
        List of ActivityData objects for the account
    """
    activities = _fetch_raw_activities(
        ws,
        account_id,
        limit,
        dividends_only,
        activity_type,
        start_date,
        end_date,
    )

    return [
        _transform_activity(ws, act, security_cache, account_label)
        for act in activities
    ]


def get_activities_data(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    dividends_only: bool = False,
    limit: int = 50,
    account_number: Optional[str] = None,
    activity_type: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> list[ActivityData]:
    """Fetch and transform activity data.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Optional account ID to filter activities
        dividends_only: Whether to include only dividend activities
        limit: Maximum number of activities per account
        account_number: Optional account number for labeling in single-account mode
        activity_type: Optional substring filter on activity type
        since: Optional start date YYYY-MM-DD
        until: Optional end date YYYY-MM-DD

    Returns:
        List of ActivityData objects
    """
    result = []
    security_cache: dict[str, str] = {}
    start_date = _as_datetime(since)
    end_date = _as_datetime(until)

    if account_id:
        # Single account mode: use account number as label if provided
        result = _process_account_activities(
            ws,
            account_id,
            account_number,
            security_cache,
            dividends_only,
            limit,
            activity_type,
            start_date,
            end_date,
        )
    else:
        # All accounts mode - fetch accounts for labeling
        accounts = ws.get_accounts()
        if not accounts:
            return []

        for account in accounts:
            acc_id = account.get("id")
            acc_label = f"{account.get('description', 'Unknown')} ({account.get('number', 'N/A')})"
            result.extend(
                _process_account_activities(
                    ws,
                    acc_id,
                    acc_label,
                    security_cache,
                    dividends_only,
                    limit,
                    activity_type,
                    start_date,
                    end_date,
                )
            )

    return result


def print_activities(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    dividends_only: bool = False,
    limit: int = 50,
    output_format: str = "table",
    verbose: bool = False,
    account_number: Optional[str] = None,
    activity_type: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> None:
    """Fetch and print activities.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Optional account ID to filter activities
        dividends_only: Whether to show only dividend activities
        limit: Maximum number of activities per account
        output_format: Output format - 'table', 'json', or 'csv' (default 'table')
        verbose: If True, print status messages during execution
        account_number: Optional account number for labeling in single-account mode
        activity_type: Optional substring filter on activity type
        since: Optional start date YYYY-MM-DD
        until: Optional end date YYYY-MM-DD
    """
    if verbose:
        print("\nFetching activities...")

    activities_data = get_activities_data(
        ws,
        account_id,
        dividends_only,
        limit,
        account_number,
        activity_type,
        since,
        until,
    )

    if not activities_data:
        print("No activities found.")
        return

    formatter = get_formatter(output_format)
    print(formatter.format_activities(activities_data))


def _format_date(iso_date: str) -> str:
    """Format ISO date to YYYY-MM-DD."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso_date[:10] if len(iso_date) >= 10 else "N/A"
