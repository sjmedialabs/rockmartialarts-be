"""
Optional performance-dashboard documents (additive; does not alter existing collections).

NOTE: `student_achievements` is already used for showcase/marketing achievements.
These models use separate `student_performance_*` collections.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MedalStatsUpsert(BaseModel):
    """Counters for medals / competitions / certificates (all optional partial updates)."""

    gold_medals: Optional[int] = Field(None, ge=0, le=9999)
    silver_medals: Optional[int] = Field(None, ge=0, le=9999)
    bronze_medals: Optional[int] = Field(None, ge=0, le=9999)
    competitions_participated: Optional[int] = Field(None, ge=0, le=99999)
    certificates_earned: Optional[int] = Field(None, ge=0, le=99999)


class SkillMetricsUpsert(BaseModel):
    strength: Optional[float] = Field(None, ge=0, le=100)
    speed: Optional[float] = Field(None, ge=0, le=100)
    flexibility: Optional[float] = Field(None, ge=0, le=100)
    technique: Optional[float] = Field(None, ge=0, le=100)


class GoalsUpsert(BaseModel):
    current_goal: Optional[str] = Field(None, max_length=2000)
    target_belt: Optional[str] = Field(None, max_length=200)
    progress_percentage: Optional[float] = Field(None, ge=0, le=100)

    @field_validator("current_goal", "target_belt", mode="before")
    @classmethod
    def strip_str(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return v


class CoachFeedbackUpsert(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=4000)

    @field_validator("feedback", mode="before")
    @classmethod
    def strip_feedback(cls, v):
        if not isinstance(v, str):
            raise ValueError("feedback must be a string")
        s = v.strip()
        if not s:
            raise ValueError("feedback cannot be empty")
        return s


class ProfilePerformanceUpsert(BaseModel):
    """Updates display fields on the student user document (belt / level)."""

    level_or_belt: Optional[str] = Field(None, max_length=200)
    student_level: Optional[str] = Field(None, max_length=200)

    @field_validator("level_or_belt", "student_level", mode="before")
    @classmethod
    def strip_profile_fields(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return v


class WarriorStatsUpsert(BaseModel):
    training_streak: Optional[int] = Field(None, ge=0, le=100000)
    rank: Optional[str] = Field(None, max_length=120)
    next_level_progress: Optional[float] = Field(None, ge=0, le=100)

    @field_validator("rank", mode="before")
    @classmethod
    def strip_rank(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return v
