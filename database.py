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

        await conn.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_model ( 
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
                make_id UUID NOT NULL REFERENCES vehicle_make(id), 
                name TEXT NOT NULL, 
                UNIQUE(make_id, name) 
            )
        """)
        await conn.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_trim ( 
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
                model_id UUID NOT NULL REFERENCES vehicle_model(id), 
                year_from SMALLINT, 
                year_to SMALLINT, 
                trim TEXT
                )
        """)
        await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS vehicle_trim_unique_idx 
                    ON vehicle_trim (
                    model_id, 
                    COALESCE(year_from, 0), 
                    COALESCE(year_to, 0), 
                    COALESCE(trim, '')
                    )
        """)
        await conn.execute("""
                CREATE TABLE IF NOT EXISTS part_request (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES app_user(id),
                title TEXT NOT NULL,
                description TEXT,
                urgency TEXT CHECK (urgency IN ('low','normal','high','critical')) NOT NULL,
                required_by_date DATE,
                vehicle_make TEXT NOT NULL,
                vehicle_model TEXT NOT NULL,
                vehicle_model_trim TEXT NOT NULL,
                attachment TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
        """)
        await conn.execute("""
            CREATE TABLE  IF NOT EXISTS supplier_profile ( 
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
            user_id UUID NOT NULL REFERENCES app_user(id) UNIQUE, 
            supplier_name varchar(255),
            company_name TEXT, 
            kyc_status TEXT NOT NULL DEFAULT 'pending' CHECK (kyc_status IN 
            ('pending','approved','rejected')), 
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), 
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now() 
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS buyer_profile (
                  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
                    user_id UUID NOT NULL REFERENCES app_user(id) UNIQUE, 
                    buyer_name varchar(255),
                    company_name TEXT, 
                    vat_number TEXT, 
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), 
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now() 
            )
        """)
        await conn.execute("""
            CREATE TABLE  IF NOT EXISTS supplier_profile ( 
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
            user_id UUID NOT NULL REFERENCES app_user(id) UNIQUE, 
            supplier_name varchar(255),
            company_name TEXT, 
            kyc_status TEXT NOT NULL DEFAULT 'pending' CHECK (kyc_status IN 
            ('pending','approved','rejected')), 
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), 
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now() 
            )
        """)
        await conn.execute("""
                        CREATE TABLE  IF NOT EXISTS buyer_address ( 
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            buyer_id UUID NOT NULL REFERENCES buyer_profile(id),  
            line1 TEXT NOT NULL, 
            line2 TEXT, 
            city TEXT, 
            province TEXT, 
            postal_code TEXT, 
            country CHAR(2) NOT NULL DEFAULT 'ZA' 
            )
        """)
        await conn.execute("""
                CREATE TABLE IF NOT EXISTS quote ( 
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
                    request_id UUID NOT NULL REFERENCES part_request(id) ON DELETE CASCADE, 
                    supplier_id UUID NOT NULL REFERENCES supplier_profile(id), 
                    price_cents BIGINT NOT NULL CHECK (price_cents >= 0), 
                    currency CHAR(3) NOT NULL DEFAULT 'ZAR', 
                    eta_days SMALLINT, 
                    terms TEXT, 
                    is_accepted BOOLEAN NOT NULL DEFAULT FALSE, 
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now() 
                    )
        """)
        await conn.execute("""
            CREATE TABLE  IF NOT EXISTS supplier_profile ( 
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
            user_id UUID NOT NULL REFERENCES app_user(id) UNIQUE, 
            supplier_name varchar(255),
            company_name TEXT, 
            kyc_status TEXT NOT NULL DEFAULT 'pending' CHECK (kyc_status IN 
            ('pending','approved','rejected')), 
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), 
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now() 
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS buyer_profile (
                  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
                    user_id UUID NOT NULL REFERENCES app_user(id) UNIQUE, 
                    buyer_name varchar(255),
                    company_name TEXT, 
                    vat_number TEXT, 
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), 
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now() 
            )
        """)
        await conn.execute("""
            CREATE TABLE  IF NOT EXISTS supplier_profile ( 
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
            user_id UUID NOT NULL REFERENCES app_user(id) UNIQUE, 
            supplier_name varchar(255),
            company_name TEXT, 
            kyc_status TEXT NOT NULL DEFAULT 'pending' CHECK (kyc_status IN 
            ('pending','approved','rejected')), 
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), 
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now() 
            )
        """)

        
        
        demo_users = [
            ("qasimmizbah@gmail.com", "Admin123", "admin", True),
            ("muskan@techbeeps.co.in", "Admin123", "buyer", True),
            ("mprofessionalwfh@gmail.com", "Admin123", "supplier", True),
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
