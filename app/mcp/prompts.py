from app.mcp import mcp


@mcp.prompt(
    description="Generate a complete summary of a specific AFE, covering master data and financial position."
)
def summarize_afe(afe_number: str) -> list[dict]:
    """
    afe_number: the AFE identifier to summarize e.g. 'AFE-2025-001'.
    """
    content = (
        f"Provide a complete summary of AFE {afe_number}.\n\n"
        "You MUST follow these steps in order:\n"
        f'1. Call query_afe_master with afe_number="{afe_number}" to get '
        "attributes, status, project name, company, and timeline\n"
        f'2. Call query_afe_financial with afe_number="{afe_number}" to get '
        "budget, actuals, commitments, and spend position\n"
        "3. Combine both results into a structured summary covering:\n"
        "   - AFE identity and status\n"
        "   - Financial position (budget vs actuals vs commitments)\n"
        "   - Key observations or anomalies\n\n"
        "Do not skip step 1 or step 2."
    )
    return [{"role": "user", "content": content}]
