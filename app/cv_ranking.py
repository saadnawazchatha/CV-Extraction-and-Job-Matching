import httpx
from fastapi import HTTPException

from .ranking.ranker import NoJobRequirements, rank_batch
from .ranking.schema import RankingRequest, RankingResponse


def rank_cvs(request: RankingRequest) -> RankingResponse:
    try:
        return rank_batch(request)
    except NoJobRequirements as error:
        raise HTTPException(422, str(error)) from error
    except httpx.TimeoutException as error:
        raise HTTPException(504, "The local model timed out while ranking CVs.") from error
    except (OSError, RuntimeError, httpx.HTTPError) as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(502, str(error)) from error
