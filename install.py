from http.client import HTTPException
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from urllib.request import urlopen

from app.parsers.OCR.models import MODEL_DIR, MODELS, verified


def install() -> None:
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


if __name__ == "__main__":
    try:
        install()
    except (HTTPException, OSError, ValueError) as error:
        raise SystemExit(f"Model installation failed. {error} Run python install.py to retry.") from error
