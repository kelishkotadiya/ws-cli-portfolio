"""Data models for wealthgrabber output formatting."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AccountData:
    """Container for formatted account data."""

    description: str
    number: str
    value: float
    currency: str
    net_deposits: float = 0.0
    return_amount: float = 0.0
    return_rate: Optional[float] = None


@dataclass
class ActivityData:
    """Container for formatted activity data."""

    date: str  # YYYY-MM-DD format
    activity_type: str
    description: str
    amount: float
    currency: str
    sign: str  # "+" or "-"
    account_label: Optional[str] = None
    fees: Optional[float] = None
    fx_rate: Optional[float] = None
    realized_pnl: Optional[float] = None
    withholding_tax: Optional[float] = None
    asset_symbol: Optional[str] = None
    merchant: Optional[str] = None


@dataclass
class PositionData:
    """Container for formatted position data."""

    symbol: str
    name: str
    quantity: float
    market_value: float
    book_value: float
    currency: str
    pnl: float
    pnl_pct: float
    account_label: Optional[str] = None


@dataclass
class DividendIncomeRow:
    """Per-security dividend income over a period."""

    symbol: str
    name: str
    amount: float
    currency: str


@dataclass
class UpcomingDividendRow:
    """Announced dividend event for a held security."""

    symbol: str
    name: str
    yield_pct: Optional[float]
    frequency: Optional[str]
    ex_date: Optional[str]
    record_date: Optional[str]
    payable_date: Optional[str]


@dataclass
class DividendsReport:
    """Received income plus upcoming announced dividends."""

    since: str
    currency: str
    total_amount: float
    income: list[DividendIncomeRow]
    upcoming: list[UpcomingDividendRow]
    account_label: Optional[str] = None


@dataclass
class NetWorthPoint:
    """One historical net-worth observation."""

    date: str
    amount: float
    currency: str


@dataclass
class NetWorthAccountRow:
    """Wealthsimple account included in net worth."""

    description: str
    number: str
    value: float
    currency: str


@dataclass
class NetWorthExternalRow:
    """Linked external account included in net worth."""

    name: str
    institution: str
    entity_type: str
    amount: float
    currency: str


@dataclass
class NetWorthReport:
    """Current net worth plus optional history and account breakdown."""

    scope: str
    currency: str
    current_amount: float
    start_date: Optional[str]
    start_amount: Optional[float]
    change: float
    change_pct: Optional[float]
    history: list[NetWorthPoint]
    accounts: list[NetWorthAccountRow]
    external: list[NetWorthExternalRow]


@dataclass
class RealizedSecurityRow:
    """Realized return for one security."""

    symbol: str
    name: str
    amount: float
    currency: str


@dataclass
class UnrealizedAccountRow:
    """Unrealized P&L for one account."""

    account_label: str
    amount: float
    rate: Optional[float]
    currency: str


@dataclass
class PerformancePoint:
    """One historical performance observation."""

    date: str
    net_liquidation: float
    net_deposits: float
    currency: str


@dataclass
class PerformanceReport:
    """Identity-level performance over a period."""

    since: str
    currency: str
    net_liquidation: float
    net_deposits: float
    return_amount: float
    return_rate: Optional[float]
    return_as_of: Optional[str]
    realized_total: float
    realized: list[RealizedSecurityRow]
    unrealized: list[UnrealizedAccountRow]
    history: list[PerformancePoint]
    account_label: Optional[str] = None
