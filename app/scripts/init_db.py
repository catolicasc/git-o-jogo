from app.shared.db import models  # noqa: F401
from app.shared.db.base import Base
from app.shared.db.session import engine


def main() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
