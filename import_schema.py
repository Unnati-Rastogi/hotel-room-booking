"""
import_schema.py
Imports schema.sql into MySQL using mysql-connector-python.
Handles DELIMITER changes and multi-statement blocks natively.
Run once: python import_schema.py
"""

import mysql.connector
import re

HOST     = "localhost"
USER     = "root"
PASSWORD = "@R00t123"

SQL_FILE = "schema.sql"


def split_statements(sql: str):
    """
    Split SQL text into individual statements, respecting DELIMITER changes
    and stripping comments.
    """
    statements = []
    delimiter  = ";"
    buffer     = ""

    for raw_line in sql.splitlines():
        line = raw_line.strip()

        # Skip pure comment lines and blank lines
        if not line or line.startswith("--"):
            continue

        # Handle DELIMITER change
        m = re.match(r"^DELIMITER\s+(\S+)\s*$", line, re.IGNORECASE)
        if m:
            delimiter = m.group(1)
            continue

        buffer += raw_line + "\n"

        if buffer.rstrip().endswith(delimiter):
            stmt = buffer.rstrip()
            if delimiter != ";":
                stmt = stmt[: -len(delimiter)].rstrip()
            stmt = stmt.strip()
            if stmt:
                statements.append(stmt)
            buffer = ""

    # Flush any remaining content
    if buffer.strip():
        statements.append(buffer.strip())

    return statements


def run():
    print("Connecting to MySQL…")
    # First connect without a database to create it
    conn = mysql.connector.connect(
        host=HOST, user=USER, password=PASSWORD, autocommit=True
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS hotel_booking")
    cursor.execute("USE hotel_booking")
    print("Database 'hotel_booking' ready.")

    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()

    # Remove CREATE DATABASE / USE lines — we've already handled them
    sql = re.sub(r"(?im)^CREATE DATABASE.*?;\s*$", "", sql)
    sql = re.sub(r"(?im)^USE\s+\w+\s*;\s*$", "", sql)

    statements = split_statements(sql)
    print(f"Executing {len(statements)} statements…\n")

    errors = 0
    for i, stmt in enumerate(statements, 1):
        preview = stmt[:60].replace("\n", " ")
        try:
            cursor.execute(stmt)
            # Consume any result sets (e.g. from CALL)
            while cursor.nextset():
                pass
            print(f"  [{i:02d}] OK — {preview}…")
        except mysql.connector.Error as e:
            print(f"  [{i:02d}] ERROR — {e}\n       Statement: {preview}…")
            errors += 1

    cursor.close()
    conn.close()

    print()
    if errors == 0:
        print("✅ Schema imported successfully! All statements executed without errors.")
    else:
        print(f"⚠️  Done with {errors} error(s). Check the output above.")


if __name__ == "__main__":
    run()
