from datetime import date
from unittest.mock import MagicMock

import pytest

from wealthgrabber.dividends import get_dividends_data, print_dividends

AS_OF = date(2026, 9, 24)


@pytest.fixture
def mock_ws_client():
    return MagicMock()


def _income_payload(
    rows: list[tuple[str, str, str, float]], total: float, currency="CAD"
):
    return {
        "totalValue": {"amount": str(total), "currency": currency},
        "issuingSecurityBreakdown": [
            {
                "security": {"id": sec_id, "stock": {"symbol": symbol, "name": name}},
                "totalValue": {"amount": str(amount), "currency": currency},
            }
            for sec_id, symbol, name, amount in rows
        ],
    }


def test_get_dividends_data_maps_income_and_sorts_by_amount(mock_ws_client):
    mock_ws_client.get_dividends.return_value = _income_payload(
        [
            ("sec-s-aaa", "VCN", "Vanguard Canada", 10.0),
            ("sec-s-bbb", "XEQT", "iShares Core Equity", 50.5),
        ],
        total=60.5,
    )
    mock_ws_client.get_identity_positions.return_value = []

    result = get_dividends_data(
        mock_ws_client, since="2026-01-01", include_upcoming=False
    )

    assert result.since == "2026-01-01"
    assert result.currency == "CAD"
    assert result.total_amount == 60.5
    assert [row.symbol for row in result.income] == ["XEQT", "VCN"]
    assert result.income[0].name == "iShares Core Equity"
    assert result.income[0].amount == 50.5
    mock_ws_client.get_dividends.assert_called_once_with(
        "CAD",
        None,
        "2026-01-01",
        include_issuing_security_breakdown=True,
    )
    mock_ws_client.get_security_dividend_details.assert_not_called()


def test_get_dividends_data_defaults_since_to_year_start(mock_ws_client):
    mock_ws_client.get_dividends.return_value = _income_payload([], 0)
    expected = f"{date.today().year}-01-01"

    result = get_dividends_data(mock_ws_client, include_upcoming=False)

    assert result.since == expected
    assert mock_ws_client.get_dividends.call_args.args[2] == expected


def test_get_dividends_data_falls_back_to_security_id(mock_ws_client):
    mock_ws_client.get_dividends.return_value = {
        "totalValue": {"amount": "5", "currency": "CAD"},
        "issuingSecurityBreakdown": [
            {
                "security": {"id": "sec-s-orphan", "stock": {}},
                "totalValue": {"amount": "5", "currency": "CAD"},
            }
        ],
    }

    result = get_dividends_data(
        mock_ws_client, since="2026-01-01", include_upcoming=False
    )

    assert result.income[0].symbol == "sec-s-orphan"
    assert result.income[0].name == "sec-s-orphan"


def test_get_dividends_data_empty_response(mock_ws_client):
    mock_ws_client.get_dividends.return_value = None

    result = get_dividends_data(
        mock_ws_client, since="2026-01-01", include_upcoming=False
    )

    assert result.income == []
    assert result.upcoming == []
    assert result.total_amount == 0.0


def test_get_dividends_data_passes_account_ids(mock_ws_client):
    mock_ws_client.get_dividends.return_value = _income_payload([], 0)
    mock_ws_client.get_identity_positions.return_value = []

    get_dividends_data(
        mock_ws_client,
        account_id="acc-123",
        since="2026-01-01",
        include_upcoming=False,
        account_label="TFSA-001",
    )

    assert mock_ws_client.get_dividends.call_args.args[1] == ["acc-123"]


