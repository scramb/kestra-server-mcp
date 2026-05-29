"""register_kestra_token MCP tool -- store a Kestra API token for the authenticated user."""

from src.auth.session import current_user_id
from src.auth.token_store import TokenStore

_store: TokenStore | None = None


def set_token_store(store: TokenStore) -> None:
    global _store
    _store = store


async def handle(arguments: dict) -> dict:
    user_id = current_user_id.get()
    if not user_id:
        return {"error": True, "code": "UNAUTHENTICATED", "message": "No active user session"}

    kestra_token = arguments.get("token", "").strip()
    if not kestra_token:
        return {"error": True, "code": "MISSING_TOKEN", "message": "token field is required"}

    assert _store is not None
    _store.store_token(user_id, kestra_token)
    return {"status": "stored", "user_id": user_id}
