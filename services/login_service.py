from datetime import timedelta
from fastapi import HTTPException, Request
from utils.security import verify_password, create_access_token
from services.logs_service import write_log


async def user_login_service(user, request: Request):
    async with request.app.state.pool.acquire() as conn:
        db_user = await conn.fetchrow("SELECT * FROM app_user WHERE is_active=TRUE and email=$1", user.email)
        print("User found:", db_user)  # Debugging line
        if not db_user or not verify_password(user.password, db_user["password_hash"]):
            await write_log(
                request=request,
                action="LOGIN_FAILED",
                level="WARNING",
                user_id=None,
                path=str(request.url.path),
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                meta={"email": user.email}
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")

        
        token_expires = timedelta(minutes=3600)
        access_token = create_access_token(
            data={"user_id": str(db_user["id"]),"role": db_user["role"]}, expires_delta=token_expires
        )
        
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user["id"],
                "email": db_user["email"],
                "role": db_user["role"],
                "is_active": db_user["is_active"],
            }
        }
