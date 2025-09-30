from datetime import timedelta
from fastapi import HTTPException, Request
from utils.security import verify_password, create_access_token
from services.logs_service import write_log


async def user_login_service(user, request: Request):
    async with request.app.state.pool.acquire() as conn:
        db_user = await conn.fetchrow("SELECT * FROM app_user WHERE is_active='true' and email=$1", user.email)
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

        
        
        return {
            "user": {
                "id": db_user["id"],
                "email": db_user["email"],
                "role": db_user["role"],
                "is_active": db_user["is_active"],
            }
        }
