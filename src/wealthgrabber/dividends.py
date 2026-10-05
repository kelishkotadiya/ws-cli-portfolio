from datetime import date
from typing import Optional

from ws_api import WealthsimpleAPI

from .formatters import get_formatter
from .models import DividendIncomeRow, DividendsReport, UpcomingDividendRow


def _money_amount(value: Optional[dict]) -> float:
    """Extract a numeric amount from a Money-like dict."""
    if not value:
        return 0.0
    return float(value.get("amount") or 0)


def _default_since() -> str:
    """January 1 of the current local year."""
    return f"{date.today().year}-01-01"


def _security_label(security: Optional[dict], fallback: str) -> tuple[str, str]:
    """Return (symbol, name), falling back to the security id."""
    stock = (security or {}).get("stock") or {}
    symbol = stock.get("symbol") or fallback
    name = stock.get("name") or fallback
    return symbol, name


def _yield_pct(raw: object) -> Optional[float]:
    """Normalize API yield to a percent value."""
    if raw is None:
        return None
    value = float(raw)
    if 0 <= value <= 1:
        return value * 100
    return value


def _date_str(value: Optional[str]) -> Optional[str]:
    """Normalize an API date to YYYY-MM-DD."""
    if not value:
        return None
    return value[:10]


def _parse_date(value: Optional[str]) -> Optional[date]:
    text = _date_str(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _is_upcoming_event(event: dict, as_of: date) -> bool:
    """True when ex-date or payable date is on or after as_of."""
    ex = _parse_date(event.get("exDividendDate"))
    payable = _parse_date(event.get("payableDate"))
    return (ex is not None and ex >= as_of) or (
        payable is not None and payable >= as_of
    )


def _is_cash_security(security_id: str) -> bool:
    return security_id.startswith("sec-c-")


def _position_in_account(position: dict, account_id: str) -> bool:
    accounts = position.get("accounts") or []
    return any(acc.get("id") == account_id for acc in accounts)


def _unique_holding_ids(positions: list, account_id: Optional[str]) -> list[str]:
    """Deduplicate held security ids, skipping cash."""
    seen: set[str] = set()
    ids: list[str] = []
    for position in positions:
        if account_id and not _position_in_account(position, account_id):
            continue
        security = position.get("security") or {}
        security_id = security.get("id") or ""
        if not security_id or _is_cash_security(security_id) or security_id in seen:
            continue
        seen.add(security_id)
        ids.append(security_id)
    return ids


def _income_rows(
    payload: Optional[dict], currency: str
) -> tuple[float, list[DividendIncomeRow]]:
    if not payload:
        return 0.0, []

    total = _money_amount(payload.get("totalValue"))
    breakdown = payload.get("issuingSecurityBreakdown") or []
    rows: list[DividendIncomeRow] = []
    for item in breakdown:
        security = item.get("security") or {}
        fallback = security.get("id") or "Unknown"
        symbol, name = _security_label(security, fallback)
        amount = _money_amount(item.get("totalValue"))
        row_currency = (item.get("totalValue") or {}).get("currency") or currency
        rows.append(
            DividendIncomeRow(
                symbol=symbol,
                name=name,
                amount=amount,
                currency=row_currency,
            )
        )
    rows.sort(key=lambda row: row.amount, reverse=True)
    return total, rows


def _upcoming_rows_for_security(
    security_id: str,
    details: dict,
    as_of: date,
    market_data: Optional[dict] = None,
) -> list[UpcomingDividendRow]:
    stock = details.get("stock") or {}
    symbol, name = _security_label(details, security_id)
    market_stock = (market_data or {}).get("stock") or {}
    if symbol == security_id:
        symbol = market_stock.get("symbol") or security_id
    if name == security_id:
        name = market_stock.get("name") or market_stock.get("symbol") or security_id
    frequency = stock.get("dividendFrequency")
    fundamentals = details.get("fundamentals") or {}
    yield_pct = _yield_pct(fundamentals.get("yield"))
    events = details.get("events") or []

    rows: list[UpcomingDividendRow] = []
    for event in events:
        if not _is_upcoming_event(event, as_of):
            continue
        rows.append(
            UpcomingDividendRow(
                symbol=symbol,
                name=name,
                yield_pct=yield_pct,
                frequency=frequency,
                ex_date=_date_str(event.get("exDividendDate")),
                record_date=_date_str(event.get("recordDate")),
                payable_date=_date_str(event.get("payableDate")),
            )
        )

    has_unannounced_event = not events or any(
        _parse_date(event.get("exDividendDate")) is None
        and _parse_date(event.get("payableDate")) is None
        for event in events
    )
    if not rows and yield_pct is not None and yield_pct > 0 and has_unannounced_event:
        rows.append(
            UpcomingDividendRow(
                symbol=symbol,
                name=name,
                yield_pct=yield_pct,
                frequency=frequency,
                ex_date=None,
                record_date=None,
                payable_date=None,
            )
        )

    return rows


def get_dividends_data(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    since: Optional[str] = None,
    currency: str = "CAD",
    include_upcoming: bool = True,
    account_label: Optional[str] = None,
    verbose: bool = False,
    as_of: Optional[date] = None,
) -> DividendsReport:
    """Fetch dividend income and optional upcoming announced dates.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Optional account ID to filter income and holdings
        since: Start date YYYY-MM-DD; defaults to January 1 of this year
        currency: Currency for amounts and yield
        include_upcoming: Whether to look up announced dates on holdings
        account_label: Optional account number/label for output
        verbose: Print progress while looking up holdings
        as_of: Date used to decide which events are upcoming (default today)
    """
    start_date = since or _default_since()
    account_ids = [account_id] if account_id else None
    today = as_of or date.today()

    payload = ws.get_dividends(
        currency,
        account_ids,
        start_date,
        include_issuing_security_breakdown=True,
    )
    total, income = _income_rows(payload, currency)

    upcoming: list[UpcomingDividendRow] = []
    if include_upcoming:
        positions = ws.get_identity_positions(None, currency) or []
        holding_ids = _unique_holding_ids(positions, account_id)
        if verbose:
            print(f"Checking announced dates for {len(holding_ids)} holdings...")
        for security_id in holding_ids:
            try:
                details = ws.get_security_dividend_details(security_id, currency)
            except Exception:
                continue
            if not details:
                continue
            stock = details.get("stock") or {}
            market_data = None
            if not stock.get("symbol") or not stock.get("name"):
                try:
                    market_data = ws.get_security_market_data(
                        security_id, use_cache=False
                    )
                except Exception:
                    pass
            upcoming.extend(
                _upcoming_rows_for_security(
                    security_id, details, today, market_data=market_data
                )
            )
        upcoming.sort(key=lambda row: row.symbol or row.ex_date or row.payable_date or "")

    return DividendsReport(
        since=start_date,
        currency=currency,
        total_amount=total,
        income=income,
        upcoming=upcoming,
        account_label=account_label,
    )


def print_dividends(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    since: Optional[str] = None,
    currency: str = "CAD",
    include_upcoming: bool = True,
    output_format: str = "table",
    verbose: bool = False,
    account_label: Optional[str] = None,
    as_of: Optional[date] = None,
) -> None:
    """Fetch and print dividend income and upcoming dates."""
    if verbose:
        print("\nFetching dividend income...")

    report = get_dividends_data(
        ws,
        account_id=account_id,
        since=since,
        currency=currency,
        include_upcoming=include_upcoming,
        account_label=account_label,
        verbose=verbose,
        as_of=as_of,
    )

    if not report.income and not report.upcoming:
        print("No dividend data found.")
        return

    formatter = get_formatter(output_format)
    print(formatter.format_dividends(report))
