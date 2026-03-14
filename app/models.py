import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # OAuth fields
    auth_provider: Mapped[str] = mapped_column(String(50), default="email")  # "email" or "google"
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workflows: Mapped[list["Workflow"]] = relationship(
        "Workflow", back_populates="owner", cascade="all, delete-orphan"
    )
    credentials: Mapped[list["Credential"]] = relationship(
        "Credential", back_populates="owner", cascade="all, delete-orphan"
    )


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Workflow")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Canvas state — stored as JSON so the frontend can persist its exact state
    nodes: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    connections: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    viewport: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=lambda: {"zoom": 1, "pan": {"x": 0, "y": 0}}
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="workflows")


class NodeTemplate(Base):
    """Catalog of available node types that users can drag onto the canvas."""
    __tablename__ = "node_templates"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # e.g. "openai"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Default config schema for the node (e.g. which fields to show)
    default_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Credential(Base):
    """Stores OAuth2 client credentials + tokens for third-party integrations."""
    __tablename__ = "credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)       # e.g. "google-docs"
    name: Mapped[str] = mapped_column(String(255), nullable=False)      # user display name
    client_id: Mapped[str] = mapped_column(Text, nullable=False)
    client_secret: Mapped[str] = mapped_column(Text, nullable=False)    # store encrypted in production
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="credentials")
