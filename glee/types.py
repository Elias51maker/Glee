"""Type definitions for Glee."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class ReviewStatus(StrEnum):
    """Status of a review session."""

    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class ReviewSession:
    """Represents a review session."""

    review_id: str
    files: list[str]
    project_path: str
    status: ReviewStatus = ReviewStatus.IN_PROGRESS
    iteration: int = 0
    max_iterations: int = 10
    feedback: Optional[str] = None
