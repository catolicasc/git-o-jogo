from app.integrations.binance.binance_client import BinanceClient


class AccountService:
    def __init__(self, binance_client: BinanceClient) -> None:
        self.binance_client = binance_client

    def get_account_overview(self) -> dict:
        account_info = self.binance_client.get_account_info(omit_zero_balances=True)
        balances = [
            {
                "asset": balance["asset"],
                "free": float(balance["free"]),
                "locked": float(balance["locked"]),
                "total": float(balance["free"]) + float(balance["locked"]),
            }
            for balance in account_info.get("balances", [])
        ]
        balances = [balance for balance in balances if balance["total"] > 0]
        balances.sort(key=lambda item: item["total"], reverse=True)

        return {
            "account_type": account_info.get("accountType", "SPOT"),
            "can_trade": account_info.get("canTrade", False),
            "can_deposit": account_info.get("canDeposit", False),
            "can_withdraw": account_info.get("canWithdraw", False),
            "permissions": account_info.get("permissions", []),
            "balances": balances,
            "balances_count": len(balances),
            "updated_at": account_info.get("updateTime"),
        }

    def get_balance_map(self) -> dict[str, dict[str, float]]:
        overview = self.get_account_overview()
        return {
            balance["asset"]: {
                "free": balance["free"],
                "locked": balance["locked"],
                "total": balance["total"],
            }
            for balance in overview["balances"]
        }
