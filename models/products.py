from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey, text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship  
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)  
    category: Mapped["Category"] = relationship("Category", back_populates="products")  
    
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False) 
    seller: Mapped["User"] = relationship("User", back_populates="products")  

    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=0.0, server_default=text('0'))  # New
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="product")