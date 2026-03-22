from sqlalchemy import text

from app.shared.db import models  # noqa: F401
from app.shared.db.base import Base
from app.shared.db.session import SessionLocal


def main() -> None:
    table_names = [table.name for table in reversed(Base.metadata.sorted_tables)]

    if not table_names:
        print("No tables found to reset.")
        return

    truncate_sql = "TRUNCATE TABLE " + ", ".join(table_names) + " RESTART IDENTITY CASCADE"

    with SessionLocal() as db:
        db.execute(text(truncate_sql))
        db.commit()

    print("Database reset completed.")
    print("Truncated tables:")
    for table_name in table_names:
        print(f"- {table_name}")


if __name__ == "__main__":
    main()
