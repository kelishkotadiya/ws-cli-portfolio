"""Output formatters for different data formats."""

import csv
import json
from dataclasses import asdict
from io import StringIO
from typing import Optional, Protocol, Sequence

from .models import (
    AccountData,
    ActivityData,
    DividendIncomeRow,
    DividendsReport,
    NetWorthReport,
    PerformanceReport,
    PositionData,
    UpcomingDividendRow,
)


def _calculate_position_totals(
    positions: Sequence[PositionData],
) -> tuple[float, float, float, float]:
    """Calculate total position values and P&L.

    Args:
        positions: Sequence of positions

    Returns:
        Tuple of (total_value, total_book, total_pnl, total_pnl_pct)
    """
    total_value = sum(p.market_value for p in positions)
    total_book = sum(p.book_value for p in positions)
    total_pnl = total_value - total_book
    total_pnl_pct = (total_pnl / total_book * 100) if total_book != 0 else 0.0
    return total_value, total_book, total_pnl, total_pnl_pct


class FormatterProtocol(Protocol):
    """Protocol for data formatters."""

    def format_accounts(self, accounts: Sequence[AccountData]) -> str:
        """Format account data."""
        ...

    def format_activities(self, activities: Sequence[ActivityData]) -> str:
        """Format activity data."""
        ...

    def format_positions(
        self,
        positions: Sequence[PositionData],
        show_totals: bool = True,
        group_label: Optional[str] = None,
    ) -> str:
        """Format position data."""
        ...

    def format_dividends(self, report: DividendsReport) -> str:
        """Format dividend income and upcoming dates."""
        ...

    def format_networth(self, report: NetWorthReport) -> str:
        """Format net worth data."""
        ...

    def format_performance(self, report: PerformanceReport) -> str:
        """Format performance data."""
        ...


