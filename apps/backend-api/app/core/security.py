from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: UUID
    email: str | None
    role: str
    organization_id: UUID | None = None


bearer = HTTPBearer(auto_error=False)


@lru_cache
def jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{url.rstrip('/')}/auth/v1/.well-known/jwks.json", cache_keys=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_dev_user_id: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if settings.auth_disabled and settings.app_env in {"development", "test"}:
        dev_id = UUID(x_dev_user_id or "00000000-0000-0000-0000-000000000001")
        return CurrentUser(id=dev_id, email="dev@example.com", role="admin")
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")

    token = credentials.credentials
    try:
        signing_key = jwks_client(settings.supabase_url).get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience=settings.supabase_jwt_audience,
            options={"require": ["exp", "sub"]},
        )
        app_metadata = payload.get("app_metadata") or {}
        org_value = app_metadata.get("organization_id")
        return CurrentUser(
            id=UUID(payload["sub"]),
            email=payload.get("email"),
            role=app_metadata.get("role", payload.get("role", "authenticated")),
            organization_id=UUID(org_value) if org_value else None,
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o vencido",
        ) from exc


UserDependency = Annotated[CurrentUser, Depends(get_current_user)]
