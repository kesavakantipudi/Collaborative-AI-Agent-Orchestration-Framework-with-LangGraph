import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://agent_user:agent_pass@db:5432/agent_db')

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    # create extension and tasks table
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS pgcrypto'))
        conn.execute(text('''
        CREATE TABLE IF NOT EXISTS tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            prompt TEXT NOT NULL,
            status VARCHAR(50) NOT NULL,
            result TEXT NULL,
            agent_logs JSONB NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        '''))
        conn.commit()
