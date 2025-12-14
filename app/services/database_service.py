"""
services/database_service.py - Database Service for MongoDB operations using pymongo
"""
from pymongo.database import Database
from typing import List, Optional, Dict
from bson import ObjectId
from datetime import datetime
import math


class DatabaseService:
    def __init__(self, db: Database):
        self.db = db
        self.pages = db.pages
        self.posts = db.posts
        self.employees = db.employees
        self.comments = db.comments
    def get_page_by_id(self, page_id: str) -> Optional[Dict]:
        """Get page by page_id"""
        page = self.pages.find_one({"page_id": page_id})
        if page:
            page["_id"] = str(page["_id"])
        return page
    def create_page(self, page_data: Dict) -> Dict:
        """Create or update page"""
        page_data["scraped_at"] = datetime.utcnow()
        
        # Check if page exists
        existing = self.pages.find_one({"page_id": page_data["page_id"]})
        
        if existing:
            # Update existing
            self.pages.update_one(
                {"page_id": page_data["page_id"]},
                {"$set": page_data}
            )
            page_data["_id"] = str(existing["_id"])
        else:
            # Insert new
            result = self.pages.insert_one(page_data)
            page_data["_id"] = str(result.inserted_id)
        
        return page_data
    
    def get_pages_with_filters(
        self,
        min_followers: Optional[int] = None,
        max_followers: Optional[int] = None,
        name: Optional[str] = None,
        industry: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Dict], int]:
        """Get pages with filters and pagination"""
        query = {}
        
        if min_followers is not None or max_followers is not None:
            query["followers_count"] = {}
            if min_followers is not None:
                query["followers_count"]["$gte"] = min_followers
            if max_followers is not None:
                query["followers_count"]["$lte"] = max_followers
        
        if name:
            query["name"] = {"$regex": name, "$options": "i"}
        
        if industry:
            query["industry"] = {"$regex": industry, "$options": "i"}
        
        # Count total
        total = self.pages.count_documents(query)
        
        # Get paginated results
        skip = (page - 1) * page_size
        pages = list(self.pages.find(query).skip(skip).limit(page_size))
        
        # Convert ObjectId to string
        for p in pages:
            p["_id"] = str(p["_id"])
        
        return pages, total
    
    # Post operations
    def create_posts(self, posts: List[Dict]) -> int:
        """Create posts for a page"""
        if not posts:
            return 0
        
        inserted_count = 0
        for post in posts:
            try:
                # Check if post exists
                existing = self.posts.find_one({"linkedin_post_id": post["linkedin_post_id"]})
                
                if existing:
                    # Update
                    self.posts.update_one(
                        {"linkedin_post_id": post["linkedin_post_id"]},
                        {"$set": post}
                    )
                else:
                    # Insert
                    self.posts.insert_one(post)
                    inserted_count += 1
            except Exception as e:
                print(f"Error inserting post: {e}")
                continue
        
        return inserted_count
    
    def get_posts_by_page(self, page_id: str, limit: int = 15) -> List[Dict]:
        """Get posts for a page"""
        posts = list(self.posts.find({"page_id": page_id}).sort("posted_at", -1).limit(limit))
        
        for post in posts:
            post["_id"] = str(post["_id"])
        
        return posts
    
    # Employee operations
    def create_employees(self, employees: List[Dict]) -> int:
        """Create employees for a page"""
        if not employees:
            return 0
        
        # Delete existing employees for this page
        page_id = employees[0].get("page_id")
        if page_id:
            self.employees.delete_many({"page_id": page_id})
        
        # Insert new employees
        result = self.employees.insert_many(employees)
        return len(result.inserted_ids)
    
    def get_employees_by_page(
        self,
        page_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Dict], int]:
        """Get employees for a page with pagination"""
        query = {"page_id": page_id}
        
        total = self.employees.count_documents(query)
        
        skip = (page - 1) * page_size
        employees = list(self.employees.find(query).skip(skip).limit(page_size))
        
        for emp in employees:
            emp["_id"] = str(emp["_id"])
        
        return employees, total
    
    # Comment operations
    def create_comments(self, post_id: str, comments: List[Dict]) -> int:
        """Create comments for a post"""
        if not comments:
            return 0
        
        # Add post_id to each comment
        for comment in comments:
            comment["post_id"] = post_id
        
        # Delete existing comments
        self.comments.delete_many({"post_id": post_id})
        
        # Insert new comments
        result = self.comments.insert_many(comments)
        return len(result.inserted_ids)
    
    def get_comments_by_post(self, post_id: str) -> List[Dict]:
        """Get comments for a post"""
        comments = list(self.comments.find({"post_id": post_id}))
        
        for comment in comments:
            comment["_id"] = str(comment["_id"])
        
        return comments
    
    # Statistics
    def get_page_stats(self, page_id: str) -> Dict:
        """Get statistics for a page"""
        posts_count = self.posts.count_documents({"page_id": page_id})
        employees_count = self.employees.count_documents({"page_id": page_id})
        
        return {
            "total_posts": posts_count,
            "total_employees": employees_count
        }