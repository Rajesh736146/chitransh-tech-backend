-- Social interaction tables for profile module
-- Run this against your Neon PostgreSQL database

-- User Connections (follow/unfollow)
CREATE TABLE IF NOT EXISTS public.user_connections (
    id uuid DEFAULT uuid_generate_v4() NOT NULL,
    follower_id uuid NOT NULL,
    following_id uuid NOT NULL,
    created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    CONSTRAINT user_connections_pkey PRIMARY KEY (id),
    CONSTRAINT uq_user_connections UNIQUE (follower_id, following_id),
    CONSTRAINT fk_connections_follower FOREIGN KEY (follower_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_connections_following FOREIGN KEY (following_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_connections_follower ON public.user_connections (follower_id);
CREATE INDEX IF NOT EXISTS idx_connections_following ON public.user_connections (following_id);

-- Profile Views
CREATE TABLE IF NOT EXISTS public.profile_views (
    id uuid DEFAULT uuid_generate_v4() NOT NULL,
    viewer_id uuid NOT NULL,
    viewed_id uuid NOT NULL,
    viewed_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    CONSTRAINT profile_views_pkey PRIMARY KEY (id),
    CONSTRAINT fk_profile_views_viewer FOREIGN KEY (viewer_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_profile_views_viewed FOREIGN KEY (viewed_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_profile_views_viewer ON public.profile_views (viewer_id);
CREATE INDEX IF NOT EXISTS idx_profile_views_viewed ON public.profile_views (viewed_id);

-- Skill Endorsements
CREATE TABLE IF NOT EXISTS public.skill_endorsements (
    id uuid DEFAULT uuid_generate_v4() NOT NULL,
    endorser_id uuid NOT NULL,
    skill_id uuid NOT NULL,
    created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    CONSTRAINT skill_endorsements_pkey PRIMARY KEY (id),
    CONSTRAINT uq_skill_endorsement UNIQUE (endorser_id, skill_id),
    CONSTRAINT fk_endorsement_endorser FOREIGN KEY (endorser_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_endorsement_skill FOREIGN KEY (skill_id) REFERENCES public.user_skills(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_endorsements_endorser ON public.skill_endorsements (endorser_id);
CREATE INDEX IF NOT EXISTS idx_endorsements_skill ON public.skill_endorsements (skill_id);

-- Profile Shares
CREATE TABLE IF NOT EXISTS public.profile_shares (
    id uuid DEFAULT uuid_generate_v4() NOT NULL,
    sharer_id uuid NOT NULL,
    shared_profile_id uuid NOT NULL,
    platform varchar(50) NULL,
    created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    CONSTRAINT profile_shares_pkey PRIMARY KEY (id),
    CONSTRAINT fk_shares_sharer FOREIGN KEY (sharer_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_shares_profile FOREIGN KEY (shared_profile_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_shares_sharer ON public.profile_shares (sharer_id);
CREATE INDEX IF NOT EXISTS idx_shares_profile ON public.profile_shares (shared_profile_id);