class TableFormatter:
    """Format data as aligned ASCII tables."""

    @staticmethod
    def _format_position_row(pos: PositionData) -> str:
        """Format a single position as a table row.

        Args:
            pos: Position data

        Returns:
            Formatted row string
        """
        pnl_str = f"{'+' if pos.pnl >= 0 else ''}{pos.pnl:,.2f}"
        pnl_pct_str = f"{'+' if pos.pnl_pct >= 0 else ''}{pos.pnl_pct:.1f}%"
        return (
            f"{pos.symbol:<10} {pos.name:<30} {pos.quantity:>10.2f} "
            f"{pos.market_value:>12,.2f} {pos.currency} {pnl_str:>13} {pnl_pct_str:>8}"
        )

    @staticmethod
    def _format_totals_row(
        total_value: float,
        total_pnl: float,
        total_pnl_pct: float,
        label: str,
        currency: str,
    ) -> str:
        """Format totals as a table row.

        Args:
            total_value: Total market value
            total_pnl: Total P&L
            total_pnl_pct: Total P&L percentage
            label: Row label
            currency: Currency code

        Returns:
            Formatted totals row
        """
        pnl_str = f"{'+' if total_pnl >= 0 else ''}{total_pnl:,.2f}"
        pnl_pct_str = f"{'+' if total_pnl_pct >= 0 else ''}{total_pnl_pct:.1f}%"
        return f"{label:<51} {total_value:>13,.2f} {currency} {pnl_str:>13} {pnl_pct_str:>8}"

    def format_accounts(self, accounts: Sequence[AccountData]) -> str:
        """Format accounts as table with totals."""
        if not accounts:
            return "No accounts found."

        width = 108
        lines = []
        lines.append("\n" + "=" * width)
        lines.append(
            f"{'Account':<28} {'Number':<16} {'Value':>16} "
            f"{'Deposits':>14} {'Return':>14}"
        )
        lines.append("-" * width)

        total_value = 0.0
        total_deposits = 0.0
        total_return = 0.0
        for acc in accounts:
            return_str = self._format_return(acc.return_amount, acc.return_rate)
            lines.append(
                f"{acc.description[:28]:<28} {acc.number:<16} "
                f"{acc.value:>12,.2f} {acc.currency} "
                f"{acc.net_deposits:>10,.2f} {return_str:>14}"
            )
            total_value += acc.value
            total_deposits += acc.net_deposits
            total_return += acc.return_amount

        lines.append("=" * width)
        lines.append(
            f"{'Total':<45} {total_value:>12,.2f} CAD "
            f"{total_deposits:>10,.2f} {total_return:>+14,.2f}"
        )
        lines.append("=" * width)

        return "\n".join(lines)

    @staticmethod
    def _format_return(amount: float, rate: Optional[float]) -> str:
        if rate is None:
            return f"{amount:+,.2f}"
        return f"{amount:+,.2f} {rate:.1f}%"

    def format_activities(self, activities: Sequence[ActivityData]) -> str:
        """Format activities as table."""
        if not activities:
            return "No activities found."

        lines = []
        current_account = None

        for act in activities:
            # Print account header if account changes
            if act.account_label and act.account_label != current_account:
                if current_account is not None:
                    lines.append("=" * 80)
                lines.append("\n" + "=" * 80)
                lines.append(f"Account: {act.account_label}")
                lines.append("=" * 80)
                lines.append(
                    f"{'Date':<12} {'Type':<14} {'Description':<34} "
                    f"{'Amount':>18} {'Fees':>10} {'RPnL':>12}"
                )
                lines.append("-" * 80)
                current_account = act.account_label
            elif current_account is None:
                # First activity, no account label
                lines.append("\n" + "=" * 80)
                lines.append(
                    f"{'Date':<12} {'Type':<14} {'Description':<34} "
                    f"{'Amount':>18} {'Fees':>10} {'RPnL':>12}"
                )
                lines.append("-" * 80)
                current_account = ""

            fees = f"{act.fees:,.2f}" if act.fees is not None else ""
            rpnl = f"{act.realized_pnl:+,.2f}" if act.realized_pnl is not None else ""
            lines.append(
                f"{act.date:<12} {act.activity_type:<14} {act.description:<34} "
                f"{act.sign}{act.amount:>14,.2f} {act.currency} {fees:>10} {rpnl:>12}"
            )

        lines.append("=" * 80)
        return "\n".join(lines)

    def format_positions(
        self,
        positions: Sequence[PositionData],
        show_totals: bool = True,
        group_label: Optional[str] = None,
    ) -> str:
        """Format positions as table with P&L."""
        if not positions:
            return "No positions found."

        lines = []

        # Header
        if group_label:
            lines.append("\n" + "=" * 94)
            lines.append(f"Account: {group_label}")
            lines.append("=" * 94)
        else:
            lines.append("\n" + "=" * 94)

        lines.append(
            f"{'Symbol':<10} {'Name':<30} {'Qty':>10} "
            f"{'Market Value':>16} {'P&L':>14} {'P&L %':>8}"
        )
        lines.append("-" * 94)

        # Position rows
        for pos in positions:
            lines.append(self._format_position_row(pos))

        # Totals
        if show_totals:
            total_value, total_book, total_pnl, total_pnl_pct = (
                _calculate_position_totals(positions)
            )
            label = "Account Total" if group_label else "Total"
            currency = positions[0].currency if positions else "CAD"

            lines.append("=" * 94)
            lines.append(
                self._format_totals_row(
                    total_value, total_pnl, total_pnl_pct, label, currency
                )
            )
            lines.append("=" * 94)

        return "\n".join(lines)

    def format_dividends(self, report: DividendsReport) -> str:
        """Format dividend income and upcoming dates as a table."""
        lines: list[str] = []
        title = f"Dividends received since {report.since} ({report.currency})"
        if report.account_label:
            title = f"{title} - {report.account_label}"

        lines.append("")
        lines.append("=" * 80)
        lines.append(title)
        lines.append("=" * 80)

        if not report.income:
            lines.append(f"No dividend income since {report.since}.")
        else:
            lines.append(f"{'SYMBOL':<10} {'NAME':<32} {'AMOUNT':>18}")
            lines.append("-" * 80)
            for row in report.income:
                lines.append(self._format_income_row(row))
            lines.append("=" * 80)
            lines.append(
                f"{'TOTAL':<43} {report.total_amount:>15,.2f} {report.currency}"
            )
            lines.append("=" * 80)

        if report.upcoming:
            lines.append("")
            lines.append("=" * 94)
            lines.append("Upcoming dividends")
            lines.append("=" * 94)
            lines.append(
                f"{'SYMBOL':<10} {'NAME':<24} {'YIELD':>7} {'FREQ':<12} "
                f"{'EX':<12} {'PAYABLE':<12}"
            )
            lines.append("-" * 94)
            for row in report.upcoming:
                lines.append(self._format_upcoming_row(row))
            lines.append("=" * 94)

        return "\n".join(lines)

    @staticmethod
    def _format_income_row(row: DividendIncomeRow) -> str:
        return (
            f"{row.symbol:<10} {row.name[:32]:<32} "
            f"{row.amount:>15,.2f} {row.currency}"
        )

    @staticmethod
    def _format_upcoming_row(row: UpcomingDividendRow) -> str:
        yield_str = f"{row.yield_pct:.2f}%" if row.yield_pct is not None else ""
        frequency = row.frequency or ""
        ex_date = row.ex_date or ""
        payable = row.payable_date or ""
        return (
            f"{row.symbol:<10} {row.name[:24]:<24} {yield_str:>7} "
            f"{frequency:<12} {ex_date:<12} {payable:<12}"
        )

    def format_networth(self, report: NetWorthReport) -> str:
        """Format net worth as a summary table plus optional accounts."""
        lines = [""]
        lines.append("=" * 80)
        lines.append(f"Net worth ({report.scope}) {report.currency}")
        lines.append("=" * 80)
        lines.append(
            f"{'Current':<22} {report.current_amount:>15,.2f} {report.currency}"
        )
        if report.start_date is not None and report.start_amount is not None:
            lines.append(
                f"{'Start (' + report.start_date + ')':<22} "
                f"{report.start_amount:>15,.2f} {report.currency}"
            )
        change_pct = (
            f" ({report.change_pct:+.1f}%)" if report.change_pct is not None else ""
        )
        lines.append(
            f"{'Change':<22} {report.change:>+15,.2f} {report.currency}{change_pct}"
        )
        lines.append("=" * 80)

        if report.accounts:
            lines.append("")
            lines.append("=" * 80)
            lines.append("Wealthsimple accounts")
            lines.append("=" * 80)
            lines.append(f"{'Account':<40} {'Number':<20} {'Value':>18}")
            lines.append("-" * 80)
            for acc in report.accounts:
                lines.append(
                    f"{acc.description[:40]:<40} {acc.number:<20} "
                    f"{acc.value:>15,.2f} {acc.currency}"
                )
            lines.append("=" * 80)

        if report.external:
            lines.append("")
            lines.append("=" * 80)
            lines.append("External accounts")
            lines.append("=" * 80)
            lines.append(f"{'Name':<28} {'Institution':<22} {'Amount':>18}")
            lines.append("-" * 80)
            for entity in report.external:
                lines.append(
                    f"{entity.name[:28]:<28} {entity.institution[:22]:<22} "
                    f"{entity.amount:>15,.2f} {entity.currency}"
                )
            lines.append("=" * 80)

        return "\n".join(lines)

    def format_performance(self, report: PerformanceReport) -> str:
        """Format performance as summary plus realized and unrealized sections."""
        lines = [""]
        title = f"Performance since {report.since} ({report.currency})"
        if report.account_label:
            title = f"{title} - {report.account_label}"
        lines.append("=" * 80)
        lines.append(title)
        lines.append("=" * 80)
        lines.append(
            f"{'Net liquidation':<22} {report.net_liquidation:>15,.2f} {report.currency}"
        )
        lines.append(
            f"{'Net deposits':<22} {report.net_deposits:>15,.2f} {report.currency}"
        )
        return_str = f"{report.return_amount:>+15,.2f} {report.currency}"
        if report.return_rate is not None:
            return_str += f" ({report.return_rate:+.1f}%)"
        lines.append(f"{'Simple return':<22} {return_str}")
        lines.append(
            f"{'Realized gains':<22} {report.realized_total:>+15,.2f} {report.currency}"
        )
        lines.append("=" * 80)

        if report.realized:
            lines.append("")
            lines.append("=" * 80)
            lines.append("Realized by security")
            lines.append("=" * 80)
            lines.append(f"{'SYMBOL':<10} {'NAME':<32} {'AMOUNT':>18}")
            lines.append("-" * 80)
            for row in report.realized:
                lines.append(
                    f"{row.symbol:<10} {row.name[:32]:<32} "
                    f"{row.amount:>15,.2f} {row.currency}"
                )
            lines.append("=" * 80)

        if report.unrealized:
            lines.append("")
            lines.append("=" * 80)
            lines.append("Unrealized P&L by account")
            lines.append("=" * 80)
            lines.append(f"{'Account':<48} {'Amount':>16} {'Rate':>10}")
            lines.append("-" * 80)
            for row in report.unrealized:
                rate = f"{row.rate:.1f}%" if row.rate is not None else ""
                lines.append(
                    f"{row.account_label[:48]:<48} {row.amount:>+13,.2f} "
                    f"{row.currency} {rate:>10}"
                )
            lines.append("=" * 80)

        return "\n".join(lines)


