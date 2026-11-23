from typing import Annotated, Literal

from pydantic import BaseModel, Field, Json, StringConstraints

from app.extraction.schema import CV


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Category = Literal["education", "experience", "skills"]
Score = Annotated[float, Field(ge=0, le=10)]


class SavedCV(BaseModel):
    file_name: Text
    # The API returns an object. A caller reading a stored JSON cell can also send its text.
    extracted_data: CV | Json[CV]


class RankingRequest(BaseModel):
    job_description: Text
    cvs: list[SavedCV] = Field(min_length=1)


class Requirement(BaseModel):
    text: Text
    category: Category
    priority: Literal["required", "preferred"]


class JobChecklist(BaseModel):
    entry_level_quote: Text | None
    requirements: list[Requirement]


class NumberedRequirement(Requirement):
    id: int


class Match(BaseModel):
    requirement_id: int = Field(ge=1)
    status: Literal["supported", "partial", "no_evidence"]
    evidence: list[str] = Field(description="Paths to the supporting fields in extracted_data.")


class Matches(BaseModel):
    matches: list[Match]


class RankedCV(BaseModel):
    file_name: str
    extracted_data: CV
    education_score: Score
    experience_score: Score
    skills_score: Score
    overall_score: Score
    matches: list[Match]
    required_to_review: list[int] = Field(description="IDs of required items with partial or missing evidence.")


class RankingResponse(BaseModel):
    job_description: str
    weights: dict[Category, float] = Field(description="Category shares of the overall score, from 0 to 1.")
    requirements: list[NumberedRequirement]
    ranked_cvs: list[RankedCV]
