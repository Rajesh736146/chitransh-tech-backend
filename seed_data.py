"""
Seed script to insert dummy candidates, employers (companies), and jobs
into the database tables.

Usage: python seed_data.py
"""

import asyncio
import uuid
from datetime import datetime

from passlib.context import CryptContext
from sqlalchemy import text

from app.db.session import engine, AsyncSessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ─── Dummy Data ───────────────────────────────────────────────────────────────

# Candidates (role_id=2 for job seekers)
CANDIDATES = [
    {
        "id": str(uuid.uuid4()),
        "full_name": "Rahul Sharma",
        "email": "rahul.sharma@example.com",
        "phone": "+919876543210",
        "password_hash": hash_password("Password@123"),
        "role_id": 2,
        "preferred_category": "white_collar",
        "status": "ACTIVE",
        "email_verified": True,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Priya Patel",
        "email": "priya.patel@example.com",
        "phone": "+919876543211",
        "password_hash": hash_password("Password@123"),
        "role_id": 2,
        "preferred_category": "white_collar",
        "status": "ACTIVE",
        "email_verified": True,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Amit Kumar",
        "email": "amit.kumar@example.com",
        "phone": "+919876543212",
        "password_hash": hash_password("Password@123"),
        "role_id": 2,
        "preferred_category": "blue_collar",
        "status": "ACTIVE",
        "email_verified": True,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Sneha Gupta",
        "email": "sneha.gupta@example.com",
        "phone": "+919876543213",
        "password_hash": hash_password("Password@123"),
        "role_id": 2,
        "preferred_category": "white_collar",
        "status": "ACTIVE",
        "email_verified": True,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Vikram Singh",
        "email": "vikram.singh@example.com",
        "phone": "+919876543214",
        "password_hash": hash_password("Password@123"),
        "role_id": 2,
        "preferred_category": "blue_collar",
        "status": "ACTIVE",
        "email_verified": True,
    },
]

# Employers (role_id=3 for employers)
EMPLOYERS = [
    {
        "id": str(uuid.uuid4()),
        "full_name": "Rajesh Verma",
        "email": "rajesh@techcorp.com",
        "phone": "+919800000001",
        "password_hash": hash_password("Employer@123"),
        "role_id": 3,
        "preferred_category": "white_collar",
        "status": "ACTIVE",
        "email_verified": True,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Anita Desai",
        "email": "anita@innovatesolutions.com",
        "phone": "+919800000002",
        "password_hash": hash_password("Employer@123"),
        "role_id": 3,
        "preferred_category": "white_collar",
        "status": "ACTIVE",
        "email_verified": True,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Suresh Menon",
        "email": "suresh@buildfast.com",
        "phone": "+919800000003",
        "password_hash": hash_password("Employer@123"),
        "role_id": 3,
        "preferred_category": "blue_collar",
        "status": "ACTIVE",
        "email_verified": True,
    },
]

# Companies
COMPANIES = [
    {
        "id": str(uuid.uuid4()),
        "company_name": "TechCorp India",
        "company_description": "Leading IT services and consulting company specializing in cloud solutions, AI/ML, and enterprise software development.",
        "website": "https://techcorp.example.com",
        "logo_url": None,
        "company_size": "1000-5000",
        "industry": "Information Technology",
        "headquarters": "Bangalore, Karnataka",
    },
    {
        "id": str(uuid.uuid4()),
        "company_name": "Innovate Solutions",
        "company_description": "A fast-growing startup focused on fintech and digital payments. Building the future of financial inclusion in India.",
        "website": "https://innovatesolutions.example.com",
        "logo_url": None,
        "company_size": "50-200",
        "industry": "Fintech",
        "headquarters": "Mumbai, Maharashtra",
    },
    {
        "id": str(uuid.uuid4()),
        "company_name": "BuildFast Construction",
        "company_description": "One of India's top construction and infrastructure development companies with projects across 15 states.",
        "website": "https://buildfast.example.com",
        "logo_url": None,
        "company_size": "5000-10000",
        "industry": "Construction",
        "headquarters": "Delhi NCR",
    },
]


