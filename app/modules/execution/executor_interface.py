from typing import Protocol

from app.shared.types.domain import ExecutionRequest, ExecutionResult


class Executor(Protocol):
    def execute(self, order: ExecutionRequest) -> ExecutionResult: ...
