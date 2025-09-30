import uuid
from fastapi import HTTPException, Request
from utils.security import verify_password
from utils.security import hash_password, verify_password 
from datetime import datetime, timedelta
import hashlib

async def user_change_password_service(
    email, old_password,new_password,confirm_new_password,request: Request = None
):
    if new_password != confirm_new_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")

    async with request.app.state.pool.acquire() as conn:
        # fetch user
        db_user = await conn.fetchrow("SELECT * FROM app_user WHERE email=$1", email)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        # verify old password
        if not verify_password(old_password, db_user["password_hash"]):
            raise HTTPException(status_code=401, detail="Old password is incorrect")

        # hash new password
        hashed_password = hash_password(new_password)

        # update DB
        await conn.execute(
            "UPDATE app_user SET password_hash=$1 WHERE email=$2",
            hashed_password, email
        )

        return {"message": "Password changed successfully"}
    

async def forgot_password_service(email, request: Request):
    
    async with request.app.state.pool.acquire() as conn:

        db_user = await conn.fetchrow("SELECT id, email FROM app_user WHERE email=$1", email)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
    

        token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=1)

        # store token in reset_tokens table (create this table in DB)
        await conn.execute("""
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES ($1, $2, $3)
        """, db_user["id"], token, expires_at)

        reset_link = f"{request.base_url}auth/reset-password?token={token}"

        # TODO: integrate real email sender
        print("Send this reset link via email:", reset_link)

        return {"message": "Password reset link sent to email"}
    


async def reset_password_service(data, request: Request):

    async with request.app.state.pool.acquire() as conn:
         
        token_data = await conn.fetchrow("""
            SELECT user_id, expires_at FROM password_reset_tokens
            WHERE token=$1
        """, data.token)

        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid token")

        if token_data["expires_at"] < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Token expired")

        # update password
        hashed_pw = hash_password(data.new_password)
        user_id = uuid.UUID(token_data["user_id"]) if isinstance(token_data["user_id"], str) else token_data["user_id"]
        #await conn.execute("UPDATE app_user SET password_hash=$1 WHERE id=$2", hashed_pw, token_data["user_id"])

   
    
        await conn.execute(
        "UPDATE app_user SET password_hash=$1 WHERE id=$2",
        hashed_pw,
        user_id
        )

    
        await conn.execute("DELETE FROM password_reset_tokens WHERE token=$1", data.token)



    # delete token after use
   
    return {"message": "Password reset successfully"}
        
                
    