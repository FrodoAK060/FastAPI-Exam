from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi.security import OAuth2PasswordRequestForm

from app.models.users import User as UserModel
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel
from app.models.categories import Category as CategoryModel

from app.schemas import UserCreate, User as UserSchema,  RefreshTokenRequest
from app.db_depends import get_async_db
from app.auth import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user

from app.config import SECRET_KEY, ALGORITHM
import jwt


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Регистрирует нового пользователя с ролью 'buyer' или 'seller'.
    """
    # Проверка уникальности email
    result = await db.scalars(select(UserModel).where(UserModel.email == user.email))
    if result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email already registered")

    # Создание объекта пользователя с хешированным паролем
    db_user = UserModel(
        email=user.email,
        hashed_password=hash_password(user.password),
        role=user.role
    )

    # Добавление в сессию и сохранение в базе
    db.add(db_user)
    await db.commit()
    return db_user


@router.post("/token")                                                                # New
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    """
    Аутентифицирует пользователя и возвращает access_token и refresh_token.
    """
    result = await db.scalars(
        select(UserModel).where(UserModel.email == form_data.username, UserModel.is_active == True))
    user = result.first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email, "role": user.role, "id": user.id})
    refresh_token = create_refresh_token(data={"sub": user.email, "role": user.role, "id": user.id})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get("/", response_model=list[UserSchema])
async def get_all_users(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех пользователей.
    """
    result = await db.scalars(select(UserModel))
    return result.all()

@router.put("/{user_id}", response_model=UserSchema)
async def update_user(user_id: int, user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Меняет данные пользователя по его ID.
    """
    result = await db.scalars(select(UserModel).where(UserModel.id == user_id))
    db_user = result.first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.execute(update(UserModel).where(UserModel.id == user_id).values(email=user.email,
                                                                             hashed_password=hash_password(user.password),
                                                                             role=user.role))
    await db.commit()
    await db.refresh(db_user) 
    return db_user


@router.post("/refresh-token")
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Обновляет refresh-токен, принимая старый refresh-токен в теле запроса.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    old_refresh_token = body.refresh_token

    try:
        payload = jwt.decode(old_refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")

        # Проверяем, что токен действительно refresh
        if email is None or token_type != "refresh":
            raise credentials_exception

    except jwt.ExpiredSignatureError:
        # refresh-токен истёк
        raise credentials_exception
    except jwt.PyJWTError:
        # подпись неверна или токен повреждён
        raise credentials_exception

    # Проверяем, что пользователь существует и активен
    result = await db.scalars(
        select(UserModel).where(
            UserModel.email == email,
            UserModel.is_active == True
        )
    )
    user = result.first()
    if user is None:
        raise credentials_exception

    # Генерируем новый refresh-токен
    new_refresh_token = create_refresh_token(
        data={"sub": user.email, "role": user.role, "id": user.id}
    )

    return {
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/accsess-token")
async def get_new_access_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db),
):
    refresh_token = body.refresh_token

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user_id = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        result = await db.scalars(select(UserModel).where(UserModel.id == user_id, UserModel.is_active == True))
        user = result.first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        new_access_token = create_access_token(data={"sub": user.email, "role": user.role, "id": user.id})
        return {"access_token": new_access_token, "token_type": "bearer"}
    
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: int, 
                      current_user = Depends(get_current_user), 
                      db: AsyncSession = Depends(get_async_db)
) -> dict:
    """
    Удаляет пользователя (помечает его как неактивного).
    """
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    result = await db.scalars(select(UserModel).where(UserModel.id == user_id))
    user = result.first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.execute(update(UserModel).where(UserModel.id == user_id).values(is_active=False))

    # Deactivate user's products, reviews and categories based on their role
    if user.role == "seller":
        await db.execute(update(ProductModel).where(ProductModel.seller_id == user_id).values(is_active=False))  
    if user.role == "buyer":
        await db.execute(update(ReviewModel).where(ReviewModel.user_id == user_id).values(is_active=False))
    if user.role == "admin":
        await db.execute(update(CategoryModel).where(CategoryModel.admin_id == user_id).values(is_active=False))
    
    await db.commit()
    await db.refresh(user)
    return user    
