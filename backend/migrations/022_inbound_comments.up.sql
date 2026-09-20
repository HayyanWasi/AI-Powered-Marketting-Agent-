CREATE TABLE linkedin_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    linkedin_account_id UUID NOT NULL REFERENCES linkedin_accounts(id) ON DELETE CASCADE,
    post_social_id TEXT NOT NULL,
    remote_comment_id TEXT NOT NULL,
    text TEXT NOT NULL,
    author_provider_id TEXT,
    author_name TEXT,
    is_own_comment BOOLEAN NOT NULL DEFAULT false,
    parent_comment_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(linkedin_account_id, remote_comment_id)
);

CREATE TABLE linkedin_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    linkedin_account_id UUID NOT NULL REFERENCES linkedin_accounts(id) ON DELETE CASCADE,
    target_remote_comment_id TEXT NOT NULL,
    reply_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    remote_reply_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(linkedin_account_id, target_remote_comment_id, reply_text)
);

