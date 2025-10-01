from datetime import timedelta
from fastapi import HTTPException, Request
from utils.security import verify_password, create_access_token
from services.logs_service import write_log


async def user_login_service(user, request: Request):
    async with request.app.state.pool.acquire() as conn:
        db_user = await conn.fetchrow("SELECT * FROM app_user WHERE is_active=true and email=$1", user.email)
        print("User found:", db_user)  # Debugging line
        print("User Email:", user.email)  # Debugging line
       
