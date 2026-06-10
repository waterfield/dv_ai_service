def test_summarize_afe_returns_message_list():
    from app.mcp.prompts import summarize_afe
    result = summarize_afe(afe_number="AFE-2024-001")
    assert isinstance(result, list)
    assert len(result) > 0


def test_summarize_afe_contains_afe_number():
    from app.mcp.prompts import summarize_afe
    result = summarize_afe(afe_number="AFE-2024-001")
    full_text = " ".join(str(msg["content"]) for msg in result)
    assert "AFE-2024-001" in full_text


def test_summarize_afe_mentions_both_tools():
    from app.mcp.prompts import summarize_afe
    result = summarize_afe(afe_number="AFE-2024-001")
    full_text = " ".join(str(msg["content"]) for msg in result)
    assert "query_afe_master" in full_text
    assert "query_afe_financial" in full_text


def test_summarize_afe_role_is_user():
    from app.mcp.prompts import summarize_afe
    result = summarize_afe(afe_number="AFE-2024-001")
    assert result[0]["role"] == "user"
