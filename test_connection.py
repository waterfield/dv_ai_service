from database import test_connection, get_schema

if __name__ == "__main__":
    print("Testing SQL Server connection...")
    ok = test_connection()
    if not ok:
        print("Connection FAILED. Check .env credentials.")
        exit(1)

    print("\nLoading schema...")
    schema = get_schema()
    print(f"\nFound {len(schema)} tables:")
    for table, cols in list(schema.items())[:10]:
        col_names = ", ".join(c["name"] for c in cols[:5])
        more = f" (+{len(cols)-5} more)" if len(cols) > 5 else ""
        print(f"  {table}: {col_names}{more}")
    if len(schema) > 10:
        print(f"  ... and {len(schema) - 10} more tables")
