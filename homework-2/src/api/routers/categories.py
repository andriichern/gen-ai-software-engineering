"""Category management API: view and extend the keyword-classification categories."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import CategoryCreate, CategoryKeywords, CategoryKeywordsUpdate
from ..services.category_registry import CategoryNotFoundError, category_registry

router = APIRouter(prefix="/category", tags=["categories"])


@router.get("/list", response_model=list[CategoryKeywords])
def list_categories():
    return [
        CategoryKeywords(category=key, keywords=keywords)
        for key, keywords in category_registry.list_all().items()
    ]


@router.get("/{key}", response_model=CategoryKeywords)
def get_category(key: str):
    try:
        keywords = category_registry.get(key)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CategoryKeywords(category=key, keywords=keywords)


@router.post("", response_model=CategoryKeywords, status_code=201)
def create_category(payload: CategoryCreate):
    keywords = category_registry.create(payload.key, payload.keywords)
    return CategoryKeywords(category=payload.key, keywords=keywords)


@router.put("/{key}", response_model=CategoryKeywords)
def update_category(key: str, payload: CategoryKeywordsUpdate):
    try:
        keywords = category_registry.add_keywords(key, payload.keywords)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CategoryKeywords(category=key, keywords=keywords)
