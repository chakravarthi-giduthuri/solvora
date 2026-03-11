from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SolutionResponse(BaseModel):
    """Solution schema with camelCase fields matching the frontend."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    problem_id: str = Field(serialization_alias="problemId")
    provider: str
    content: str = Field(serialization_alias="content")
    upvotes: int = 0
    downvotes: int = 0
    user_vote: Optional[int] = Field(None, serialization_alias="userVote")
    generated_at: datetime = Field(serialization_alias="generatedAt")
    model_version: Optional[str] = Field(None, serialization_alias="modelVersion")
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def map_fields(cls, data: Any) -> Any:
        """Map ORM attribute names to schema field names."""
        if hasattr(data, "__dict__") or hasattr(data, "_sa_instance_state"):
            obj = data
            return {
                "id": getattr(obj, "id", ""),
                "problem_id": getattr(obj, "problem_id", ""),
                "provider": getattr(obj, "provider", ""),
                "content": getattr(obj, "solution_text", ""),
                "upvotes": getattr(obj, "rating", 0) if getattr(obj, "rating", 0) > 0 else 0,
                "downvotes": 0,
                "user_vote": None,
                "generated_at": getattr(obj, "generated_at", datetime.utcnow()),
                "model_version": getattr(obj, "model_name", None),
                "is_active": getattr(obj, "is_active", True),
            }
        return data

class ProblemResponse(BaseModel):
    """Problem schema with camelCase fields matching the frontend."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    platform: str
    title: str
    body: Optional[str] = None
    source_url: str = Field(serialization_alias="sourceUrl")
    source_id: str
    author: Optional[str] = Field(None, serialization_alias="author")
    upvotes: int = 0
    comment_count: int = Field(0, serialization_alias="commentCount")
    subreddit: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None
    summary: Optional[str] = None
    is_problem: bool = Field(False, serialization_alias="isProblem")
    has_solution: bool = Field(False, serialization_alias="hasSolution")
    solution_count: int = Field(0, serialization_alias="solutionCount")
    confidence_score: Optional[float] = Field(None, serialization_alias="confidenceScore")
    is_active: bool = True
    is_bookmarked: bool = Field(False, serialization_alias="isBookmarked")
    created_at: datetime = Field(serialization_alias="createdAt")
    scraped_at: datetime = Field(serialization_alias="scrapedAt")
    solutions: List[SolutionResponse] = []

    @model_validator(mode="before")
    @classmethod
    def map_fields(cls, data: Any) -> Any:
        """Map ORM attribute names to schema field names."""
        if hasattr(data, "_sa_instance_state"):
            obj = data
            sols = getattr(obj, "solutions", []) or []
            active_sols = [s for s in sols if getattr(s, "is_active", True)]
            return {
                "id": getattr(obj, "id", ""),
                "platform": getattr(obj, "platform", ""),
                "title": getattr(obj, "title", ""),
                "body": getattr(obj, "body", None),
                "source_url": getattr(obj, "url", ""),
                "source_id": getattr(obj, "source_id", ""),
                "author": getattr(obj, "author_handle", None),
                "upvotes": getattr(obj, "upvotes", 0),
                "comment_count": getattr(obj, "comment_count", 0),
                "subreddit": getattr(obj, "subreddit", None),
                "category": getattr(obj, "category", None),
                "sentiment": getattr(obj, "sentiment", None),
                "summary": getattr(obj, "summary", None),
                "is_problem": getattr(obj, "is_problem", False),
                "has_solution": len(active_sols) > 0,
                "solution_count": len(active_sols),
                "confidence_score": getattr(obj, "confidence_score", None),
                "is_active": getattr(obj, "is_active", True),
                "is_bookmarked": False,
                "created_at": getattr(obj, "created_at", datetime.utcnow()),
                "scraped_at": getattr(obj, "scraped_at", datetime.utcnow()),
                "solutions": active_sols,
            }
        return data

class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedProblems(BaseModel):
    """Flat paginated response matching frontend PaginatedProblems type."""
    items: List[ProblemResponse]
    total: int
    page: int
    per_page: int = Field(serialization_alias="perPage")
    total_pages: int = Field(serialization_alias="totalPages")
    has_next: bool = Field(serialization_alias="hasNext")
    has_prev: bool = Field(serialization_alias="hasPrev")

class TrendingTopic(BaseModel):
    id: str
    name: str
    category: str
    count: int
    change: int
    sparklineData: List[int]


class AnalyticsSummary(BaseModel):
    by_category: dict[str, int]
    by_platform: dict[str, int]
    sentiment_distribution: dict[str, int]
    volume_over_time: List[dict[str, Any]]
    total_problems: int
    total_solutions: int
    avg_confidence: float


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    slug: str
    description: Optional[str] = None