async def seed():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # ── Insert Candidates ─────────────────────────────────────────
            print("Inserting candidates...")
            for c in CANDIDATES:
                await session.execute(
                    text("""
                        INSERT INTO public.users (id, full_name, email, phone, password_hash, role_id, preferred_category, status, email_verified)
                        VALUES (:id, :full_name, :email, :phone, :password_hash, :role_id, :preferred_category, :status, :email_verified)
                        ON CONFLICT (email) DO NOTHING
                    """),
                    c,
                )
            print(f"  ✓ {len(CANDIDATES)} candidates inserted")

            # ── Insert Employers ──────────────────────────────────────────
            print("Inserting employers...")
            for e in EMPLOYERS:
                await session.execute(
                    text("""
                        INSERT INTO public.users (id, full_name, email, phone, password_hash, role_id, preferred_category, status, email_verified)
                        VALUES (:id, :full_name, :email, :phone, :password_hash, :role_id, :preferred_category, :status, :email_verified)
                        ON CONFLICT (email) DO NOTHING
                    """),
                    e,
                )
            print(f"  ✓ {len(EMPLOYERS)} employers inserted")

            # ── Insert Companies ──────────────────────────────────────────
            print("Inserting companies...")
            for co in COMPANIES:
                await session.execute(
                    text("""
                        INSERT INTO public.companies (id, company_name, company_description, website, logo_url, company_size, industry, headquarters)
                        VALUES (:id, :company_name, :company_description, :website, :logo_url, :company_size, :industry, :headquarters)
                        ON CONFLICT DO NOTHING
                    """),
                    co,
                )
            print(f"  ✓ {len(COMPANIES)} companies inserted")

            # ── Insert Jobs ───────────────────────────────────────────────
            print("Inserting jobs...")
            JOBS = [
                {
                    "id": str(uuid.uuid4()),
                    "company_id": COMPANIES[0]["id"],
                    "title": "Senior Python Developer",
                    "description": "We are looking for an experienced Python developer with expertise in FastAPI, SQLAlchemy, and cloud services. You will work on building scalable microservices for our enterprise clients.",
                    "employment_type": "Full-time",
                    "experience_required": "4-6 years",
                    "salary_min": 1200000,
                    "salary_max": 2000000,
                    "location": "Bangalore, Karnataka",
                    "remote_type": "Hybrid",
                    "job_category": "white_collar",
                    "status": "OPEN",
                    "posted_by": EMPLOYERS[0]["id"],
                },
                {
                    "id": str(uuid.uuid4()),
                    "company_id": COMPANIES[0]["id"],
                    "title": "React Frontend Engineer",
                    "description": "Join our frontend team to build beautiful, responsive UIs using React, TypeScript, and Next.js. Experience with state management and design systems is a plus.",
                    "employment_type": "Full-time",
                    "experience_required": "2-4 years",
                    "salary_min": 800000,
                    "salary_max": 1500000,
                    "location": "Bangalore, Karnataka",
                    "remote_type": "Remote",
                    "job_category": "white_collar",
                    "status": "OPEN",
                    "posted_by": EMPLOYERS[0]["id"],
                },
                {
                    "id": str(uuid.uuid4()),
                    "company_id": COMPANIES[1]["id"],
                    "title": "Full Stack Developer",
                    "description": "Looking for a versatile developer comfortable with both backend (Node.js/Python) and frontend (React/Vue). Fintech experience preferred. You'll help build our core payment platform.",
                    "employment_type": "Full-time",
                    "experience_required": "3-5 years",
                    "salary_min": 1000000,
                    "salary_max": 1800000,
                    "location": "Mumbai, Maharashtra",
                    "remote_type": "Hybrid",
                    "job_category": "white_collar",
                    "status": "OPEN",
                    "posted_by": EMPLOYERS[1]["id"],
                },
                {
                    "id": str(uuid.uuid4()),
                    "company_id": COMPANIES[1]["id"],
                    "title": "Data Analyst Intern",
                    "description": "6-month internship for fresh graduates. You'll work with our data team analyzing transaction patterns, building dashboards, and generating insights using Python and SQL.",
                    "employment_type": "Internship",
                    "experience_required": "Fresher",
                    "salary_min": 15000,
                    "salary_max": 25000,
                    "location": "Mumbai, Maharashtra",
                    "remote_type": "On-site",
                    "job_category": "white_collar",
                    "status": "OPEN",
                    "posted_by": EMPLOYERS[1]["id"],
                },
                {
                    "id": str(uuid.uuid4()),
                    "company_id": COMPANIES[2]["id"],
                    "title": "Site Supervisor",
                    "description": "Manage day-to-day operations at construction sites. Ensure safety compliance, coordinate with workers, and report progress to project managers. Diploma in Civil Engineering required.",
                    "employment_type": "Full-time",
                    "experience_required": "5+ years",
                    "salary_min": 400000,
                    "salary_max": 700000,
                    "location": "Delhi NCR",
                    "remote_type": "On-site",
                    "job_category": "blue_collar",
                    "status": "OPEN",
                    "posted_by": EMPLOYERS[2]["id"],
                },
                {
                    "id": str(uuid.uuid4()),
                    "company_id": COMPANIES[2]["id"],
                    "title": "Electrician",
                    "description": "Experienced electrician needed for large-scale residential and commercial projects. Must have valid license and ITI certification. Knowledge of modern wiring systems preferred.",
                    "employment_type": "Contract",
                    "experience_required": "3-5 years",
                    "salary_min": 300000,
                    "salary_max": 500000,
                    "location": "Noida, UP",
                    "remote_type": "On-site",
                    "job_category": "blue_collar",
                    "status": "OPEN",
                    "posted_by": EMPLOYERS[2]["id"],
                },
                {
                    "id": str(uuid.uuid4()),
                    "company_id": COMPANIES[0]["id"],
                    "title": "DevOps Engineer",
                    "description": "Looking for a DevOps engineer to manage CI/CD pipelines, Kubernetes clusters, and AWS infrastructure. Terraform and Docker experience is mandatory.",
                    "employment_type": "Full-time",
                    "experience_required": "3-5 years",
                    "salary_min": 1400000,
                    "salary_max": 2200000,
                    "location": "Hyderabad, Telangana",
                    "remote_type": "Remote",
                    "job_category": "white_collar",
                    "status": "OPEN",
                    "posted_by": EMPLOYERS[0]["id"],
                },
                {
                    "id": str(uuid.uuid4()),
                    "company_id": COMPANIES[2]["id"],
                    "title": "Plumber",
                    "description": "Skilled plumber required for new residential township project. Must have experience with modern plumbing systems and able to read blueprints.",
                    "employment_type": "Contract",
                    "experience_required": "2-4 years",
                    "salary_min": 250000,
                    "salary_max": 400000,
                    "location": "Gurugram, Haryana",
                    "remote_type": "On-site",
                    "job_category": "blue_collar",
                    "status": "OPEN",
                    "posted_by": EMPLOYERS[2]["id"],
                },
            ]

            for j in JOBS:
                await session.execute(
                    text("""
                        INSERT INTO public.jobs (id, company_id, title, description, employment_type, experience_required, salary_min, salary_max, location, remote_type, job_category, status, posted_by)
                        VALUES (:id, :company_id, :title, :description, :employment_type, :experience_required, :salary_min, :salary_max, :location, :remote_type, :job_category, :status, :posted_by)
                        ON CONFLICT DO NOTHING
                    """),
                    j,
                )
            print(f"  ✓ {len(JOBS)} jobs inserted")

            # ── Insert Job Skills ─────────────────────────────────────────
            print("Inserting job skills...")
            SKILLS_MAP = {
                0: [("Python", True), ("FastAPI", True), ("SQLAlchemy", True), ("AWS", False), ("Docker", False)],
                1: [("React", True), ("TypeScript", True), ("Next.js", False), ("CSS/Tailwind", True)],
                2: [("Node.js", True), ("React", True), ("PostgreSQL", True), ("REST APIs", True)],
                3: [("Python", True), ("SQL", True), ("Excel", False), ("Tableau", False)],
                4: [("Project Management", True), ("Safety Compliance", True), ("AutoCAD", False)],
                5: [("Electrical Wiring", True), ("Blueprint Reading", True), ("Safety Standards", True)],
                6: [("AWS", True), ("Kubernetes", True), ("Docker", True), ("Terraform", True), ("CI/CD", True)],
                7: [("Plumbing Systems", True), ("Blueprint Reading", True), ("PVC/CPVC Piping", True)],
            }

            for job_idx, skills in SKILLS_MAP.items():
                for skill_name, mandatory in skills:
                    await session.execute(
                        text("""
                            INSERT INTO public.job_skills (id, job_id, skill_name, mandatory)
                            VALUES (:id, :job_id, :skill_name, :mandatory)
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "job_id": JOBS[job_idx]["id"],
                            "skill_name": skill_name,
                            "mandatory": mandatory,
                        },
                    )
            total_skills = sum(len(s) for s in SKILLS_MAP.values())
            print(f"  ✓ {total_skills} job skills inserted")

        print("\n🎉 Seed data inserted successfully!")
        print(f"   - {len(CANDIDATES)} candidates (password: Password@123)")
        print(f"   - {len(EMPLOYERS)} employers (password: Employer@123)")
        print(f"   - {len(COMPANIES)} companies")
        print(f"   - {len(JOBS)} jobs")
        print(f"   - {total_skills} skills")


if __name__ == "__main__":
    asyncio.run(seed())
