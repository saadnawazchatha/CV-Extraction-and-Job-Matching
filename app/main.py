from fastapi import FastAPI, UploadFile
from pydantic import BaseModel

from .cv_parser import parse_cv
from .extraction.schema import CV
from .information_extraction import extract_information

app = FastAPI(title="CV extraction service", docs_url=None, redoc_url=None)


class CVResponse(BaseModel):
    file_name: str
    data: str
    extracted_data: CV


@app.post("/cv/raw")
def read_cv(file: UploadFile) -> CVResponse:
    file_name, raw_text = parse_cv(file)
    extracted_data = extract_information(file_name, raw_text)
    return CVResponse(file_name=file_name, data=raw_text, extracted_data=extracted_data)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
