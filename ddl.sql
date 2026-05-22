-- public.companies definition

-- Drop table

-- DROP TABLE public.companies;

CREATE TABLE public.companies (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	company_name varchar(255) NOT NULL,
	company_description text NULL,
	website text NULL,
	logo_url text NULL,
	company_size varchar(100) NULL,
	industry varchar(255) NULL,
	headquarters varchar(255) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT companies_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_companies_name ON public.companies USING btree (company_name);


-- public.roles definition

-- Drop table

-- DROP TABLE public.roles;

CREATE TABLE public.roles (
	id bigserial NOT NULL,
	role_name varchar(100) NOT NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT roles_pkey PRIMARY KEY (id),
	CONSTRAINT roles_role_name_key UNIQUE (role_name)
);


-- public.users definition

-- Drop table

-- DROP TABLE public.users;

CREATE TABLE public.users (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	full_name varchar(255) NOT NULL,
	email varchar(255) NOT NULL,
	phone varchar(20) NULL,
	password_hash text NOT NULL,
	role_id int8 NOT NULL,
	profile_image text NULL,
	status varchar(50) DEFAULT 'ACTIVE'::character varying NULL,
	email_verified bool DEFAULT false NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	verification_token text NULL,
	password_reset_token text NULL,
	password_reset_expires_at timestamp NULL,
	CONSTRAINT users_email_key UNIQUE (email),
	CONSTRAINT users_pkey PRIMARY KEY (id),
	CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES public.roles(id)
);
CREATE INDEX idx_users_email ON public.users USING btree (email);
CREATE INDEX idx_users_role_id ON public.users USING btree (role_id);


-- public.employer_profiles definition

-- Drop table

-- DROP TABLE public.employer_profiles;

CREATE TABLE public.employer_profiles (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	company_id uuid NOT NULL,
	designation varchar(255) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT employer_profiles_pkey PRIMARY KEY (id),
	CONSTRAINT employer_profiles_user_id_key UNIQUE (user_id),
	CONSTRAINT fk_employer_profiles_company FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE,
	CONSTRAINT fk_employer_profiles_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_employer_profiles_company_id ON public.employer_profiles USING btree (company_id);


-- public.feed_posts definition

-- Drop table

-- DROP TABLE public.feed_posts;

CREATE TABLE public.feed_posts (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	author_id uuid NULL,
	post_type varchar(50) NOT NULL,
	title varchar(500) NULL,
	"content" text NULL,
	media_url text NULL,
	external_link text NULL,
	visibility varchar(50) DEFAULT 'PUBLIC'::character varying NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT feed_posts_pkey PRIMARY KEY (id),
	CONSTRAINT fk_feed_posts_author FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE SET NULL
);


-- public.feed_reactions definition

-- Drop table

-- DROP TABLE public.feed_reactions;

CREATE TABLE public.feed_reactions (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	post_id uuid NOT NULL,
	user_id uuid NOT NULL,
	reaction_type varchar(50) DEFAULT 'LIKE'::character varying NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT feed_reactions_pkey PRIMARY KEY (id),
	CONSTRAINT fk_feed_reactions_post FOREIGN KEY (post_id) REFERENCES public.feed_posts(id) ON DELETE CASCADE,
	CONSTRAINT fk_feed_reactions_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);


-- public.jobs definition

-- Drop table

-- DROP TABLE public.jobs;

CREATE TABLE public.jobs (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	company_id uuid NOT NULL,
	title varchar(255) NOT NULL,
	description text NOT NULL,
	employment_type varchar(100) NULL,
	experience_required varchar(100) NULL,
	salary_min numeric(12, 2) NULL,
	salary_max numeric(12, 2) NULL,
	"location" varchar(255) NULL,
	remote_type varchar(100) NULL,
	status varchar(50) DEFAULT 'OPEN'::character varying NULL,
	posted_by uuid NOT NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT jobs_pkey PRIMARY KEY (id),
	CONSTRAINT fk_jobs_company FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE,
	CONSTRAINT fk_jobs_posted_by FOREIGN KEY (posted_by) REFERENCES public.users(id)
);
CREATE INDEX idx_jobs_company_id ON public.jobs USING btree (company_id);
CREATE INDEX idx_jobs_location ON public.jobs USING btree (location);
CREATE INDEX idx_jobs_status ON public.jobs USING btree (status);
CREATE INDEX idx_jobs_title ON public.jobs USING btree (title);


-- public.notifications definition

-- Drop table

-- DROP TABLE public.notifications;

CREATE TABLE public.notifications (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	notification_type varchar(100) NULL,
	title varchar(255) NULL,
	message text NULL,
	is_read bool DEFAULT false NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT notifications_pkey PRIMARY KEY (id),
	CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_notifications_is_read ON public.notifications USING btree (is_read);
CREATE INDEX idx_notifications_user_id ON public.notifications USING btree (user_id);


-- public.resumes definition

-- Drop table

-- DROP TABLE public.resumes;

CREATE TABLE public.resumes (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	resume_url text NOT NULL,
	parsed_text text NULL,
	ai_keywords jsonb NULL,
	uploaded_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT resumes_pkey PRIMARY KEY (id),
	CONSTRAINT fk_resumes_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_resumes_user_id ON public.resumes USING btree (user_id);


-- public.saved_jobs definition

-- Drop table

-- DROP TABLE public.saved_jobs;

CREATE TABLE public.saved_jobs (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	job_id uuid NOT NULL,
	saved_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT saved_jobs_pkey PRIMARY KEY (id),
	CONSTRAINT fk_saved_jobs_job FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE,
	CONSTRAINT fk_saved_jobs_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uq_saved_jobs_user_job ON public.saved_jobs USING btree (user_id, job_id);


-- public.search_logs definition

-- Drop table

-- DROP TABLE public.search_logs;

CREATE TABLE public.search_logs (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NULL,
	search_keyword varchar(255) NULL,
	filters jsonb NULL,
	searched_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT search_logs_pkey PRIMARY KEY (id),
	CONSTRAINT fk_search_logs_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL
);
CREATE INDEX idx_search_logs_user_id ON public.search_logs USING btree (user_id);


-- public.user_behavior_tracking definition

-- Drop table

-- DROP TABLE public.user_behavior_tracking;

CREATE TABLE public.user_behavior_tracking (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	activity_type varchar(100) NOT NULL,
	reference_id uuid NULL,
	metadata jsonb NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT user_behavior_tracking_pkey PRIMARY KEY (id),
	CONSTRAINT fk_user_behavior_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_behavior_activity_type ON public.user_behavior_tracking USING btree (activity_type);
CREATE INDEX idx_user_behavior_user_id ON public.user_behavior_tracking USING btree (user_id);


-- public.user_education definition

-- Drop table

-- DROP TABLE public.user_education;

CREATE TABLE public.user_education (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	institution_name varchar(255) NOT NULL,
	"degree" varchar(255) NULL,
	specialization varchar(255) NULL,
	start_year int4 NULL,
	end_year int4 NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT user_education_pkey PRIMARY KEY (id),
	CONSTRAINT fk_user_education_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_education_user_id ON public.user_education USING btree (user_id);


-- public.user_experience definition

-- Drop table

-- DROP TABLE public.user_experience;

CREATE TABLE public.user_experience (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	company_name varchar(255) NOT NULL,
	designation varchar(255) NULL,
	start_date date NULL,
	end_date date NULL,
	description text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT user_experience_pkey PRIMARY KEY (id),
	CONSTRAINT fk_user_experience_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_experience_user_id ON public.user_experience USING btree (user_id);


-- public.user_job_recommendations definition

-- Drop table

-- DROP TABLE public.user_job_recommendations;

CREATE TABLE public.user_job_recommendations (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	job_id uuid NOT NULL,
	match_score numeric(5, 2) NULL,
	recommendation_reason text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT user_job_recommendations_pkey PRIMARY KEY (id),
	CONSTRAINT fk_user_job_recommendations_job FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE,
	CONSTRAINT fk_user_job_recommendations_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_job_recommendations_job_id ON public.user_job_recommendations USING btree (job_id);
CREATE INDEX idx_user_job_recommendations_user_id ON public.user_job_recommendations USING btree (user_id);


-- public.user_profiles definition

-- Drop table

-- DROP TABLE public.user_profiles;

CREATE TABLE public.user_profiles (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	headline varchar(255) NULL,
	bio text NULL,
	current_company varchar(255) NULL,
	current_position varchar(255) NULL,
	experience_years numeric(4, 1) NULL,
	current_salary numeric(12, 2) NULL,
	expected_salary numeric(12, 2) NULL,
	"location" varchar(255) NULL,
	notice_period varchar(100) NULL,
	portfolio_url text NULL,
	linkedin_url text NULL,
	github_url text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT user_profiles_pkey PRIMARY KEY (id),
	CONSTRAINT user_profiles_user_id_key UNIQUE (user_id),
	CONSTRAINT fk_user_profiles_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_profiles_user_id ON public.user_profiles USING btree (user_id);


-- public.user_skills definition

-- Drop table

-- DROP TABLE public.user_skills;

CREATE TABLE public.user_skills (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NOT NULL,
	skill_name varchar(255) NOT NULL,
	experience_years numeric(4, 1) NULL,
	skill_level varchar(50) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT user_skills_pkey PRIMARY KEY (id),
	CONSTRAINT fk_user_skills_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_skills_skill ON public.user_skills USING btree (skill_name);
CREATE INDEX idx_user_skills_user_id ON public.user_skills USING btree (user_id);


-- public.feed_comments definition

-- Drop table

-- DROP TABLE public.feed_comments;

CREATE TABLE public.feed_comments (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	post_id uuid NOT NULL,
	user_id uuid NOT NULL,
	comment_text text NOT NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT feed_comments_pkey PRIMARY KEY (id),
	CONSTRAINT fk_feed_comments_post FOREIGN KEY (post_id) REFERENCES public.feed_posts(id) ON DELETE CASCADE,
	CONSTRAINT fk_feed_comments_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);


-- public.job_applications definition

-- Drop table

-- DROP TABLE public.job_applications;

CREATE TABLE public.job_applications (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	job_id uuid NOT NULL,
	applicant_id uuid NOT NULL,
	resume_id uuid NULL,
	application_status varchar(100) DEFAULT 'APPLIED'::character varying NULL,
	ai_match_score numeric(5, 2) NULL,
	applied_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT job_applications_pkey PRIMARY KEY (id),
	CONSTRAINT fk_job_applications_job FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE,
	CONSTRAINT fk_job_applications_resume FOREIGN KEY (resume_id) REFERENCES public.resumes(id),
	CONSTRAINT fk_job_applications_user FOREIGN KEY (applicant_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_job_applications_job_id ON public.job_applications USING btree (job_id);
CREATE INDEX idx_job_applications_status ON public.job_applications USING btree (application_status);
CREATE INDEX idx_job_applications_user_id ON public.job_applications USING btree (applicant_id);


-- public.job_skills definition

-- Drop table

-- DROP TABLE public.job_skills;

CREATE TABLE public.job_skills (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	job_id uuid NOT NULL,
	skill_name varchar(255) NOT NULL,
	mandatory bool DEFAULT true NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT job_skills_pkey PRIMARY KEY (id),
	CONSTRAINT fk_job_skills_job FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE
);
CREATE INDEX idx_job_skills_job_id ON public.job_skills USING btree (job_id);
CREATE INDEX idx_job_skills_skill_name ON public.job_skills USING btree (skill_name);


-- public.job_views definition

-- Drop table

-- DROP TABLE public.job_views;

CREATE TABLE public.job_views (
	id uuid DEFAULT uuid_generate_v4() NOT NULL,
	user_id uuid NULL,
	job_id uuid NOT NULL,
	viewed_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT job_views_pkey PRIMARY KEY (id),
	CONSTRAINT fk_job_views_job FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE,
	CONSTRAINT fk_job_views_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL
);
CREATE INDEX idx_job_views_job_id ON public.job_views USING btree (job_id);
CREATE INDEX idx_job_views_user_id ON public.job_views USING btree (user_id);