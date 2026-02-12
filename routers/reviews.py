from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db_depends import get_async_db

from app.models.reviews import Review as ReviewModel
from app.schemas import ReviewCreate, ReviewSchema
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.auth import get_current_bayer, get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"] )

@router.get('/', response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Получить все отзывы.
    """
    stmt = select(ReviewModel).where(ReviewModel.is_active == True)
    result = await db.scalars(stmt)
    return result.all()
    
@router.get('/products/{product_id}/reviews/', response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_reviews_by_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Получить все отзывы о тоавре по его id
    """
    stmt1 = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    if (await db.scalar(stmt1)) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    stmt2 = select(ReviewModel).where(ReviewModel.product_id == product_id, ReviewModel.is_active == True)
    result = await db.scalars(stmt2)
    return result.all() 


@router.post('/', response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(review: ReviewCreate, 
                        current_user: UserModel = Depends(get_current_bayer), 
                        db: AsyncSession = Depends(get_async_db)
):
    """
    Создать новый отзыв.
    """
    if (await db.scalar(select(ProductModel).where(ProductModel.id == review.product_id, ProductModel.is_active == True))) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    new_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(new_review)  
    await db.commit()
    await db.refresh(new_review)
    
    # Обновляем рейтинг товара
    stmt1 = select(func.avg(ReviewModel.grade)).where(ReviewModel.product_id == review.product_id, ReviewModel.is_active == True)
    avg_rating = (await db.scalar(stmt1)) or 0.0
    stmt2 = update(ProductModel).where(ProductModel.id == review.product_id).values(rating=avg_rating)  
    await db.execute(stmt2)
    await db.commit()
    return new_review


@router.delete('/{review_id}', response_model=ReviewSchema, status_code=status.HTTP_200_OK)
async def delete_review(review_id: int, 
                        current_user: UserModel = Depends(get_current_user), 
                        db: AsyncSession = Depends(get_async_db)
):
    """
    Удалить отзыв (пометить его как неактивный).
    """
    review = (await db.scalar(select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True)))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    
    if current_user.role not in ('buyer', 'admin'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only buyers or admin can perform this action")
    
    if current_user.role == 'buyer' and current_user.id != review.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Buyers can only delete their own reviews")

    stmt = update(ReviewModel).where(ReviewModel.id == review_id).values(is_active=False)
    await db.execute(stmt)
    await db.commit()


    # Обновляем рейтинг товара
    stmt1 = select(func.avg(ReviewModel.grade)).where(ReviewModel.product_id == review.product_id, ReviewModel.is_active == True)
    avg_rating = (await db.scalar(stmt1)) or 0.0
    stmt2 = update(ProductModel).where(ProductModel.id == review.product_id).values(rating=avg_rating)  
    await db.execute(stmt2)
    await db.commit()

    return review
