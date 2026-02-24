"""
VOLO — Database Models & Initialization
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float,
    DateTime, JSON, ForeignKey, Enum as SQLEnum,
    create_engine,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector

from app.config import settings


# ---- Base ----

class Base(DeclarativeBase):
    pass


def generate_uuid():
    return str(uuid.uuid4())


# ---- Models ----

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(20), default="free")  # free, pro, enterprise
    branding = Column(JSON, default=dict)
    feature_flags = Column(JSON, default=dict)
    custom_domain = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)  # nullable for OAuth
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(20), default="member")  # owner, admin, member
    preferences = Column(JSON, default=dict)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")
    conversations = relationship("Conversation", back_populates="user")
    integrations = relationship("Integration", back_populates="user")
    memories = relationship("Memory", back_populates="user")
    standing_orders = relationship("StandingOrder", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), default="New Conversation")
    pinned = Column(Boolean, default=False)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # github, gmail, alpaca, etc.
    category = Column(String(30), nullable=False)  # code, communication, finance, etc.
    name = Column(String(255), nullable=False)
    status = Column(String(20), default="disconnected")
    config = Column(JSON, default=dict)  # encrypted credentials stored here
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="integrations")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    category = Column(String(30), nullable=False)  # fact, preference, relationship, project, decision, goal
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)
    confidence = Column(Float, default=1.0)
    embedding = Column(Vector(1536), nullable=True)  # for semantic search
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="memories")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    integration_id = Column(String, ForeignKey("integrations.id"), nullable=True)
    name = Column(String(255), nullable=False)
    full_name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    language = Column(String(50), nullable=True)
    tech_stack = Column(JSON, default=list)
    modules = Column(JSON, default=list)
    health_score = Column(Integer, nullable=True)
    last_analyzed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StandingOrder(Base):
    __tablename__ = "standing_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(20), nullable=False)  # cron, event, condition
    trigger_config = Column(JSON, default=dict)
    actions = Column(JSON, default=list)
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="standing_orders")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tier = Column(String(20), nullable=False)  # auto, notify, approve, approve_2fa
    action = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tool_name = Column(String(100), nullable=True)
    parameters = Column(JSON, default=dict)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, default="")
    data = Column(JSON, default=dict)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---- Engine & Session ----

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Dependency for getting a database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables and seed default data."""
    try:
        from sqlalchemy import select as sa_select

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Seed default tenant + dev user so FK constraints work
        async with async_session() as session:
            result = await session.execute(
                sa_select(Tenant).where(Tenant.id == "volo-default")
            )
            if not result.scalar_one_or_none():
                session.add(Tenant(
                    id="volo-default",
                    name="Volo",
                    slug="volo",
                    plan="pro",
                ))
                await session.flush()

            result = await session.execute(
                sa_select(User).where(User.id == "dev-user")
            )
            if not result.scalar_one_or_none():
                session.add(User(
                    id="dev-user",
                    tenant_id="volo-default",
                    email="dev@volo.ai",
                    name="Developer",
                    role="owner",
                ))

            await session.commit()

        print("✅ Database tables created & seeded")
    except Exception as e:
        print(f"⚠️  Database init: {e}")
