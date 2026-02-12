from pydantic import BaseModel, Field, ConfigDict, EmailStr
from decimal import Decimal
from datetime import datetime

class CategoryCreate(BaseModel):
    """
    Модель для создания и обновления категории.
    Используется в POST и PUT запросах.
    """
    name: str = Field(..., min_length=3, max_length=50, description="Название категории (3-50 символов)")
    parent_id: int | None = Field(None, description="ID родительской категории, если есть")
    admin_id: int = Field(..., description="ID администратора, ответственного за категорию")


class Category(BaseModel):
    """
    Модель для ответа с данными категории.
    Используется в GET-запросах.
    """
    id: int = Field(..., description="Уникальный идентификатор категории")
    name: str = Field(..., description="Название категории")
    parent_id: int | None = Field(None, description="ID родительской категории, если есть")
    is_active: bool = Field(..., description="Активность категории")
    admin_id: int = Field(..., description="ID администратора, ответственного за категорию")    

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """
    Модель для создания и обновления товара.
    Используется в POST и PUT запросах.
    """
    name: str = Field(..., min_length=3, max_length=100, description="Название товара (3-100 символов)")
    description: str | None = Field(None, max_length=500, description="Описание товара (до 500 символов)")
    price: Decimal = Field(..., gt=0, description="Цена товара (больше 0)", decimal_places=2)
    image_url: str | None = Field(None, max_length=200, description="URL изображения товара")
    stock: int = Field(..., ge=0, description="Количество товара на складе (0 или больше)")
    category_id: int = Field(..., description="ID категории, к которой относится товар")


class Product(BaseModel):
    """
    Модель для ответа с данными товара.
    Используется в GET-запросах.
    """
    id: int = Field(..., description="Уникальный идентификатор товара")
    name: str = Field(..., description="Название товара")
    description: str | None = Field(None, description="Описание товара")
    price: Decimal = Field(..., description="Цена товара в рублях", gt=0, decimal_places=2)
    image_url: str | None = Field(None, description="URL изображения товара")
    stock: int = Field(..., description="Количество товара на складе")
    category_id: int = Field(..., description="ID категории")
    is_active: bool = Field(..., description="Активность товара")
    rating: float = Field(..., description="Средний рейтинг товара от 0 до 5", ge=0, le=5)

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr = Field(description="Email пользователя")
    password: str = Field(min_length=8, description="Пароль (минимум 8 символов)")
    role: str = Field(default="buyer", pattern="^(buyer|seller|admin)$", description="Роль: 'buyer', 'seller' или 'admin'")


class User(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    role: str
    model_config = ConfigDict(from_attributes=True)    


class RefreshTokenRequest(BaseModel):
    refresh_token: str    

class ReviewCreate(BaseModel):
    product_id: int = Field(..., description='ID товара, к которому относится отзыв')
    grade: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5")
    comment: str | None = Field(None, description="Комментарий к товару")

class ReviewSchema(BaseModel):
    id: int = Field(..., description='Уникальный идентификатор отзыва')
    user_id: int = Field(..., description='ID пользователя, который оставил отзыв')
    product_id: int = Field(..., description='ID товара, к которому относится отзыв') 
    comment: str | None = Field(None, description="Комментарий к товару")
    comment_date: datetime = Field(..., description="Дата и время оставления отзыва")
    grade: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5")    
    is_active: bool = Field(..., description="Активность отзыва")
    
    model_config = ConfigDict(from_attributes=True) 


class ProductList(BaseModel):
    """
    Список пагинации для товаров.
    """
    items: list[Product] = Field(description="Товары для текущей страницы")
    total: int = Field(ge=0, description="Общее количество товаров")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, description="Количество элементов на странице")
    
    model_config = ConfigDict(from_attributes=True)  # Для чтения из ORM-объектов