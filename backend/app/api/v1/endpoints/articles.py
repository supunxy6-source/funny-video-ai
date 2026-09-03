"""Articles endpoints — browse collected news articles."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.article import NewsArticle
from app.schemas import ArticleResponse, ArticleListResponse

router = APIRouter()


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str = Query(None),
    verified: bool = Query(None),
    cluster_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List news articles with filtering."""
    query = select(NewsArticle)
    count_query = select(func.count(NewsArticle.id))

    if category:
        query = query.where(NewsArticle.category == category)
        count_query = count_query.where(NewsArticle.category == category)
    if verified is not None:
        query = query.where(NewsArticle.is_verified == verified)
        count_query = count_query.where(NewsArticle.is_verified == verified)
    if cluster_id is not None:
        query = query.where(NewsArticle.cluster_id == cluster_id)
        count_query = count_query.where(NewsArticle.cluster_id == cluster_id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(desc(NewsArticle.published_at))
        .offset((page - 1) * page_size).limit(page_size)
    )

    return ArticleListResponse(
        items=[ArticleResponse.model_validate(a) for a in result.scalars().all()],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Get a specific article."""
    article = await db.get(NewsArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleResponse.model_validate(article)
