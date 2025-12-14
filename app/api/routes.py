"""
api/routes.py - API Routes for LinkedIn Insights
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pymongo.database import Database
from typing import Optional, List
import math

from models.schemas import (
    PageResponse,
    PostResponse,
    EmployeeResponse,
    PaginatedResponse,
    PageWithDetails
)
from services.database_service import DatabaseService
from services.scraper_service import LinkedInScraperService

router = APIRouter()

# Global scraper instance (reused for efficiency)
scraper_instance = None


def get_db() -> Database:
    """Dependency to get database"""
    from main import app
    return app.state.get_database()


def get_scraper():
    """Get or create scraper instance"""
    global scraper_instance
    if scraper_instance is None:
        scraper_instance = LinkedInScraperService()
    return scraper_instance


@router.get("/pages/{page_id}", response_model=PageWithDetails)
def get_page_details(
    page_id: str,
    include_posts: bool = Query(True, description="Include recent posts"),
    include_employees: bool = Query(True, description="Include employees"),
    force_scrape: bool = Query(False, description="Force rescrape even if exists"),
    db: Database = Depends(get_db)
):
    """
    Get page details by page_id. 
    If page not in DB or force_scrape=True, scrapes from LinkedIn.
    """
    db_service = DatabaseService(db)
    
    # Check if page exists in DB
    page = db_service.get_page_by_id(page_id)
    
    if not page or force_scrape:
        # Scrape from LinkedIn
        print(f"Scraping page: {page_id}")
        
        scraper = get_scraper()
        
        try:
            # Login if not already logged in
            if not scraper.is_logged_in:
                if not scraper.login():
                    raise HTTPException(status_code=500, detail="Failed to login to LinkedIn")
            
            # Scrape company data
            company_data = scraper.scrape_company_page(page_id)
            
            if not company_data.get("name"):
                raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found on LinkedIn")
            
            # Save to database
            page = db_service.create_page(company_data)
            
            # Scrape posts
            posts_data = scraper.scrape_company_posts(page_id, max_posts=15)
            if posts_data:
                db_service.create_posts(posts_data)
            
            # Scrape employees
            employees_data = scraper.scrape_company_employees(page_id, max_employees=50)
            if employees_data:
                db_service.create_employees(employees_data)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Scraping error: {str(e)}")
    
    # Get additional data
    result = page.copy()
    
    if include_posts:
        posts = db_service.get_posts_by_page(page_id, limit=15)
        result["posts"] = posts
    else:
        result["posts"] = []
    
    if include_employees:
        employees, _ = db_service.get_employees_by_page(page_id, page=1, page_size=50)
        result["employees"] = employees
    else:
        result["employees"] = []
    
    # Get stats
    stats = db_service.get_page_stats(page_id)
    result["total_posts"] = stats["total_posts"]
    result["total_employees"] = stats["total_employees"]
    
    return result


@router.get("/pages", response_model=PaginatedResponse)
def search_pages(
    min_followers: Optional[int] = Query(None, description="Minimum followers count"),
    max_followers: Optional[int] = Query(None, description="Maximum followers count"),
    name: Optional[str] = Query(None, description="Search by name (partial match)"),
    industry: Optional[str] = Query(None, description="Search by industry (partial match)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Database = Depends(get_db)
):
    """
    Search and filter pages with pagination.
    Examples:
    - GET /pages?min_followers=20000&max_followers=40000
    - GET /pages?name=tech&page=1&page_size=10
    - GET /pages?industry=software
    """
    db_service = DatabaseService(db)
    
    pages, total = db_service.get_pages_with_filters(
        min_followers=min_followers,
        max_followers=max_followers,
        name=name,
        industry=industry,
        page=page,
        page_size=page_size
    )
    
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    
    return {
        "items": pages,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/pages/{page_id}/posts", response_model=List[PostResponse])
def get_page_posts(
    page_id: str,
    limit: int = Query(15, ge=1, le=50, description="Number of posts to return"),
    db: Database = Depends(get_db)
):
    """Get recent posts for a specific page"""
    db_service = DatabaseService(db)
    
    # Check if page exists
    page = db_service.get_page_by_id(page_id)
    if not page:
        raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found in database")
    
    posts = db_service.get_posts_by_page(page_id, limit=limit)
    return posts


@router.get("/pages/{page_id}/employees", response_model=PaginatedResponse)
def get_page_employees(
    page_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Database = Depends(get_db)
):
    """Get employees/followers for a specific page with pagination"""
    db_service = DatabaseService(db)
    
    # Check if page exists
    page_data = db_service.get_page_by_id(page_id)
    if not page_data:
        raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found in database")
    
    employees, total = db_service.get_employees_by_page(page_id, page=page, page_size=page_size)
    
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    
    return {
        "items": employees,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.post("/pages/{page_id}/scrape")
def scrape_page_now(
    page_id: str,
    background_tasks: BackgroundTasks,
    scrape_posts: bool = Query(True, description="Scrape posts"),
    scrape_employees: bool = Query(True, description="Scrape employees"),
    db: Database = Depends(get_db)
):
    """
    Manually trigger scraping for a specific page.
    This will update the page data in the database.
    """
    db_service = DatabaseService(db)
    scraper = get_scraper()
    
    try:
        # Login if needed
        if not scraper.is_logged_in:
            if not scraper.login():
                raise HTTPException(status_code=500, detail="Failed to login to LinkedIn")
        
        # Scrape company data
        company_data = scraper.scrape_company_page(page_id)
        
        if not company_data.get("name"):
            raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found on LinkedIn")
        
        # Save to database
        page = db_service.create_page(company_data)
        
        posts_count = 0
        employees_count = 0
        
        # Scrape posts if requested
        if scrape_posts:
            posts_data = scraper.scrape_company_posts(page_id, max_posts=15)
            if posts_data:
                posts_count = db_service.create_posts(posts_data)
        
        # Scrape employees if requested
        if scrape_employees:
            employees_data = scraper.scrape_company_employees(page_id, max_employees=50)
            if employees_data:
                employees_count = db_service.create_employees(employees_data)
        
        return {
            "message": "Scraping completed successfully",
            "page_id": page_id,
            "page_name": company_data.get("name"),
            "posts_scraped": posts_count,
            "employees_scraped": employees_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping error: {str(e)}")


@router.delete("/pages/{page_id}")
def delete_page(
    page_id: str,
    db: Database = Depends(get_db)
):
    """Delete a page and all its related data"""
    db_service = DatabaseService(db)
    
    # Check if page exists
    page = db_service.get_page_by_id(page_id)
    if not page:
        raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found")
    
    # Delete page
    db_service.pages.delete_one({"page_id": page_id})
    
    # Delete related data
    db_service.posts.delete_many({"page_id": page_id})
    db_service.employees.delete_many({"page_id": page_id})
    
    return {
        "message": f"Page '{page_id}' and all related data deleted successfully"
    }


@router.get("/stats")
def get_overall_stats(db: Database = Depends(get_db)):
    """Get overall statistics of the database"""
    db_service = DatabaseService(db)
    
    total_pages = db_service.pages.count_documents({})
    total_posts = db_service.posts.count_documents({})
    total_employees = db_service.employees.count_documents({})
    
    return {
        "total_pages": total_pages,
        "total_posts": total_posts,
        "total_employees": total_employees
    }