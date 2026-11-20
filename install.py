import json
from http.client import HTTPException
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from urllib.request import urlopen

import httpx
from filelock import FileLock

from app.extraction import runtime as gemma
from app.parsers.OCR.models import MODEL_DIR, MODELS, verified


def install_ocr() -> None:
    for model, (revision, files) in MODELS.items():
        folder = MODEL_DIR / model
        folder.mkdir(parents=True, exist_ok=True)
        for name, digest in files.items():
            destination = folder / name
            if verified(destination, digest):
                continue
            url = f"https://huggingface.co/PaddlePaddle/{model}/resolve/{revision}/{name}"
            print(f"Downloading {model}/{name} ...", flush=True)
            with TemporaryDirectory(dir=folder) as staging:
                incoming = Path(staging) / name
                with urlopen(url, timeout=90) as response, incoming.open("wb") as output:
                    copyfileobj(response, output)
                if not verified(incoming, digest):
                    raise ValueError(f"The download of {model}/{name} was incomplete or damaged.")
                incoming.replace(destination)
        print(f"Ready: {model}")
    print(f"OCR models are ready in {MODEL_DIR}")


def install_extraction() -> None:
    """Check the extractor's own Ollama store before requesting any model download."""
    gemma.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model = {"model": gemma.MODEL}
    print(f"Checking for {gemma.MODEL} in {gemma.MODEL_DIR} ...", flush=True)
    with FileLock(gemma.MODEL_DIR / ".install.lock"), gemma.local_ollama() as client:
        status = client.post("/api/show", json=model)
        if status.status_code == 404:
            print(f"Downloading {gemma.MODEL} to {gemma.MODEL_DIR} ...", flush=True)
            # Ollama verifies and stores the layers, and can resume an interrupted pull.
            with client.stream("POST", "/api/pull", json={**model, "stream": True}) as response:
                response.raise_for_status()
                last_status = ""
                for line in response.iter_lines():
                    if not line:
                        continue
                    progress = json.loads(line)
                    if progress.get("error"):
                        raise RuntimeError(progress["error"])
                    status_text = progress.get("status")
                    if status_text and status_text != last_status:
                        last_status = status_text
                        print(last_status, flush=True)
                if last_status != "success":
                    raise RuntimeError("The Gemma download ended before Ollama confirmed success.")
            status = client.post("/api/show", json=model)
        status.raise_for_status()
    print(f"Ready: {gemma.MODEL} in {gemma.MODEL_DIR}")


def install() -> None:
    install_ocr()
    install_extraction()


if __name__ == "__main__":
    try:
        install()
    except (HTTPException, OSError, RuntimeError, ValueError, httpx.HTTPError) as error:
        raise SystemExit(f"Model installation failed. {error} Run python install.py to retry.") from error
