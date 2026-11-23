from datetime import date

from app.extraction.runtime import model_session
from .matcher import match_cv, normalized, read_job
from .schema import (
    Category,
    JobChecklist,
    Match,
    NumberedRequirement,
    RankedCV,
    RankingRequest,
    RankingResponse,
    Requirement,
    SavedCV,
)


class NoJobRequirements(ValueError):
    pass


def _requirements(job: JobChecklist) -> list[NumberedRequirement]:
    # A qualification repeated in two sections of the posting earns points only once.
    unique: dict[str, Requirement] = {}
    for item in job.requirements:
        key = normalized(item.text)
        if key not in unique or item.priority == "required":
            unique[key] = item
    if not unique:
        raise NoJobRequirements(
            "The job description needs at least one education, experience, or skills requirement."
        )
    return [NumberedRequirement(id=i, **item.model_dump()) for i, item in enumerate(unique.values(), start=1)]


def _weights(requirements: list[NumberedRequirement], entry_level: bool) -> dict[Category, float]:
    base: dict[Category, int] = {
        "education": 10,
        "experience": 30 if entry_level else 50,
        "skills": 60 if entry_level else 40,
    }
    active = {item.category for item in requirements}
    total = sum(base[category] for category in active)
    return {category: weight / total if category in active else 0.0 for category, weight in base.items()}


def _score(
    cv: SavedCV,
    requirements: list[NumberedRequirement],
    matches: list[Match],
    weights: dict[Category, float],
) -> RankedCV:
    possible = dict.fromkeys(weights, 0)
    earned = dict.fromkeys(weights, 0.0)
    credit = {"supported": 1, "partial": 0.5, "no_evidence": 0}
    to_review = []
    for item, match in zip(requirements, matches, strict=True):
        points = 2 if item.priority == "required" else 1
        possible[item.category] += points
        earned[item.category] += points * credit[match.status]
        if item.priority == "required" and match.status != "supported":
            to_review.append(item.id)

    # Each category is out of ten. An unused category has zero points and zero weight.
    scores = {
        key: 10 * earned[key] / maximum if maximum else 0.0
        for key, maximum in possible.items()
    }
    overall = sum(scores[key] * weight for key, weight in weights.items())
    return RankedCV(
        file_name=cv.file_name,
        extracted_data=cv.extracted_data,
        education_score=round(scores["education"], 2),
        experience_score=round(scores["experience"], 2),
        skills_score=round(scores["skills"], 2),
        overall_score=round(overall, 2),
        matches=matches,
        required_to_review=to_review,
    )


def rank_batch(request: RankingRequest) -> RankingResponse:
    # Keep one CPU model session for the whole batch and use the same checklist for every CV.
    as_of = date.today().isoformat()
    with model_session() as client:
        job = read_job(client, request.job_description)
        requirements = _requirements(job)
        weights = _weights(requirements, entry_level=bool(job.entry_level_quote))
        ranked = []
        for cv in request.cvs:
            try:
                matches = match_cv(client, requirements, cv.extracted_data, as_of)
            except ValueError as error:
                raise ValueError(f"{cv.file_name}: {error}") from error
            ranked.append(_score(cv, requirements, matches, weights))

    # Python's stable sort preserves upload order when two CVs receive the same overall score.
    ranked.sort(key=lambda cv: cv.overall_score, reverse=True)
    return RankingResponse(
        job_description=request.job_description,
        weights=weights,
        requirements=requirements,
        ranked_cvs=ranked,
    )
