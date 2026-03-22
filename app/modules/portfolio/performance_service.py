from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.modules.portfolio.account_service import AccountService
from app.shared.db.models import MarketSnapshot, Position, Trade


class PerformanceService:
    def __init__(self, db: Session, account_service: AccountService | None = None) -> None:
        self.db = db
        self.settings = get_settings()
        self.account_service = account_service

    def get_summary(self) -> dict:
        if self.settings.app_mode == "live" and self.account_service is not None:
            try:
                return self._get_live_summary()
            except Exception:
                pass

        trades = self._filled_trades()
        positions = self._positions_with_mark_prices()
        starting_bankroll = self.settings.default_bankroll_usd

        cash_balance = starting_bankroll
        gross_volume = 0.0
        buy_count = 0
        sell_count = 0

        for trade in trades:
            notional = trade.price * trade.quantity
            gross_volume += notional
            if trade.side == "BUY":
                buy_count += 1
                cash_balance -= notional
            else:
                sell_count += 1
                cash_balance += notional

        realized_pnl = sum(position["realized_pnl"] for position in positions)
        unrealized_pnl = sum(position["unrealized_pnl_live"] for position in positions)
        inventory_value = sum(position["market_value"] for position in positions)
        equity = cash_balance + inventory_value
        pnl_abs = equity - starting_bankroll
        pnl_pct = (pnl_abs / starting_bankroll) * 100 if starting_bankroll else 0

        return {
            "mode": self.settings.app_mode,
            "starting_bankroll": round(starting_bankroll, 2),
            "cash_balance": round(cash_balance, 2),
            "inventory_value": round(inventory_value, 2),
            "equity": round(equity, 2),
            "pnl_abs": round(pnl_abs, 2),
            "pnl_pct": round(pnl_pct, 2),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_trades": len(trades),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "gross_volume": round(gross_volume, 2),
            "open_positions": sum(1 for position in positions if position["quantity"] > 0),
            "pnl_available": True,
            "valuation_source": "local_trades",
        }

    def get_charts(self) -> dict:
        trades = self._filled_trades()
        positions = self._positions_with_mark_prices()
        starting_bankroll = self.settings.default_bankroll_usd

        cash_balance = starting_bankroll
        cumulative_volume = 0.0
        symbol_notional: dict[str, float] = defaultdict(float)
        trade_points: list[dict] = []
        equity_curve: list[dict] = []

        inventory_by_symbol = {
            position["symbol"]: {
                "quantity": position["quantity"],
                "mark_price": position["mark_price"],
            }
            for position in positions
        }

        running_quantities: dict[str, float] = defaultdict(float)
        for trade in sorted(trades, key=lambda item: item.created_at):
            notional = trade.price * trade.quantity
            cumulative_volume += notional
            symbol_notional[trade.symbol] += notional

            if trade.side == "BUY":
                cash_balance -= notional
                running_quantities[trade.symbol] += trade.quantity
            else:
                cash_balance += notional
                running_quantities[trade.symbol] -= trade.quantity

            inventory_value = 0.0
            for symbol, quantity in running_quantities.items():
                if quantity <= 0:
                    continue
                mark_price = inventory_by_symbol.get(symbol, {}).get("mark_price", trade.price)
                inventory_value += quantity * mark_price

            trade_points.append(
                {
                    "timestamp": trade.created_at.isoformat(),
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "price": round(trade.price, 2),
                    "quantity": round(trade.quantity, 8),
                    "notional": round(notional, 2),
                    "confidence": round(trade.confidence or 0, 2),
                }
            )
            equity_curve.append(
                {
                    "timestamp": trade.created_at.isoformat(),
                    "equity": round(cash_balance + inventory_value, 2),
                    "cash_balance": round(cash_balance, 2),
                    "cumulative_volume": round(cumulative_volume, 2),
                }
            )

        position_bars = [
                {
                    "symbol": position["symbol"],
                    "quantity": round(position["quantity"], 8),
                    "average_price": round(position["average_price"], 2),
                    "mark_price": round(position["mark_price"], 2),
                    "market_value": round(position["market_value"], 2),
                    "unrealized_pnl": round(position["unrealized_pnl_live"], 2),
                }
            for position in positions
            if position["quantity"] > 0
        ]

        return {
            "equity_curve": equity_curve,
            "trade_points": trade_points,
            "symbol_notional": [
                {"symbol": symbol, "notional": round(notional, 2)}
                for symbol, notional in sorted(symbol_notional.items())
            ],
            "position_bars": position_bars,
        }

    def _get_live_summary(self) -> dict:
        trades = self._filled_trades()
        balances = self.account_service.get_balance_map() if self.account_service is not None else {}
        all_prices = self.account_service.binance_client.get_all_prices()

        equity = 0.0
        open_positions = 0
        for asset, amounts in balances.items():
            total = amounts.get("total", 0)
            if total <= 0:
                continue

            asset_value = self._asset_value_in_usdt(asset, total, all_prices)
            equity += asset_value

            if self._normalized_asset(asset) not in {"USDT", "USDC", "BUSD", "FDUSD", "TUSD", "BRL"} and asset_value > 0:
                open_positions += 1

        spot_cash_balance = balances.get("USDT", {}).get("free", 0)
        recoverable_cash_balance = sum(
            amounts.get("free", 0) + amounts.get("locked", 0)
            for asset, amounts in balances.items()
            if asset.startswith("LD") and self._normalized_asset(asset) == "USDT"
        )
        tether_total_balance = sum(
            amounts.get("free", 0) + amounts.get("locked", 0)
            for asset, amounts in balances.items()
            if self._normalized_asset(asset) == "USDT"
        )
        cash_balance = spot_cash_balance
        inventory_value = max(equity - cash_balance, 0)
        gross_volume, buy_count, sell_count = self._trade_stats(trades)
        cash_recovery_required = spot_cash_balance <= 0 and recoverable_cash_balance > 0

        cash_note = "Spot USDT disponivel para trading."
        if cash_recovery_required:
            cash_note = (
                "Caixa em Tether concentrado em LDUSDT. "
                "E necessario resgatar/transferir para USDT spot antes de novas compras."
            )

        return {
            "mode": self.settings.app_mode,
            "starting_bankroll": round(equity, 2),
            "cash_balance": round(cash_balance, 2),
            "spot_cash_balance": round(spot_cash_balance, 2),
            "recoverable_cash_balance": round(recoverable_cash_balance, 2),
            "tether_total_balance": round(tether_total_balance, 2),
            "inventory_value": round(inventory_value, 2),
            "equity": round(equity, 2),
            "pnl_abs": 0.0,
            "pnl_pct": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_trades": len(trades),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "gross_volume": round(gross_volume, 2),
            "open_positions": open_positions,
            "pnl_available": False,
            "valuation_source": "binance_live_balances",
            "cash_recovery_required": cash_recovery_required,
            "cash_note": cash_note,
        }

    def _asset_value_in_usdt(
        self,
        asset: str,
        quantity: float,
        all_prices: dict[str, float],
    ) -> float:
        if quantity <= 0:
            return 0.0

        asset = self._normalized_asset(asset)
        stable_assets = {"USDT", "USDC", "BUSD", "FDUSD", "TUSD"}
        if asset in stable_assets:
            return quantity

        direct_symbol = f"{asset}USDT"
        direct_price = all_prices.get(direct_symbol, 0)
        if direct_price > 0:
            return quantity * direct_price

        inverse_symbol = f"USDT{asset}"
        inverse_price = all_prices.get(inverse_symbol, 0)
        if inverse_price > 0:
            return quantity / inverse_price

        return 0.0

    def _normalized_asset(self, asset: str) -> str:
        if asset.startswith("LD") and len(asset) > 2:
            return asset[2:]
        return asset

    def _trade_stats(self, trades: list[Trade]) -> tuple[float, int, int]:
        gross_volume = 0.0
        buy_count = 0
        sell_count = 0

        for trade in trades:
            notional = trade.price * trade.quantity
            gross_volume += notional
            if trade.side == "BUY":
                buy_count += 1
            else:
                sell_count += 1

        return gross_volume, buy_count, sell_count

    def _filled_trades(self) -> list[Trade]:
        statement = select(Trade).where(Trade.status == "FILLED").order_by(Trade.created_at.asc())
        return list(self.db.scalars(statement))

    def _positions_with_mark_prices(self) -> list[dict]:
        positions = list(self.db.scalars(select(Position).order_by(Position.updated_at.desc())))
        latest_prices = self._latest_market_prices()
        enriched_positions: list[dict] = []

        for position in positions:
            mark_price = latest_prices.get(position.symbol, position.current_price or position.average_price)
            enriched_positions.append(
                {
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "average_price": position.average_price,
                    "current_price": position.current_price,
                    "realized_pnl": position.realized_pnl or 0,
                    "mark_price": mark_price,
                    "market_value": position.quantity * mark_price,
                    "unrealized_pnl_live": (mark_price - position.average_price) * position.quantity,
                }
            )

        return enriched_positions

    def _latest_market_prices(self) -> dict[str, float]:
        statement = select(MarketSnapshot).order_by(MarketSnapshot.created_at.desc())
        snapshots = list(self.db.scalars(statement))
        latest_by_symbol: dict[str, float] = {}

        for snapshot in snapshots:
            if snapshot.symbol not in latest_by_symbol:
                latest_by_symbol[snapshot.symbol] = snapshot.price

        return latest_by_symbol
