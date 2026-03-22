import json

from app.config.settings import get_settings
from app.modules.backtest.backtest_service import BacktestService


def main() -> None:
    settings = get_settings()
    service = BacktestService()
    report = service.run(symbols=settings.symbols)
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
