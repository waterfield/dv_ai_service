import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture(autouse=True)
def patch_get_db(mock_db):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_db)
    cm.__exit__ = MagicMock(return_value=False)
    with patch("app.mcp.tools._get_db_session", return_value=cm):
        yield mock_db


@pytest.fixture(autouse=True)
def patch_executor():
    with patch("app.mcp.tools._executor") as mock:
        mock.execute.return_value = (
            pd.DataFrame({"AFE Number": ["AFE-2024-001"], "Budget Amount": [100000]}),
            None,
        )
        yield mock


def test_query_afe_financial_returns_markdown():
    from app.mcp.tools import query_afe_financial
    result = query_afe_financial(template="budget_by_afe")
    assert "AFE Number" in result
    assert "Budget Amount" in result


def test_query_afe_financial_passes_filters(patch_executor):
    from app.mcp.tools import query_afe_financial
    patch_executor.execute.return_value = (pd.DataFrame({"col": [1]}), None)
    query_afe_financial(template="budget_by_afe", year=2024, afe_number="AFE-2024-001")
    call_args = patch_executor.execute.call_args
    params = call_args[0][2]
    assert params["year"] == 2024
    assert params["afe_number"] == "AFE-2024-001"


def test_query_afe_financial_invalid_template_returns_error():
    from app.mcp.tools import query_afe_financial
    result = query_afe_financial(template="nonexistent_template")
    assert "Error" in result


def test_query_afe_financial_empty_result(patch_executor):
    from app.mcp.tools import query_afe_financial
    patch_executor.execute.return_value = (pd.DataFrame(), None)
    result = query_afe_financial(template="budget_by_afe")
    assert "No results" in result


def test_query_afe_financial_db_error(patch_executor):
    from app.mcp.tools import query_afe_financial
    patch_executor.execute.return_value = (None, "Connection failed")
    result = query_afe_financial(template="budget_by_afe")
    assert "Connection failed" in result


def test_query_afe_master_returns_markdown():
    from app.mcp.tools import query_afe_master
    result = query_afe_master(template="list_afes")
    assert "|" in result


def test_query_afe_master_invalid_template_returns_error():
    from app.mcp.tools import query_afe_master
    result = query_afe_master(template="bad_template")
    assert "Error" in result


def test_get_templates_returns_all():
    from app.mcp.tools import get_templates
    result = get_templates()
    assert "budget_by_afe" in result
    assert "list_afes" in result


def test_get_templates_filters_financial():
    from app.mcp.tools import get_templates
    result = get_templates(tool_name="afe_financial")
    assert "budget_by_afe" in result
    assert "list_afes" not in result


def test_get_templates_filters_master():
    from app.mcp.tools import get_templates
    result = get_templates(tool_name="afe_master")
    assert "list_afes" in result
    assert "budget_by_afe" not in result
