"""
models/schemas.py - Pydantic Models for Request/Response
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PageBase(BaseModel):
    page_id: str
    name: Optional[str] = None
    url: Optional[str] = None
    profile_image_url: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    followers_count: Optional[int] = 0
    headcount: Optional[str] = None
    location: Optional[str] = None
    founded_year: Optional[int] = None
    specialities: Optional[List[str]] = []


class PageResponse(PageBase):
    id: str = Field(alias="_id")
    scraped_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "page_id": "deepsolv",
                "name": "DeepSolv",
                "followers_count": 35420,
                "industry": "Software Development"
            }
        }


class PostBase(BaseModel):
    page_id: str
    linkedin_post_id: str
    content: Optional[str] = None
    permalink: Optional[str] = None
    posted_at: Optional[str] = None
    likes_count: Optional[int] = 0
    comments_count: Optional[int] = 0


class PostResponse(PostBase):
    id: str = Field(alias="_id")
    
    class Config:
        populate_by_name = True


class CommentBase(BaseModel):
    post_id: str
    author_name: Optional[str] = None
    text: Optional[str] = None
    created_at: Optional[str] = None


class CommentResponse(CommentBase):
    id: str = Field(alias="_id")
    
    class Config:
        populate_by_name = True


class EmployeeBase(BaseModel):
    page_id: str
    full_name: str
    profile_url: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    type: str = "EMPLOYEE"


class EmployeeResponse(EmployeeBase):
    id: str = Field(alias="_id")
    
    class Config:
        populate_by_name = True


class PageWithDetails(PageResponse):
    posts: List[PostResponse] = []
    employees: List[EmployeeResponse] = []
    total_posts: int = 0
    total_employees: int = 0


class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class PageFilterRequest(BaseModel):
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    name: Optional[str] = None
    industry: Optional[str] = None
    page: int = 1
    page_size: int = 10