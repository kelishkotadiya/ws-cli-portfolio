from unittest.mock import MagicMock

import pytest

from wealthgrabber.networth import get_networth_data, print_networth


@pytest.fixture
def mock_ws_client():
    return MagicMock()


def test_get_networth_data_maps_balance_and_history(mock_ws_client):
    mock_ws_client.get_net_worth_accounts.return_value = {
        "accounts": [{"id": "acc-1", "description": "TFSA", "number": "TFSA-001"}],
        "externalFinancialEntities": [],
    }
    mock_ws_client.get_net_worth_with_history.return_value = {
        "balance": {"amount": "100000", "currency": "CAD"},
        "historicalDaily": [
            {"date": "2026-08-25", "balance": {"amount": "95000", "currency": "CAD"}},
            {"date": "2026-09-24", "balance": {"amount": "100000", "currency": "CAD"}},
        ],
    }

    report = get_networth_data(mock_ws_client, days=30)

    assert report.scope == "HOUSEHOLD"
    assert report.current_amount == 100000.0
    assert report.start_amount == 95000.0
    assert report.start_date == "2026-08-25"
    assert report.change == 5000.0
    assert report.change_pct == pytest.approx(5.263, rel=1e-3)
    assert [point.date for point in report.history] == ["2026-08-25", "2026-09-24"]
    assert report.accounts == []
    kwargs = mock_ws_client.get_net_worth_with_history.call_args.kwargs
    assert kwargs["account_scope"] == "HOUSEHOLD"
    assert kwargs["account_ids"] == ["acc-1"]


def test_get_networth_data_include_accounts(mock_ws_client):
    mock_ws_client.get_net_worth_accounts.return_value = {
        "accounts": [
            {
                "id": "acc-1",
                "description": "My TFSA",
                "number": "TFSA-001",
                "financials": {
                    "currentCombined": {
                        "netLiquidationValueV2": {
                            "amount": "5000",
                            "currency": "CAD",
                        }
                    }
                },
            }
        ],
        "externalFinancialEntities": [
            {
                "id": "ext-1",
                "displayName": "Home",
                "institutionName": "Bank",
                "entityType": "MORTGAGE",
                "balance": {"amount": "-200000", "currency": "CAD"},
            }
        ],
    }
    mock_ws_client.get_net_worth_with_history.return_value = {
        "balance": {"amount": "100000", "currency": "CAD"},
        "historicalDaily": [],
    }

    report = get_networth_data(mock_ws_client, include_accounts=True)

    assert report.accounts[0].description == "My TFSA"
    assert report.accounts[0].value == 5000.0
    assert report.external[0].name == "Home"
    assert report.external[0].amount == -200000.0


def test_print_networth_table(mock_ws_client, capsys):
    mock_ws_client.get_net_worth_accounts.return_value = {
        "accounts": [],
        "externalFinancialEntities": [],
    }
    mock_ws_client.get_net_worth_with_history.return_value = {
        "balance": {"amount": "100000", "currency": "CAD"},
        "historicalDaily": [
            {"date": "2026-08-25", "balance": {"amount": "95000", "currency": "CAD"}},
        ],
    }

    print_networth(mock_ws_client)

    captured = capsys.readouterr()
    assert "Net worth (HOUSEHOLD)" in captured.out
    assert "100,000.00" in captured.out
    assert "95,000.00" in captured.out
    assert "Change" in captured.out


def test_print_networth_json(mock_ws_client, capsys):
    mock_ws_client.get_net_worth_accounts.return_value = {
        "accounts": [],
        "externalFinancialEntities": [],
    }
    mock_ws_client.get_net_worth_with_history.return_value = {
        "balance": {"amount": "10", "currency": "CAD"},
        "historicalDaily": [],
    }

    print_networth(mock_ws_client, output_format="json")

    captured = capsys.readouterr()
    assert '"current_amount": 10.0' in captured.out
    assert '"history"' in captured.out
