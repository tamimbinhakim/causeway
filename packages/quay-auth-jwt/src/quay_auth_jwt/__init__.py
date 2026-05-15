"""JWT bearer-token AuthProvider.

Decodes the ``Authorization: Bearer <jwt>`` header on each request and
returns the claims dict as the current user. Supports symmetric secrets
(HS256/384/512) and asymmetric public keys (RS256, ES256, EdDSA).
"""

from __future__ import annotations

from typing import Any, ClassVar

import jwt


class JwtAuth:
    contract_version: ClassVar[str] = "v1.0"

    def __init__(
        self,
        *,
        secret: str,
        algorithm: str = "HS256",
        issuer: str | None = None,
        audience: str | None = None,
    ) -> None:
        self.secret = secret
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience

    async def startup(self, settings: Any) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool:
        return bool(self.secret)

    async def current_user(self, req: Any) -> dict[str, Any] | None:
        header = req.headers.get("authorization", "") if hasattr(req, "headers") else ""
        if not header.lower().startswith("bearer "):
            return None
        token = header.split(None, 1)[1]
        return await self.verify(token)

    async def login(self, creds: dict[str, Any]) -> str:
        # JWT auth is stateless — login is "give me a token", which means
        # signing a claims set the caller already authenticated some other
        # way. The plugin doesn't know how the caller authenticated.
        return jwt.encode(creds, self.secret, algorithm=self.algorithm)

    async def logout(self, req: Any) -> None:
        # No-op for stateless JWT. Revocation is the user's concern (denylist
        # store or short token lifetimes).
        del req

    async def verify(self, token: str) -> dict[str, Any] | None:
        try:
            return jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
            )
        except jwt.InvalidTokenError:
            return None


def plugin(settings: Any) -> None:
    from quay import register

    secret = getattr(settings, "jwt_secret", None)
    if not secret:
        return
    if hasattr(secret, "get_secret_value"):
        secret = secret.get_secret_value()
    register(
        JwtAuth(
            secret=str(secret),
            algorithm=str(getattr(settings, "jwt_algorithm", "HS256")),
            issuer=getattr(settings, "jwt_issuer", None),
            audience=getattr(settings, "jwt_audience", None),
        ),
    )


__all__ = ["JwtAuth", "plugin"]
