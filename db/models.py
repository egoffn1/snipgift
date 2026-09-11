from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    settings: Mapped[list["UserSettings"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    gift_name: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    backdrop: Mapped[str | None] = mapped_column(Text, nullable=True)
    pattern: Mapped[str | None] = mapped_column(Text, nullable=True)

    min_price: Mapped[float] = mapped_column(Float, default=0.0)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_profit_pct: Mapped[float] = mapped_column(Float, default=5.0)

    beautiful_id_only: Mapped[bool] = mapped_column(Boolean, default=False)

    buy_markets: Mapped[list | None] = mapped_column(JSON, default=list)
    sell_markets: Mapped[list | None] = mapped_column(JSON, default=list)
    floor_markets: Mapped[list | None] = mapped_column(JSON, default=list)

    auctions_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    max_auction_bid: Mapped[float | None] = mapped_column(Float, nullable=True)

    scan_interval: Mapped[int] = mapped_column(Integer, default=7)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    paused: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="settings")


class ListingSeen(Base):
    __tablename__ = "listings_seen"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    listing_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    market: Mapped[str] = mapped_column(String, index=True)
    gift_name: Mapped[str] = mapped_column(String, default="")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AlertsHistory(Base):
    __tablename__ = "alerts_history"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    listing_id: Mapped[str] = mapped_column(String, index=True)
    profit_pct: Mapped[float] = mapped_column(Float, default=0.0)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
