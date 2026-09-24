from datetime import datetime, timedelta

from ws_api import WealthsimpleAPI

from .formatters import get_formatter
from .models import (
    NetWorthAccountRow,
    NetWorthExternalRow,
    NetWorthPoint,
    NetWorthReport,
)


def _money_amount(value: object) -> float:
    """Extract a numeric amount from a Money-like value."""
    if value is None:
        return 0.0
    if isinstance(value, dict):
        return float(value.get("amount") or 0)
    return float(value or 0)


def _money_currency(value: object, default: str = "CAD") -> str:
    if isinstance(value, dict):
        return value.get("currency") or default
    return default


def _account_row(account: dict, default_currency: str) -> NetWorthAccountRow:
    description = account.get("description") or account.get("nickname") or "Account"
    number = account.get("number") or account.get("id") or "N/A"
    combined = (account.get("financials") or {}).get("currentCombined") or {}
    nlv = (
        combined.get("netLiquidationValueV2")
        or combined.get("netLiquidationValue")
        or {}
    )
    return NetWorthAccountRow(
        description=description,
        number=number,
        value=_money_amount(nlv),
        currency=_money_currency(nlv, default_currency),
    )


def _external_row(entity: dict, default_currency: str) -> NetWorthExternalRow:
    balance = entity.get("balance") or {}
    return NetWorthExternalRow(
        name=entity.get("displayName") or entity.get("name") or "External",
        institution=entity.get("institutionName") or "",
        entity_type=entity.get("entityType") or "",
        amount=_money_amount(balance),
        currency=_money_currency(balance, entity.get("currency") or default_currency),
    )


def _history_points(raw_history: object, default_currency: str) -> list[NetWorthPoint]:
    points: list[NetWorthPoint] = []
    if not isinstance(raw_history, list):
        return points
    for item in raw_history:
        balance = item.get("balance") or {}
        date_str = (item.get("date") or "")[:10]
        if not date_str:
            continue
        points.append(
            NetWorthPoint(
                date=date_str,
                amount=_money_amount(balance),
                currency=_money_currency(balance, default_currency),
            )
        )
    points.sort(key=lambda point: point.date)
    return points


def get_networth_data(
    ws: WealthsimpleAPI,
    scope: str = "HOUSEHOLD",
    currency: str = "CAD",
    days: int = 30,
    include_accounts: bool = False,
) -> NetWorthReport:
    """Fetch current net worth and history.

    Args:
        ws: Authenticated WealthsimpleAPI client
        scope: HOUSEHOLD or OWN
        currency: Currency for amounts
        days: Number of days of history
        include_accounts: Whether to include WS and external account rows
    """
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

    accounts_payload = ws.get_net_worth_accounts() or {}
    ws_accounts = accounts_payload.get("accounts") or []
    external_entities = accounts_payload.get("externalFinancialEntities") or []

    history_payload = (
        ws.get_net_worth_with_history(
            account_scope=scope,
            currency=currency,
            start_date=start_date,
            end_date=end_date,
            account_ids=[acc.get("id") for acc in ws_accounts if acc.get("id")],
            external_entity_ids=[
                entity.get("id") for entity in external_entities if entity.get("id")
            ],
        )
        or {}
    )

    current_balance = history_payload.get("balance") or {}
    current_amount = _money_amount(current_balance)
    current_currency = _money_currency(current_balance, currency)
    history = _history_points(history_payload.get("historicalDaily"), current_currency)

    start_point = history[0] if history else None
    start_amount = start_point.amount if start_point else None
    start_on = start_point.date if start_point else None
    change = current_amount - start_amount if start_amount is not None else 0.0
    change_pct = (change / start_amount * 100) if start_amount else None

    accounts: list[NetWorthAccountRow] = []
    external: list[NetWorthExternalRow] = []
    if include_accounts:
        accounts = [_account_row(acc, current_currency) for acc in ws_accounts]
        external = [
            _external_row(entity, current_currency) for entity in external_entities
        ]

    return NetWorthReport(
        scope=scope,
        currency=current_currency,
        current_amount=current_amount,
        start_date=start_on,
        start_amount=start_amount,
        change=change,
        change_pct=change_pct,
        history=history,
        accounts=accounts,
        external=external,
    )


def print_networth(
    ws: WealthsimpleAPI,
    scope: str = "HOUSEHOLD",
    currency: str = "CAD",
    days: int = 30,
    include_accounts: bool = False,
    output_format: str = "table",
    verbose: bool = False,
) -> None:
    """Fetch and print net worth."""
    if verbose:
        print("\nFetching net worth...")

    report = get_networth_data(
        ws,
        scope=scope,
        currency=currency,
        days=days,
        include_accounts=include_accounts,
    )

    if (
        report.current_amount == 0
        and not report.history
        and not report.accounts
        and not report.external
    ):
        print("No net worth data found.")
        return

    formatter = get_formatter(output_format)
    print(formatter.format_networth(report))