class JsonFormatter:
    """Format data as JSON."""

    def format_accounts(self, accounts: Sequence[AccountData]) -> str:
        """Format accounts as JSON array."""
        return json.dumps([asdict(acc) for acc in accounts], indent=2)

    def format_activities(self, activities: Sequence[ActivityData]) -> str:
        """Format activities as JSON array."""
        return json.dumps([asdict(act) for act in activities], indent=2)

    def format_positions(
        self,
        positions: Sequence[PositionData],
        show_totals: bool = True,
        group_label: Optional[str] = None,
    ) -> str:
        """Format positions as JSON with optional totals."""
        data = [asdict(pos) for pos in positions]

        if show_totals and positions:
            total_value = sum(p.market_value for p in positions)
            total_book = sum(p.book_value for p in positions)
            total_pnl = total_value - total_book
            total_pnl_pct = (total_pnl / total_book * 100) if total_book != 0 else 0.0

            result = {
                "positions": data,
                "totals": {
                    "market_value": total_value,
                    "book_value": total_book,
                    "pnl": total_pnl,
                    "pnl_pct": total_pnl_pct,
                    "currency": positions[0].currency if positions else "CAD",
                },
            }
            if group_label:
                result["group"] = group_label
            return json.dumps(result, indent=2)

        return json.dumps(data, indent=2)

    def format_dividends(self, report: DividendsReport) -> str:
        """Format dividend report as a JSON object."""
        return json.dumps(asdict(report), indent=2)

    def format_networth(self, report: NetWorthReport) -> str:
        """Format net worth as a JSON object."""
        return json.dumps(asdict(report), indent=2)

    def format_performance(self, report: PerformanceReport) -> str:
        """Format performance as a JSON object."""
        return json.dumps(asdict(report), indent=2)


