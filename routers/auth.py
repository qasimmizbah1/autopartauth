from fastapi import APIRouter, Request, BackgroundTasks, Body, Depends, HTTPException
from models import UserRegister, UserLogin, UserOut, ForgotPasswordRequest, ResetPasswordRequest
from services.login_service import user_login_service
from services.register_service import user_register_service, user_verify_service, user_resend_verification_service
from services.password_service import user_change_password_service, forgot_password_service, reset_password_service
from deps import require_login

router = APIRouter(prefix="/v1/auth", tags=["Auth"])

# Endpoint to Register
@router.post("/register", response_model=UserOut)
async def register_user(user: UserRegister, request: Request, background_tasks: BackgroundTasks):
    return await user_register_service(user, request, background_tasks)


@router.get("/verify-email")
async def verify_email(token: str, request: Request):
    return await user_verify_service(token, request)    


@router.post("/resend-verification")
async def resend_verification(email: str, request: Request, background_tasks: BackgroundTasks):
    return await user_resend_verification_service(email, request, background_tasks)
    
    
# Endpoint to Login
@router.post("/login")
async def login_user(user: UserLogin, request: Request):
    return await user_login_service(user, request)
    

# Endpoint to change password
@router.post("/change-password")
async def change_password(
    email: str = Body(..., embed=True),   # or use JWT later for authenticated user
    old_password: str = Body(..., embed=True),
    new_password: str = Body(..., embed=True),
    confirm_new_password: str = Body(..., embed=True),
    request: Request = None,
    payload: dict = Depends(require_login)
):
    return await user_change_password_service(
        email, old_password, new_password, confirm_new_password, request
    )   


# ---- Forgot password ----
@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, request: Request):
    return await forgot_password_service(data.email, request)


# ---- Reset password ----
@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, request: Request):
   return await reset_password_service(data, request)


# view all users

@router.get("/viewusers", response_model=List[Dict])
async def view_users(request: Request):
    try:
        async with request.app.state.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM app_user")
            users = [dict(row) for row in rows]  # convert asyncpg Record to dict
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))