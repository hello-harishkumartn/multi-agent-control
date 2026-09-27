import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException

from app.core.config import get_settings


ROLE_PERMISSIONS = {
    "viewer": {"read"},
    "operator": {"read", "run:create", "approval:decide", "tool:invoke"},
    "admin": {"*"},
}


@dataclass(frozen=True)
class Principal:
    name: str
    role: str

    def can(self, permission: str) -> bool:
        permissions = ROLE_PERMISSIONS.get(self.role, set())
        return "*" in permissions or permission in permissions or permission == "read"


class RateLimiter:
    def __init__(self) -> None:
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int) -> None:
        now = time.monotonic()
        bucket = self.events[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(429, "Rate limit exceeded")
        bucket.append(now)


limiter = RateLimiter()


def get_principal(
    x_api_key: str | None = Header(default=None),
    x_user: str = Header(default="local-user"),
    x_role: str = Header(default="admin"),
) -> Principal:
    settings = get_settings()
    if settings.environment != "test" and x_api_key not in (None, settings.api_key):
        raise HTTPException(401, "Invalid API key")
    if x_role not in ROLE_PERMISSIONS:
        raise HTTPException(403, "Unknown role")
    limiter.check(x_user, settings.max_requests_per_minute)
    return Principal(x_user, x_role)


def require(permission: str):
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.can(permission):
            raise HTTPException(403, f"Missing permission: {permission}")
        return principal

    return dependency


def tool_allowed(agent_permissions: list[str], required: str) -> bool:
    return "tool:*" in agent_permissions or required in agent_permissions

