"""Business logic for generic ATS resume builder."""

import uuid
import json
import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)


SUMMARY_PROMPT = """You are a professional resume writer who writes like a real human, not an AI.

Write a professional summary for someone applying for: {target_role}

Rules:
- Sound like a confident, real person wrote this — not a robot
- 3-4 sentences max, tight and punchy
- Avoid these overused AI phrases: "results-driven", "dynamic", "passionate", "leveraged", "spearheaded", "fostering", "utilizing", "synergy", "proactive", "detail-oriented"
- Use simple, direct language with strong verbs
- Mention specific skills and domain relevant to {target_role}
- End with what the person is looking to do next
- ATS-optimized with 8-10 natural keywords

Return ONLY valid JSON:
{{
  "summary": "3-4 sentence human-sounding summary",
  "keywords": ["keyword1", "keyword2"]
}}"""


SKILLS_PROMPT = """You are a professional resume writer and ATS optimization expert.

Organize and enhance the following skills for someone applying as: {target_role}

Requirements:
- Keep the user's skill categories but enhance and expand them
- Add commonly expected skills for {target_role} that align with the user's background
- Prioritize skills most relevant to {target_role}
- Include 10-15 ATS keywords

Return ONLY valid JSON:
{{
  "skills": [
    {{"category": "category name", "items": ["skill1", "skill2"]}}
  ],
  "keywords": ["keyword1", "keyword2"]
}}"""


PROJECT_PROMPT = """You are a resume writer who writes like a real human, not an AI.

Enhance this project for someone applying as: {target_role}

Rules:
- Write 3-5 bullet points that sound like a real person describing their work
- Start each bullet with a clear action verb (Built, Designed, Created, Developed, Shipped, Fixed, Improved, Integrated, Automated, Reduced)
- Be specific — mention actual tools, numbers, and outcomes
- Avoid AI filler phrases: "leveraged", "utilized", "spearheaded", "fostering", "robust", "seamless", "cutting-edge"
- Keep bullets concise — one clear idea per bullet, max 20 words
- Quantify impact where possible (e.g. "cut load time by 40%", "handled 10k daily users")

Return ONLY valid JSON:
{{
  "title": "project title",
  "bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "keywords": ["keyword1", "keyword2"]
}}"""


EXPERIENCE_PROMPT = """You are a resume writer who writes like a real human, not an AI.

Enhance this work experience for someone applying as: {target_role}

Rules:
- Write 4-6 bullet points that sound natural and confident — like the person is telling you what they did
- Start each bullet with a strong past-tense verb (Built, Ran, Managed, Grew, Cut, Improved, Launched, Handled, Wrote, Designed, Led, Shipped)
- Be specific — real numbers, real tools, real outcomes
- Avoid these AI phrases: "leveraged", "utilized", "spearheaded", "fostering collaboration", "cross-functional synergy", "proactively", "robust", "streamlined operations"
- Keep it tight — no fluff, no filler, no long winding sentences
- Quantify wherever possible (%, $, time saved, team size, user count)
- IMPORTANT: Copy start_date and end_date exactly from the input. Calculate duration.

Return ONLY valid JSON:
{{
  "company": "company name",
  "role": "job title",
  "start_date": "copied from input",
  "end_date": "copied from input",
  "duration": "e.g. Jun 2021 – Jul 2022 (1 yr 1 mo)",
  "bullets": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"],
  "keywords": ["keyword1", "keyword2"]
}}"""


async def _call_llm(prompt: str, data: dict[str, Any], retries: int = 3) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OpenAI API key not configured")

    client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    for attempt in range(retries):
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
                ],
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            logger.info("LLM response received (%d chars)", len(raw))
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("Attempt %d: malformed JSON: %s", attempt + 1, e)
            if attempt == retries - 1:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI returned invalid JSON")
        except Exception as e:
            logger.error("LLM error: %s", e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI service error: {str(e)}")


class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_resume(self, user_id: Any, payload: Any) -> dict[str, Any]:
        raw = payload.model_dump()
        target_role = payload.target_role
        ai: dict[str, Any] = {}

        # Summary
        ai["summary"] = await _call_llm(
            SUMMARY_PROMPT.format(target_role=target_role),
            {"personal_details": raw["personal_details"], "target_role": target_role},
        )

        # Skills
        if payload.skills:
            ai["skills"] = await _call_llm(
                SKILLS_PROMPT.format(target_role=target_role),
                {"skills": raw["skills"], "target_role": target_role},
            )

        # Projects — section-wise
        ai["projects"] = []
        for project in payload.projects:
            enhanced = await _call_llm(
                PROJECT_PROMPT.format(target_role=target_role),
                {**project.model_dump(), "target_role": target_role},
            )
            ai["projects"].append(enhanced)

        # Work experience — section-wise
        ai["work_experience"] = []
        for exp in payload.work_experience:
            enhanced = await _call_llm(
                EXPERIENCE_PROMPT.format(target_role=target_role),
                {**exp.model_dump(), "target_role": target_role},
            )
            # always enforce dates from input regardless of LLM output
            enhanced["start_date"] = exp.start_date
            enhanced["end_date"] = exp.end_date
            if not enhanced.get("duration") and exp.start_date and exp.end_date:
                enhanced["duration"] = f"{exp.start_date} – {exp.end_date}"
            ai["work_experience"].append(enhanced)

        return {
            "title": payload.title,
            "target_role": target_role,
            "personal_details": raw["personal_details"],
            "education": raw["education"],
            "certifications": raw["certifications"],
            "extra_sections": raw["extra_sections"],
            "ai_enhanced": ai,
        }
