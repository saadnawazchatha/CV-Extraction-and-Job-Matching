"""Run the local model on the raw text returned by the CV parser."""

import httpx
from fastapi import HTTPException

from .extraction.extractor import extract_cv
from .extraction.schema import CV


def extract_information(file_name: str, raw_text: str) -> CV:
    """Identify errors by filename and take candidate facts only from the CV text."""
    try:
        return extract_cv(raw_text)
    except httpx.TimeoutException as error:
        raise HTTPException(504, f"{file_name}: the local model timed out.") from error
    except (OSError, RuntimeError, httpx.HTTPError) as error:
        raise HTTPException(503, f"{file_name}: {error}") from error
    except ValueError as error:
        raise HTTPException(502, f"{file_name}: {error}") from error