class CsvFormatter:
    """Format data as CSV."""

    def format_accounts(self, accounts: Sequence[AccountData]) -> str:
        """Format accounts as CSV."""
        if not accounts:
            return ""

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "description",
                "number",
                "value",
                "currency",
                "net_deposits",
                "return_amount",
                "return_rate",
            ]
        )

        # Write data
        for acc in accounts:
            writer.writerow(
                [
                    acc.description,
                    acc.number,
                    acc.value,
                    acc.currency,
                    acc.net_deposits,
                    acc.return_amount,
                    acc.return_rate if acc.return_rate is not None else "",
                ]
            )

        return output.getvalue()

    def format_activities(self, activities: Sequence[ActivityData]) -> str:
        """Format activities as CSV."""
        if not activities:
            return ""

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "date",
                "activity_type",
                "description",
                "amount",
                "currency",
                "sign",
                "account_label",
                "fees",
                "fx_rate",
                "realized_pnl",
                "withholding_tax",
                "asset_symbol",
                "merchant",
            ]
        )

        # Write data
        for act in activities:
            writer.writerow(
                [
                    act.date,
                    act.activity_type,
                    act.description,
                    act.amount,
                    act.currency,
                    act.sign,
                    act.account_label or "",
                    act.fees if act.fees is not None else "",
                    act.fx_rate if act.fx_rate is not None else "",
                    act.realized_pnl if act.realized_pnl is not None else "",
                    act.withholding_tax if act.withholding_tax is not None else "",
                    act.asset_symbol or "",
                    act.merchant or "",
                ]
            )

        return output.getvalue()

    def format_positions(
        self,
        positions: Sequence[PositionData],
        show_totals: bool = True,
        group_label: Optional[str] = None,
    ) -> str:
        """Format positions as CSV."""
        if not positions:
            return ""

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "symbol",
                "name",
                "quantity",
                "market_value",
                "book_value",
                "currency",
                "pnl",
                "pnl_pct",
                "account_label",
            ]
        )

        # Write data
        for pos in positions:
            writer.writerow(
                [
                    pos.symbol,
                    pos.name,
                    pos.quantity,
                    pos.market_value,
                    pos.book_value,
                    pos.currency,
                    pos.pnl,
                    pos.pnl_pct,
                    pos.account_label or "",
                ]
            )

        # Optionally add totals row
        if show_totals and positions:
            total_value, total_book, total_pnl, total_pnl_pct = (
                _calculate_position_totals(positions)
            )
            currency = positions[0].currency if positions else "CAD"

            writer.writerow(
                [
                    "TOTAL",
                    "",
                    sum(p.quantity for p in positions),
                    total_value,
                    total_book,
                    currency,
                    total_pnl,
                    total_pnl_pct,
                    group_label or "",
                ]
            )

        return output.getvalue()

    def format_dividends(self, report: DividendsReport) -> str:
        """Format dividend report as one or two CSV tables."""
        output = StringIO()
        writer = csv.writer(output)

        if report.income:
            writer.writerow(["symbol", "name", "amount", "currency"])
            for row in report.income:
                writer.writerow([row.symbol, row.name, row.amount, row.currency])

        if report.income and report.upcoming:
            writer.writerow([])

        if report.upcoming:
            writer.writerow(
                [
                    "symbol",
                    "name",
                    "yield_pct",
                    "frequency",
                    "ex_date",
                    "record_date",
                    "payable_date",
                ]
            )
            for row in report.upcoming:
                writer.writerow(
                    [
                        row.symbol,
                        row.name,
                        row.yield_pct if row.yield_pct is not None else "",
                        row.frequency or "",
                        row.ex_date or "",
                        row.record_date or "",
                        row.payable_date or "",
                    ]
                )

        return output.getvalue()

    def format_networth(self, report: NetWorthReport) -> str:
        """Format net worth as summary plus history CSV tables."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "scope",
                "currency",
                "current_amount",
                "start_date",
                "start_amount",
                "change",
                "change_pct",
            ]
        )
        writer.writerow(
            [
                report.scope,
                report.currency,
                report.current_amount,
                report.start_date or "",
                report.start_amount if report.start_amount is not None else "",
                report.change,
                report.change_pct if report.change_pct is not None else "",
            ]
        )
        if report.history:
            writer.writerow([])
            writer.writerow(["date", "amount", "currency"])
            for point in report.history:
                writer.writerow([point.date, point.amount, point.currency])
        if report.accounts:
            writer.writerow([])
            writer.writerow(["description", "number", "value", "currency"])
            for acc in report.accounts:
                writer.writerow([acc.description, acc.number, acc.value, acc.currency])
        if report.external:
            writer.writerow([])
            writer.writerow(
                ["name", "institution", "entity_type", "amount", "currency"]
            )
            for entity in report.external:
                writer.writerow(
                    [
                        entity.name,
                        entity.institution,
                        entity.entity_type,
                        entity.amount,
                        entity.currency,
                    ]
                )
        return output.getvalue()

    def format_performance(self, report: PerformanceReport) -> str:
        """Format performance as summary plus breakdown CSV tables."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "since",
                "currency",
                "net_liquidation",
                "net_deposits",
                "return_amount",
                "return_rate",
                "realized_total",
                "account_label",
            ]
        )
        writer.writerow(
            [
                report.since,
                report.currency,
                report.net_liquidation,
                report.net_deposits,
                report.return_amount,
                report.return_rate if report.return_rate is not None else "",
                report.realized_total,
                report.account_label or "",
            ]
        )
        if report.realized:
            writer.writerow([])
            writer.writerow(["symbol", "name", "amount", "currency"])
            for row in report.realized:
                writer.writerow([row.symbol, row.name, row.amount, row.currency])
        if report.unrealized:
            writer.writerow([])
            writer.writerow(["account_label", "amount", "rate", "currency"])
            for row in report.unrealized:
                writer.writerow(
                    [
                        row.account_label,
                        row.amount,
                        row.rate if row.rate is not None else "",
                        row.currency,
                    ]
                )
        if report.history:
            writer.writerow([])
            writer.writerow(["date", "net_liquidation", "net_deposits", "currency"])
            for point in report.history:
                writer.writerow(
                    [
                        point.date,
                        point.net_liquidation,
                        point.net_deposits,
                        point.currency,
                    ]
                )
        return output.getvalue()


def get_formatter(format_type: str) -> FormatterProtocol:
    """Get formatter instance by type.

    Args:
        format_type: One of 'table', 'json', or 'csv'

    Returns:
        Formatter instance. Defaults to TableFormatter for unknown types.
    """
    formatters = {
        "table": TableFormatter(),
        "json": JsonFormatter(),
        "csv": CsvFormatter(),
    }
    return formatters.get(format_type.lower(), TableFormatter())
