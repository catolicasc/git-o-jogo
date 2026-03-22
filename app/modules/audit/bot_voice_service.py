import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.portfolio.account_service import AccountService
from app.modules.portfolio.performance_service import PerformanceService
from app.shared.db.models import JobRun, Trade


class BotVoiceService:
    def __init__(
        self,
        db: Session,
        mode: str,
        performance_service: PerformanceService,
        account_service: AccountService,
    ) -> None:
        self.db = db
        self.mode = mode
        self.performance_service = performance_service
        self.account_service = account_service

    def build_briefing(self) -> str:
        summary = self.performance_service.get_summary()
        latest_job = self.db.scalar(select(JobRun).order_by(JobRun.started_at.desc()).limit(1))
        latest_trade = self.db.scalar(select(Trade).order_by(Trade.created_at.desc()).limit(1))

        pnl_text = (
            f"PnL: {summary['pnl_abs']:.2f} USD ({summary['pnl_pct']:.2f}%)."
            if summary.get("pnl_available", True)
            else "PnL: indisponivel no modo live sem baseline confiavel."
        )

        lines = [
            f"Modo atual: {self.mode}.",
            f"Equity: {summary['equity']:.2f} USD.",
            f"Caixa: {summary['cash_balance']:.2f} USD.",
            pnl_text,
            f"Trades executados: {summary['total_trades']}.",
            f"Posicoes abertas: {summary['open_positions']}.",
        ]

        if latest_job is not None:
            lines.append(
                f"Ultimo job: {latest_job.job_name} com status {latest_job.status}."
            )

        if latest_trade is not None:
            lines.append(
                f"Ultimo trade: {latest_trade.side} {latest_trade.symbol} a {latest_trade.price:.2f}."
            )

        try:
            account = self.account_service.get_account_overview()
            top_balances = ", ".join(
                f"{item['asset']}={item['total']:.6f}" for item in account["balances"][:5]
            )
            if top_balances:
                lines.append(f"Saldos principais: {top_balances}.")
        except Exception:
            lines.append("Nao consegui consultar os saldos da Binance agora.")

        lines.append("Proximo passo: seguir monitorando sinais, risco e saldo antes de agir.")
        return " ".join(lines)

    def answer_question(self, question: str) -> str:
        normalized = question.lower().strip()
        summary = self.performance_service.get_summary()

        if any(term in normalized for term in ["oi", "ola", "olá", "e ai", "e aí"]):
            return "Oi. Estou online e acompanhando mercado, risco, saldo e execucao do bot."

        if "o que voce fez" in normalized or "o que você fez" in normalized:
            return self.build_briefing()

        if "equity" in normalized or "pnl" in normalized or "lucro" in normalized:
            if not summary.get("pnl_available", True):
                return (
                    f"Equity atual {summary['equity']:.2f} USD, "
                    f"caixa {summary['cash_balance']:.2f} USD. "
                    "PnL esta indisponivel porque no modo live eu uso o saldo real da Binance "
                    "sem uma linha de base historica confiavel."
                )
            return (
                f"Equity atual {summary['equity']:.2f} USD, "
                f"PnL {summary['pnl_abs']:.2f} USD, "
                f"caixa {summary['cash_balance']:.2f} USD."
            )

        if "saldo" in normalized or "moedas" in normalized or "carteira" in normalized:
            try:
                account = self.account_service.get_account_overview()
                balances = ", ".join(
                    f"{item['asset']}={item['total']:.6f}" for item in account["balances"][:8]
                )
                return balances or "No momento nao encontrei saldos diferentes de zero."
            except Exception:
                return "Nao consegui consultar os saldos da Binance agora."

        if "trade" in normalized or "ordem" in normalized:
            latest_trade = self.db.scalar(select(Trade).order_by(Trade.created_at.desc()).limit(1))
            if latest_trade is None:
                return "Ainda nao tenho trade registrado."
            return (
                f"Ultimo trade: {latest_trade.side} {latest_trade.symbol} "
                f"a {latest_trade.price:.2f}, status {latest_trade.status}."
            )

        if re.search(r"\b(plano|pretende|vai fazer)\b", normalized):
            return (
                "Meu plano e continuar monitorando os simbolos da allowlist, validar risco, "
                "respeitar cooldown, saldo real e limites antes de comprar ou vender."
            )

        return (
            "Posso te responder sobre equity, pnl, saldo, trades, ordens e plano do bot. "
            "Pergunte algo como: o que voce fez, qual o pnl, quais moedas eu tenho, qual seu plano."
        )
