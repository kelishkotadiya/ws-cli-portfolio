from datetime import date, datetime
from typing import Optional

from ws_api import WealthsimpleAPI

from .formatters import get_formatter
from .models import (
    PerformancePoint,
    PerformanceReport,
    RealizedSecurityRow,
    UnrealizedAccountRow,
)


def _money_amount(value: object) -> float:
    """Extract a numeric amount from a Money-like value."""
    if value is None:
        return 0.0
    if isinstance(value, dict):
        nested = value.get("amount")
        if isinstance(nested, dict):
            return float(nested.get("amount") or 0)
        return float(nested or 0)
    return float(value or 0)


def _money_currency(value: object, default: str = "CAD") -> str:
    if isinstance(value, dict):
        nested = value.get("amount")
        if isinstance(nested, dict) and nested.get("currency"):
            return nested["currency"]
        return value.get("currency") or default
    return default


def _rate_pct(raw: object) -> Optional[float]:
    """Normalize a rate to percent. Values in [-1, 1] are treated as fractions."""
    if raw is None:
        return None
    value = float(raw)
    if abs(value) <= 1:
        return value * 100
    return value


def _default_since() -> str:
    return f"{date.today().year}-01-01"


def _breakdown_nodes(breakdown: object) -> list[dict]:
    if not breakdown:
        return []
    if isinstance(breakdown, list):
        return breakdown
    if isinstance(breakdown, dict):
        edges = breakdown.get("edges") or []
        nodes = []
        for edge in edges:
            if isinstance(edge, dict) and "node" in edge:
                nodes.append(edge["node"])
            elif isinstance(edge, dict):
                nodes.append(edge)
        return nodes
    return []


def _realized_rows(
    payload: Optional[dict], currency: str
) -> tuple[float, list[RealizedSecurityRow]]:
    if not payload:
        return 0.0, []
    total = _money_amount(payload.get("totalValue"))
    rows: list[RealizedSecurityRow] = []
    for item in _breakdown_nodes(payload.get("securityBreakdown")):
        security = item.get("security") or {}
        stock = security.get("stock") or {}
        fallback = security.get("id") or "Unknown"
        rows.append(
            RealizedSecurityRow(
                symbol=stock.get("symbol") or fallback,
                name=stock.get("name") or fallback,
                amount=_money_amount(item.get("totalValue")),
                currency=_money_currency(item.get("totalValue"), currency),
            )
        )
    rows.sort(key=lambda row: row.amount, reverse=True)
    return total, rows


def _history_points(raw_history: object, currency: str) -> list[PerformancePoint]:
    points: list[PerformancePoint] = []
    if not isinstance(raw_history, list):
        return points
    for item in raw_history:
        nlv = item.get("netLiquidationValueV2") or item.get("netLiquidationValue") or {}
        deposits = item.get("netDepositsV2") or item.get("netDeposits") or {}
        date_str = (item.get("date") or "")[:10]
        if not date_str:
            continue
        points.append(
            PerformancePoint(
                date=date_str,
                net_liquidation=_money_amount(nlv),
                net_deposits=_money_amount(deposits),
                currency=_money_currency(nlv, currency),
            )
        )
    points.sort(key=lambda point: point.date)
    return points


def _unrealized_rows(
    ws: WealthsimpleAPI,
    currency: str,
    account_id: Optional[str],
) -> list[UnrealizedAccountRow]:
    accounts = ws.get_accounts() or []
    rows: list[UnrealizedAccountRow] = []
    for account in accounts:
        acc_id = account.get("id")
        if not acc_id:
            continue
        if account_id and acc_id != account_id:
            continue
        try:
            pnl = ws.get_account_unrealized_pnl(acc_id, currency) or {}
        except Exception:
            continue
        amount_obj = pnl.get("amount") if isinstance(pnl, dict) else None
        label = (
            f"{account.get('description', 'Unknown')} "
            f"({account.get('number', 'N/A')})"
        )
        rows.append(
            UnrealizedAccountRow(
                account_label=label,
                amount=_money_amount(amount_obj if amount_obj is not None else pnl),
                rate=_rate_pct(pnl.get("rate") if isinstance(pnl, dict) else None),
                currency=_money_currency(
                    amount_obj if isinstance(amount_obj, dict) else pnl, currency
                ),
            )
        )
    return rows


def get_performance_data(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    since: Optional[str] = None,
    currency: str = "CAD",
    account_label: Optional[str] = None,
) -> PerformanceReport:
    """Fetch identity performance, realized returns, history, and unrealized P&L."""
    start = since or _default_since()
    account_ids = [account_id] if account_id else None
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.today()

    current = ws.get_identity_current_financials(currency, account_ids, start) or {}
    nlv = (
        current.get("netLiquidationValueV2") or current.get("netLiquidationValue") or {}
    )
    deposits = current.get("netDeposits") or current.get("netDepositsV2") or {}
    simple = current.get("simpleReturns") or {}
    return_amount = _money_amount(
        simple.get("amount") if isinstance(simple, dict) else None
    )
    return_rate = _rate_pct(simple.get("rate") if isinstance(simple, dict) else None)
    return_as_of = None
    if isinstance(simple, dict) and simple.get("asOf"):
        return_as_of = str(simple["asOf"])[:10]

    realized_payload = ws.get_identity_realized_returns(currency, account_ids, start)
    realized_total, realized = _realized_rows(realized_payload, currency)

    raw_history = ws.get_identity_historical_financials(
        account_ids=account_ids,
        currency=currency,
        start_date=start_dt,
        end_date=end_dt,
        first=400,
    )
    history = _history_points(raw_history, currency)
    unrealized = _unrealized_rows(ws, currency, account_id)

    return PerformanceReport(
        since=start,
        currency=_money_currency(nlv, currency),
        net_liquidation=_money_amount(nlv),
        net_deposits=_money_amount(deposits),
        return_amount=return_amount,
        return_rate=return_rate,
        return_as_of=return_as_of,
        realized_total=realized_total,
        realized=realized,
        unrealized=unrealized,
        history=history,
        account_label=account_label,
    )


def print_performance(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    since: Optional[str] = None,
    currency: str = "CAD",
    output_format: str = "table",
    verbose: bool = False,
    account_label: Optional[str] = None,
) -> None:
    """Fetch and print performance."""
    if verbose:
        print("\nFetching performance...")

    report = get_performance_data(
        ws,
        account_id=account_id,
        since=since,
        currency=currency,
        account_label=account_label,
    )

    if (
        report.net_liquidation == 0
        and report.net_deposits == 0
        and report.return_amount == 0
        and not report.realized
        and not report.unrealized
        and not report.history
    ):
        print("No performance data found.")
        return

    formatter = get_formatter(output_format)
    print(formatter.format_performance(report))
