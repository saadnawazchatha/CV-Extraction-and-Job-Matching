from fastapi import FastAPI, UploadFile
from pydantic import BaseModel, Field

from .cv_parser import parse_cv
from .cv_ranking import rank_cvs
from .extraction.schema import CV
from .information_extraction import extract_information
from .ranking.schema import RankedCV, RankingRequest, RankingResponse, Score

app = FastAPI(title="CV extraction service", docs_url=None, redoc_url=None)


class RawText(BaseModel):
    file_name: str = Field(pattern=r"\S")
    raw_text: str = Field(pattern=r"\S")


class ExtractedInformation(BaseModel):
    file_name: str
    extracted_data: CV


class RankedScores(BaseModel):
    rank: int
    file_name: str
    education_score: Score
    experience_score: Score
    skills_score: Score
    overall_score: Score


class ScoreReport(BaseModel):
    job_description: str
    ranked_cvs: list[RankedScores]


class RankedDetails(RankedCV):
    rank: int


class DetailedReport(RankingResponse):
    ranked_cvs: list[RankedDetails]


@app.post("/cv/raw")
def read_cv(file: UploadFile) -> RawText:
    file_name, raw_text = parse_cv(file)
    return RawText(file_name=file_name, raw_text=raw_text)


@app.post("/cv/extract")
def extract_cv(request: RawText) -> ExtractedInformation:
    fields = extract_information(request.file_name, request.raw_text)
    return ExtractedInformation(file_name=request.file_name, extracted_data=fields)


@app.post("/cv/rank")
def rank_cv_batch(request: RankingRequest, include_details: bool = False) -> DetailedReport | ScoreReport:
    result = rank_cvs(request)
    # The existing ranker already sorts by overall score and preserves submission order for ties.
    if include_details:
        rows = [RankedDetails(rank=i, **cv.model_dump()) for i, cv in enumerate(result.ranked_cvs, 1)]
        return DetailedReport(
            job_description=result.job_description, weights=result.weights,
            requirements=result.requirements, ranked_cvs=rows,
        )
    return ScoreReport(
        job_description=result.job_description,
        ranked_cvs=[
            RankedScores(
                rank=i, file_name=cv.file_name, education_score=cv.education_score,
                experience_score=cv.experience_score, skills_score=cv.skills_score, overall_score=cv.overall_score,
            )
            for i, cv in enumerate(result.ranked_cvs, 1)
        ],
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