def test_upcoming_skips_cash_past_events_and_empty_events(mock_ws_client):
    mock_ws_client.get_dividends.return_value = _income_payload([], 0)
    mock_ws_client.get_identity_positions.return_value = [
        {"security": {"id": "sec-c-cad"}, "accounts": [{"id": "acc-1"}]},
        {"security": {"id": "sec-s-xeqt"}, "accounts": [{"id": "acc-1"}]},
        {"security": {"id": "sec-s-past"}, "accounts": [{"id": "acc-1"}]},
        {"security": {"id": "sec-s-empty"}, "accounts": [{"id": "acc-1"}]},
        {"security": {"id": "sec-s-zero"}, "accounts": [{"id": "acc-1"}]},
        {"security": {"id": "sec-s-xeqt"}, "accounts": [{"id": "acc-2"}]},
    ]

    def details(security_id, currency=None):
        payloads = {
            "sec-s-xeqt": {
                "stock": {
                    "symbol": "XEQT",
                    "name": "iShares Core",
                    "dividendFrequency": "QUARTERLY",
                },
                "fundamentals": {"yield": 0.018},
                "events": [
                    {
                        "exDividendDate": "2026-09-28",
                        "recordDate": "2026-09-29",
                        "payableDate": "2026-10-07",
                    }
                ],
            },
            "sec-s-past": {
                "stock": {
                    "symbol": "OLD",
                    "name": "Past Payer",
                    "dividendFrequency": "ANNUAL",
                },
                "fundamentals": {"yield": 2.5},
                "events": [
                    {
                        "exDividendDate": "2026-01-01",
                        "recordDate": "2026-01-02",
                        "payableDate": "2026-01-15",
                    }
                ],
            },
            "sec-s-empty": {
                "stock": {"symbol": "NONE", "name": "No Event"},
                "fundamentals": {"yield": 0.01},
                "events": [],
            },
            "sec-s-zero": {
                "stock": {"symbol": "ZERO", "name": "Zero Yield"},
                "fundamentals": {"yield": 0},
                "events": [],
            },
        }
        return payloads[security_id]

    mock_ws_client.get_security_dividend_details.side_effect = details

    result = get_dividends_data(mock_ws_client, since="2026-01-01", as_of=AS_OF)

    rows_by_symbol = {row.symbol: row for row in result.upcoming}
    assert set(rows_by_symbol) == {"XEQT", "NONE"}
    assert rows_by_symbol["XEQT"].yield_pct == pytest.approx(1.8)
    assert rows_by_symbol["XEQT"].frequency == "QUARTERLY"
    assert rows_by_symbol["XEQT"].ex_date == "2026-09-28"
    assert rows_by_symbol["XEQT"].payable_date == "2026-10-07"
    assert rows_by_symbol["NONE"].yield_pct == pytest.approx(1.0)
    assert rows_by_symbol["NONE"].ex_date is None
    assert rows_by_symbol["NONE"].payable_date is None
    looked_up = [
        call.args[0]
        for call in mock_ws_client.get_security_dividend_details.call_args_list
    ]
    assert looked_up == [
        "sec-s-xeqt",
        "sec-s-past",
        "sec-s-empty",
        "sec-s-zero",
    ]


def test_upcoming_skips_lookup_errors(mock_ws_client):
    mock_ws_client.get_dividends.return_value = _income_payload([], 0)
    mock_ws_client.get_identity_positions.return_value = [
        {"security": {"id": "sec-s-bad"}},
        {"security": {"id": "sec-s-good"}},
    ]

    def details(security_id, currency=None):
        if security_id == "sec-s-bad":
            raise RuntimeError("lookup failed")
        return {
            "stock": {
                "symbol": "GOOD",
                "name": "Good Co",
                "dividendFrequency": "MONTHLY",
            },
            "fundamentals": {"yield": 3.2},
            "events": [
                {
                    "exDividendDate": "2026-10-01",
                    "recordDate": "2026-10-02",
                    "payableDate": "2026-10-15",
                }
            ],
        }

    mock_ws_client.get_security_dividend_details.side_effect = details

    result = get_dividends_data(mock_ws_client, since="2026-01-01", as_of=AS_OF)

    assert [row.symbol for row in result.upcoming] == ["GOOD"]
    assert result.upcoming[0].yield_pct == pytest.approx(3.2)


def test_upcoming_uses_market_data_when_dividend_details_omit_security_labels(
    mock_ws_client,
):
    mock_ws_client.get_dividends.return_value = _income_payload([], 0)
    mock_ws_client.get_identity_positions.return_value = [
        {"security": {"id": "sec-s-xeqt"}},
    ]
    mock_ws_client.get_security_dividend_details.return_value = {
        "stock": {"dividendFrequency": "QUARTERLY"},
        "fundamentals": {"yield": 0.018},
        "events": [
            {
                "exDividendDate": "2026-09-28",
                "recordDate": "2026-09-29",
                "payableDate": "2026-10-07",
            }
        ],
    }
    mock_ws_client.get_security_market_data.return_value = {
        "stock": {"symbol": "XEQT", "name": "iShares Core Equity ETF"},
    }

    result = get_dividends_data(
        mock_ws_client, since="2026-01-01", as_of=AS_OF
    )

    assert len(result.upcoming) == 1
    assert result.upcoming[0].symbol == "XEQT"
    assert result.upcoming[0].name == "iShares Core Equity ETF"
    assert result.upcoming[0].frequency == "QUARTERLY"
    mock_ws_client.get_security_market_data.assert_called_once_with(
        "sec-s-xeqt", use_cache=False
    )


