from datetime import date
from unittest.mock import MagicMock

import pytest

from wealthgrabber.performance import get_performance_data, print_performance


@pytest.fixture
def mock_ws_client():
    return MagicMock()


def test_get_performance_data_maps_current_and_realized(mock_ws_client):
    mock_ws_client.get_identity_current_financials.return_value = {
        "netLiquidationValueV2": {"amount": "100000", "currency": "CAD"},
        "netDeposits": {"amount": "80000", "currency": "CAD"},
        "simpleReturns": {
            "amount": {"amount": "5000", "currency": "CAD"},
            "rate": 0.0625,
            "asOf": "2026-09-24",
        },
    }
    mock_ws_client.get_identity_realized_returns.return_value = {
        "totalValue": {"amount": "1200", "currency": "CAD"},
        "securityBreakdown": {
            "edges": [
                {
                    "node": {
                        "security": {
                            "id": "sec-s-xeqt",
                            "stock": {"symbol": "XEQT", "name": "iShares Core"},
                        },
                        "totalValue": {"amount": "1200", "currency": "CAD"},
                    }
                }
            ]
        },
    }
    mock_ws_client.get_identity_historical_financials.return_value = [
        {
            "date": "2026-01-01",
            "netLiquidationValueV2": {"amount": "90000", "currency": "CAD"},
            "netDepositsV2": {"amount": "80000", "currency": "CAD"},
        }
    ]
    mock_ws_client.get_accounts.return_value = [
        {"id": "acc-1", "description": "My TFSA", "number": "TFSA-001"}
    ]
    mock_ws_client.get_account_unrealized_pnl.return_value = {
        "amount": {"amount": "3000", "currency": "CAD"},
        "rate": 0.04,
    }

    report = get_performance_data(mock_ws_client, since="2026-01-01")

    assert report.net_liquidation == 100000.0
    assert report.net_deposits == 80000.0
    assert report.return_amount == 5000.0
    assert report.return_rate == pytest.approx(6.25)
    assert report.realized_total == 1200.0
    assert report.realized[0].symbol == "XEQT"
    assert report.unrealized[0].amount == 3000.0
    assert report.unrealized[0].rate == pytest.approx(4.0)
    assert report.history[0].net_liquidation == 90000.0
    mock_ws_client.get_identity_current_financials.assert_called_with(
        "CAD", None, "2026-01-01"
    )


def test_get_performance_data_defaults_since_to_year_start(mock_ws_client):
    mock_ws_client.get_identity_current_financials.return_value = {}
    mock_ws_client.get_identity_realized_returns.return_value = {}
    mock_ws_client.get_identity_historical_financials.return_value = []
    mock_ws_client.get_accounts.return_value = []

    report = get_performance_data(mock_ws_client)
    expected = f"{date.today().year}-01-01"
    assert report.since == expected
    assert mock_ws_client.get_identity_current_financials.call_args.args[2] == expected


def test_get_performance_data_filters_unrealized_by_account(mock_ws_client):
    mock_ws_client.get_identity_current_financials.return_value = {}
    mock_ws_client.get_identity_realized_returns.return_value = {}
    mock_ws_client.get_identity_historical_financials.return_value = []
    mock_ws_client.get_accounts.return_value = [
        {"id": "acc-keep", "description": "TFSA", "number": "TFSA-001"},
        {"id": "acc-drop", "description": "RRSP", "number": "RRSP-001"},
    ]
    mock_ws_client.get_account_unrealized_pnl.return_value = {
        "amount": {"amount": "1", "currency": "CAD"},
        "rate": 0.01,
    }

    report = get_performance_data(mock_ws_client, account_id="acc-keep")

    mock_ws_client.get_account_unrealized_pnl.assert_called_once_with("acc-keep", "CAD")
    assert len(report.unrealized) == 1
    assert "TFSA-001" in report.unrealized[0].account_label


def test_print_performance_table(mock_ws_client, capsys):
    mock_ws_client.get_identity_current_financials.return_value = {
        "netLiquidationValueV2": {"amount": "1000", "currency": "CAD"},
        "netDeposits": {"amount": "800", "currency": "CAD"},
        "simpleReturns": {"amount": {"amount": "50", "currency": "CAD"}, "rate": 0.05},
    }
    mock_ws_client.get_identity_realized_returns.return_value = {
        "totalValue": {"amount": "10", "currency": "CAD"},
        "securityBreakdown": {"edges": []},
    }
    mock_ws_client.get_identity_historical_financials.return_value = []
    mock_ws_client.get_accounts.return_value = []

    print_performance(mock_ws_client, since="2026-01-01")

    captured = capsys.readouterr()
    assert "Performance since 2026-01-01" in captured.out
    assert "Net liquidation" in captured.out
    assert "1,000.00" in captured.out
    assert "Simple return" in captured.out
