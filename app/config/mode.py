from app.config.settings import get_settings


def get_app_mode() -> str:
    return get_settings().app_mode


def is_observe_mode() -> bool:
    return get_app_mode() == "observe"


def is_paper_mode() -> bool:
    return get_app_mode() == "paper"


def is_live_mode() -> bool:
    return get_app_mode() == "live"
