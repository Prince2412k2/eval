"""
Database migration for conversation management tables.

Run this migration to create the conversations and messages tables.

Usage:
    python -m alembic revision --autogenerate -m "add_conversation_tables"
    python -m alembic upgrade head

Or manually run the SQL below.
"""

CREATE_TABLES_SQL = """
-- Create message_roles enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE message_roles AS ENUM ('user', 'assistant', 'system');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create conversations table
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    title VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    documents_discussed TEXT[] DEFAULT '{}',
    topics_covered TEXT[] DEFAULT '{}'
);

-- Create messages table
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    role message_roles NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sources TEXT[],
    citations JSONB,
    extra_metadata JSONB
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON public.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON public.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON public.messages(created_at);

-- Add comment
COMMENT ON TABLE public.conversations IS 'Stores conversation sessions for chat history';
COMMENT ON TABLE public.messages IS 'Stores individual messages within conversations';
"""

DROP_TABLES_SQL = """
-- Drop tables (for rollback)
DROP TABLE IF EXISTS public.messages CASCADE;
DROP TABLE IF EXISTS public.conversations CASCADE;
DROP TYPE IF EXISTS message_roles;
"""

if __name__ == "__main__":
    print("Conversation Management Migration")
    print("=" * 50)
    print("\nTo apply this migration, run:")
    print("\nOption 1 - Using psql:")
    print("  psql -U <user> -d <database> -f migrations/add_conversation_tables.sql")
    print("\nOption 2 - Using Python:")
    print("  python migrations/add_conversation_tables.py")
    print("\n" + "=" * 50)
    print("\nSQL to execute:")
    print(CREATE_TABLES_SQL)
