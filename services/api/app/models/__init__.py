from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey as FK, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

LIFECYCLE = (
    "operational", "still_travelling", "mission_completed_hardware_left",
    "decommissioned_dormant", "lost_contact_failed", "crashed_impacted", "unknown_unverified",
)
LEVELS = ("explorer", "investigator", "scientist")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user")  # user|reviewer|admin
    preferences: Mapped["UserPreference"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(FK("users.id", ondelete="CASCADE"), unique=True)
    level: Mapped[str] = mapped_column(String(20), default="explorer")
    reduced_motion: Mapped[bool] = mapped_column(Boolean, default=False)
    leaderboard_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship(back_populates="preferences")


class Agency(Base):
    __tablename__ = "agencies"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))


class CelestialObject(Base, TimestampMixin):
    __tablename__ = "celestial_objects"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(30), index=True)  # star|planet|moon|asteroid|comet
    parent_id: Mapped[int | None] = mapped_column(FK("celestial_objects.id"))
    mean_radius_km: Mapped[float | None] = mapped_column(Float)
    semi_major_axis_km: Mapped[float | None] = mapped_column(Float)
    orbital_period_days: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(FK("data_sources.id"))


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))


class LearningPath(Base):
    __tablename__ = "learning_paths"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(20))


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[int | None] = mapped_column(FK("learning_paths.id"))
    topic_id: Mapped[int | None] = mapped_column(FK("topics.id"))
    title: Mapped[str] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(20))
    objectives: Mapped[list] = mapped_column(JSON, default=list)


class Lesson(Base, TimestampMixin):
    __tablename__ = "lessons"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(FK("courses.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200))
    body_md: Mapped[str | None] = mapped_column(Text)
    mission_id: Mapped[int | None] = mapped_column(FK("missions.id"))


class Quiz(Base):
    __tablename__ = "quizzes"
    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(FK("lessons.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(FK("quizzes.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON)
    correct_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str | None] = mapped_column(Text)


class QuizAttempt(Base, TimestampMixin):
    __tablename__ = "quiz_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(FK("users.id", ondelete="CASCADE"), index=True)
    quiz_id: Mapped[int] = mapped_column(FK("quizzes.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float)


class UserProgress(Base, TimestampMixin):
    __tablename__ = "user_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(FK("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(FK("lessons.id", ondelete="CASCADE"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)


class UserAchievement(Base, TimestampMixin):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(FK("users.id", ondelete="CASCADE"), index=True)
    achievement_id: Mapped[int] = mapped_column(FK("achievements.id"))


class Challenge(Base):
    __tablename__ = "challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    cadence: Mapped[str] = mapped_column(String(20))  # daily|weekly
    title: Mapped[str] = mapped_column(String(200))
    xp_reward: Mapped[int] = mapped_column(Integer, default=0)
    spec: Mapped[dict] = mapped_column(JSON, default=dict)


class Simulation(Base):
    __tablename__ = "simulations"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    disclaimer: Mapped[str] = mapped_column(Text, default="Educational approximation, not a flight-certified engineering tool.")


class AIConversation(Base, TimestampMixin):
    __tablename__ = "ai_conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(FK("users.id", ondelete="CASCADE"), index=True)
    level: Mapped[str] = mapped_column(String(20), default="explorer")
    messages: Mapped[list] = mapped_column(JSON, default=list)


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(FK("data_sources.id"))
    title: Mapped[str] = mapped_column(String(300))
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(FK("knowledge_documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(JSON().with_variant(Vector(384), "postgresql"), nullable=True)
    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


class Bookmark(Base, TimestampMixin):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(FK("users.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int] = mapped_column(Integer)


from app.models.archive import Artifact, ArtifactImage, ArtifactLocation, ArtifactSource, Mission, MissionEvent, MissionSource  # noqa: E402,F401
from app.models.nasa import CatalogueRecord, DataSource, IngestionJob, VerificationEvent  # noqa: E402,F401