def test_upcoming_filters_positions_by_account(mock_ws_client):
    mock_ws_client.get_dividends.return_value = _income_payload([], 0)
    mock_ws_client.get_identity_positions.return_value = [
        {"security": {"id": "sec-s-keep"}, "accounts": [{"id": "acc-keep"}]},
        {"security": {"id": "sec-s-drop"}, "accounts": [{"id": "acc-other"}]},
    ]
    mock_ws_client.get_security_dividend_details.return_value = {
        "stock": {
            "symbol": "KEEP",
            "name": "Keep Co",
            "dividendFrequency": "QUARTERLY",
        },
        "fundamentals": {"yield": 1.0},
        "events": [
            {
                "exDividendDate": "2026-10-01",
                "recordDate": None,
                "payableDate": "2026-10-15",
            }
        ],
    }

    result = get_dividends_data(
        mock_ws_client, account_id="acc-keep", since="2026-01-01", as_of=AS_OF
    )

    mock_ws_client.get_security_dividend_details.assert_called_once()
    assert (
        mock_ws_client.get_security_dividend_details.call_args.args[0] == "sec-s-keep"
    )
    assert result.upcoming[0].symbol == "KEEP"


def test_print_dividends_no_data(mock_ws_client, capsys):
    mock_ws_client.get_dividends.return_value = None

    print_dividends(mock_ws_client, since="2026-01-01", include_upcoming=False)

    captured = capsys.readouterr()
    assert "No dividend data found." in captured.out


def test_print_dividends_table_has_income_and_upcoming(mock_ws_client, capsys):
    mock_ws_client.get_dividends.return_value = _income_payload(
        [("sec-s-xeqt", "XEQT", "iShares Core Equity ETF", 123.45)],
        total=123.45,
    )
    mock_ws_client.get_identity_positions.return_value = [
        {"security": {"id": "sec-s-xeqt"}}
    ]
    mock_ws_client.get_security_dividend_details.return_value = {
        "stock": {
            "symbol": "XEQT",
            "name": "iShares Core Equity ETF",
            "dividendFrequency": "QUARTERLY",
        },
        "fundamentals": {"yield": 0.018},
        "events": [
            {
                "exDividendDate": "2026-09-28",
                "recordDate": "2026-09-29",
                "payableDate": "2026-10-07",
            }
        ],
    }

    print_dividends(mock_ws_client, since="2026-01-01", as_of=AS_OF)

    captured = capsys.readouterr()
    assert "Dividends received since 2026-01-01" in captured.out
    assert "XEQT" in captured.out
    assert "123.45" in captured.out
    assert "TOTAL" in captured.out
    assert "Upcoming dividends" in captured.out
    assert "2026-09-28" in captured.out
    assert "2026-10-07" in captured.out


def test_print_dividends_json(mock_ws_client, capsys):
    mock_ws_client.get_dividends.return_value = _income_payload(
        [("sec-s-xeqt", "XEQT", "iShares Core", 10.0)],
        total=10.0,
    )

    print_dividends(
        mock_ws_client,
        since="2026-01-01",
        include_upcoming=False,
        output_format="json",
    )

    captured = capsys.readouterr()
    assert '"since": "2026-01-01"' in captured.out
    assert '"total_amount": 10.0' in captured.out
    assert '"income"' in captured.out
    assert '"upcoming"' in captured.out
    assert '"XEQT"' in captured.out


def test_print_dividends_csv_two_tables(mock_ws_client, capsys):
    mock_ws_client.get_dividends.return_value = _income_payload(
        [("sec-s-xeqt", "XEQT", "iShares Core", 10.0)],
        total=10.0,
    )
    mock_ws_client.get_identity_positions.return_value = [
        {"security": {"id": "sec-s-xeqt"}}
    ]
    mock_ws_client.get_security_dividend_details.return_value = {
        "stock": {
            "symbol": "XEQT",
            "name": "iShares Core",
            "dividendFrequency": "QUARTERLY",
        },
        "fundamentals": {"yield": 0.018},
        "events": [
            {
                "exDividendDate": "2026-09-28",
                "recordDate": "2026-09-29",
                "payableDate": "2026-10-07",
            }
        ],
    }

    print_dividends(
        mock_ws_client, since="2026-01-01", output_format="csv", as_of=AS_OF
    )

    captured = capsys.readouterr()
    assert "symbol,name,amount,currency" in captured.out
    assert (
        "symbol,name,yield_pct,frequency,ex_date,record_date,payable_date"
        in captured.out
    )


def test_print_dividends_verbose(mock_ws_client, capsys):
    mock_ws_client.get_dividends.return_value = _income_payload([], 0)
    mock_ws_client.get_identity_positions.return_value = [
        {"security": {"id": "sec-s-xeqt"}}
    ]
    mock_ws_client.get_security_dividend_details.return_value = {
        "stock": {"symbol": "XEQT", "name": "Core", "dividendFrequency": "QUARTERLY"},
        "fundamentals": {"yield": 0.01},
        "events": [
            {
                "exDividendDate": "2026-10-01",
                "recordDate": "2026-10-02",
                "payableDate": "2026-10-15",
            }
        ],
    }

    print_dividends(mock_ws_client, since="2026-01-01", verbose=True, as_of=AS_OF)

    captured = capsys.readouterr()
    assert "Fetching dividend income" in captured.out
    assert "Checking announced dates" in captured.out
