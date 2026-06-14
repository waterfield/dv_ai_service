"""
Run every SQL template against the live database and report PASS/FAIL.
Uses NULL params (all filters disabled) with top_n=5 to keep result sets small.

Usage:
    python test_templates.py           # run all templates
    python test_templates.py financial # run only afe_financial templates
    python test_templates.py master    # run only afe_master templates
"""

import logging
import os
import sys
import time

# Must be set before database.py is imported (it reads DEBUG at module level)
os.environ.setdefault("DEBUG", "false")
logging.disable(logging.INFO)

from sqlalchemy import text
from database import engine

logging.disable(logging.NOTSET)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
from app.services.tools.afe_financial import AFE_FINANCIAL_TEMPLATES
from app.services.tools.afe_master import AFE_MASTER_TEMPLATES

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD  = "\033[1m"

FINANCIAL_PARAMS = {
    "year":                 None,
    "month":                None,
    "status":               None,
    "afe_type_description": None,
    "top_n":                5,
}

MASTER_PARAMS = {
    "year":                   None,
    "approved_date_from":     None,
    "approved_date_to":       None,
    "completion_date_from":   None,
    "completion_date_to":     None,
    "closed_date_from":       None,
    "closed_date_to":         None,
    "status":                 None,
    "afe_type_description":   None,
    "afe_number":             None,
    "afe_project_name":       None,
    "company_name":           None,
    "division_order_number":  None,
    "top_n":                  5,
}


def run_suite(label: str, templates: dict[str, str], params: dict) -> tuple[int, int]:
    """Run all templates in a suite. Returns (passed, failed)."""
    passed = failed = 0
    width = max(len(k) for k in templates) + 2

    print(f"\n{BOLD}{'-' * 60}{RESET}")
    print(f"{BOLD}  {label}{RESET}")
    print(f"{BOLD}{'-' * 60}{RESET}")

    with engine.connect() as conn:
        for key, sql in templates.items():
            t0 = time.perf_counter()
            try:
                result = conn.execute(text(sql), params)
                rows = result.fetchall()
                elapsed = time.perf_counter() - t0
                print(
                    f"  {GREEN}PASS{RESET}  {key:<{width}}"
                    f"  {len(rows)} row(s)  {elapsed:.2f}s"
                )
                passed += 1
            except Exception as exc:
                elapsed = time.perf_counter() - t0
                print(
                    f"  {RED}FAIL{RESET}  {key:<{width}}"
                    f"  {elapsed:.2f}s"
                )
                print(f"         {RED}{exc}{RESET}")
                failed += 1

    return passed, failed


def main() -> None:
    filter_arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    total_passed = total_failed = 0

    if filter_arg in ("all", "financial"):
        p, f = run_suite("afe_financial  (25 templates)", AFE_FINANCIAL_TEMPLATES, FINANCIAL_PARAMS)
        total_passed += p
        total_failed += f

    if filter_arg in ("all", "master"):
        p, f = run_suite("afe_master     (12 templates)", AFE_MASTER_TEMPLATES, MASTER_PARAMS)
        total_passed += p
        total_failed += f

    total = total_passed + total_failed
    print(f"\n{BOLD}{'-' * 60}{RESET}")
    print(
        f"{BOLD}  Results: "
        f"{GREEN}{total_passed} passed{RESET}{BOLD}, "
        f"{RED if total_failed else ''}{total_failed} failed{RESET}{BOLD} / {total} total{RESET}"
    )
    print(f"{BOLD}{'-' * 60}{RESET}\n")

    if total_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
