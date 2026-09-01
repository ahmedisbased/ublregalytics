from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    permissions: list
    model_config = ConfigDict(from_attributes=True)


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str


class LogoutRequest(BaseModel):
    # access token comes from the Authorization header; the refresh token is
    # sent in the body so it can be revoked too.
    refresh_token: str | None = None
