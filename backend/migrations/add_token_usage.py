"""
Database migration: Add token usage tracking and enhance documents table

This migration:
1. Creates token_usage table for tracking LLM token consumption
2. Adds metadata columns to documents table (file_size, page_count, chunk_count, status)
3. Creates indexes for performance
"""

import asyncio
from app.core.database import get_db_session


async def run_migration():
    """Execute the migration"""
    async with get_db_session() as db:
        # SQL statements
        migration_sql = """
        -- Create token_usage table
        CREATE TABLE IF NOT EXISTS public.token_usage (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
            model VARCHAR(255) NOT NULL,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd DECIMAL(10, 6),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Create indexes for token_usage
        CREATE INDEX IF NOT EXISTS idx_token_usage_conversation 
            ON public.token_usage(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_token_usage_created_at 
            ON public.token_usage(created_at);
        CREATE INDEX IF NOT EXISTS idx_token_usage_model 
            ON public.token_usage(model);

        -- Add columns to documents table (if they don't exist)
        DO $$ 
        BEGIN
            -- Add file_size column
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='file_size'
            ) THEN
                ALTER TABLE public.documents ADD COLUMN file_size BIGINT;
            END IF;

            -- Add page_count column
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='page_count'
            ) THEN
                ALTER TABLE public.documents ADD COLUMN page_count INTEGER;
            END IF;

            -- Add chunk_count column
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='chunk_count'
            ) THEN
                ALTER TABLE public.documents ADD COLUMN chunk_count INTEGER;
            END IF;

            -- Add status column
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='status'
            ) THEN
                ALTER TABLE public.documents 
                ADD COLUMN status VARCHAR(50) DEFAULT 'indexed';
            END IF;
        END $$;

        -- Create index on documents status
        CREATE INDEX IF NOT EXISTS idx_documents_status 
            ON public.documents(status);
        """

        # Execute migration
        await db.execute(migration_sql)
        await db.commit()
        print("✅ Migration completed successfully!")
        print("   - Created token_usage table")
        print("   - Added indexes for token_usage")
        print("   - Enhanced documents table with metadata columns")
        print("   - Created indexes for documents")


async def rollback_migration():
    """Rollback the migration"""
    async with get_db_session() as db:
        rollback_sql = """
        -- Drop indexes
        DROP INDEX IF EXISTS public.idx_token_usage_conversation;
        DROP INDEX IF EXISTS public.idx_token_usage_created_at;
        DROP INDEX IF EXISTS public.idx_token_usage_model;
        DROP INDEX IF EXISTS public.idx_documents_status;

        -- Drop token_usage table
        DROP TABLE IF EXISTS public.token_usage;

        -- Remove columns from documents (optional - commented out for safety)
        -- ALTER TABLE public.documents DROP COLUMN IF EXISTS file_size;
        -- ALTER TABLE public.documents DROP COLUMN IF EXISTS page_count;
        -- ALTER TABLE public.documents DROP COLUMN IF EXISTS chunk_count;
        -- ALTER TABLE public.documents DROP COLUMN IF EXISTS status;
        """

        await db.execute(rollback_sql)
        await db.commit()
        print("✅ Rollback completed successfully!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("🔄 Rolling back migration...")
        asyncio.run(rollback_migration())
    else:
        print("🚀 Running migration...")
        asyncio.run(run_migration())
