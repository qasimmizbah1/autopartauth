import asyncpg
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import os
import hashlib


load_dotenv()


DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "ssl": "require",
}

print("DB CONFIG:", DB_CONFIG)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(**DB_CONFIG)

    async with app.state.pool.acquire() as conn:
    # Create users table


        await conn.execute("CREATE EXTENSION IF NOT EXISTS citext;")

        await conn.execute("""
                CREATE TABLE IF NOT EXISTS app_user ( 
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
                email CITEXT UNIQUE NOT NULL, 
                password_hash TEXT NOT NULL, 
                role TEXT NOT NULL CHECK (role IN ('buyer','supplier','admin')), 
                is_active BOOLEAN NOT NULL DEFAULT TRUE, 
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(), 
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now() 
                )
        """)

        # Create verification_tokens table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS verification_tokens (
                id SERIAL PRIMARY KEY,
                token VARCHAR(255) NOT NULL UNIQUE,
                user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_verification_tokens_token ON verification_tokens(token)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_verification_tokens_user_id ON verification_tokens(user_id)")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY, 
            user_id UUID NOT NULL,   
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT fk_user
                FOREIGN KEY(user_id)
                REFERENCES app_user(id)
                ON DELETE CASCADE
        )
        """)
        await conn.execute("""
           CREATE EXTENSION IF NOT EXISTS pgcrypto
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NULL REFERENCES app_user(id) ON DELETE SET NULL,
                level TEXT NOT NULL CHECK (level IN ('DEBUG','INFO','WARNING','ERROR','CRITICAL','AUDIT')),
                action TEXT NOT NULL,               -- short description, e.g. "USER_LOGIN"
                path TEXT,                          -- request path like "/auth/login"
                ip INET,                            -- client IP
                user_agent TEXT,
                meta JSONB NOT NULL DEFAULT '{}'::jsonb,  -- extra data
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute("""
           CREATE INDEX IF NOT EXISTS system_log_created_at_idx ON system_log (created_at DESC)
        """)
        await conn.execute("""
           CREATE INDEX IF NOT EXISTS system_log_user_id_idx ON system_log (user_id)
        """)
        await conn.execute("""
          CREATE INDEX IF NOT EXISTS system_log_level_idx ON system_log (level)
        """)
        await conn.execute("""
           CREATE INDEX IF NOT EXISTS system_log_meta_gin ON system_log USING GIN (meta)
        """)
        
        demo_users = [
            ("qasimmizbah@gmail.com", "Admin123", "admin", "TRUE"),
            ("muskan@techbeeps.co.in", "Admin123", "buyer", "TRUE"),
            ("mprofessionalwfh@gmail.com", "Admin123", "supplier", "TRUE"),
        ]

        for email, password, role, is_active in demo_users:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            await conn.execute("""
                INSERT INTO app_user (email, password_hash, role, is_active)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (email) DO NOTHING
            """, email, password_hash, role, is_active)


    yield
    await app.state.pool.close()
