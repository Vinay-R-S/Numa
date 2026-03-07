from fastapi import APIRouter, Depends, HTTPException, status

from .schemas import SignUpRequest, SignInRequest, TokenResponse, UserResponse, ExchangeRequest
from .service import sign_up, sign_in, exchange_supabase_token, JWT_EXPIRE_SECONDS
from .dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Email / Password ──────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignUpRequest):
    """Register with email + password. Returns a 2-day JWT."""
    try:
        result = sign_up(body.email, body.password, body.full_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return TokenResponse(access_token=result["token"], expires_in=JWT_EXPIRE_SECONDS)


@router.post("/signin", response_model=TokenResponse)
def signin(body: SignInRequest):
    """Sign in with email + password. Returns a 2-day JWT."""
    try:
        result = sign_in(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return TokenResponse(access_token=result["token"], expires_in=JWT_EXPIRE_SECONDS)


# ── OAuth token exchange (Google / GitHub) ────────────────────────────────────

@router.post("/exchange", response_model=TokenResponse)
def exchange(body: ExchangeRequest):
    """
    Accept the Supabase access_token that the frontend receives after OAuth
    (Google / GitHub) and return our own 2-day JWT.
    """
    try:
        result = exchange_supabase_token(body.supabase_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return TokenResponse(access_token=result["token"], expires_in=JWT_EXPIRE_SECONDS)


# ── Protected endpoints ───────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(
        id=current_user["sub"],
        email=current_user["email"],
        full_name=current_user.get("full_name") or None,
    )


@router.post("/signout")
def signout():
    """
    Stateless sign-out — the client simply discards its JWT.
    Supabase session tokens are short-lived; our JWT expiry handles revocation.
    """
    return {"message": "Signed out successfully."}
