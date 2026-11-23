import json
import os
import shutil
import socket
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

import httpx
from pydantic import BaseModel

MODEL = "gemma4:e4b"
MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "extractor model"
_model_lock = Lock()


@contextmanager
def local_ollama() -> Iterator[httpx.Client]:
    executable = shutil.which("ollama")
    if not executable:
        raise FileNotFoundError("Install Ollama for Windows, reopen PowerShell, then run python install.py.")

    # Pick a free loopback port so this server can run alongside an existing Ollama session.
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        host = f"127.0.0.1:{reservation.getsockname()[1]}"
    # Use the project's installed weights, disable cloud inference, and run on the CPU.
    environment = {
        **os.environ,
        "OLLAMA_HOST": host,
        "OLLAMA_MODELS": str(MODEL_DIR),
        "OLLAMA_NO_CLOUD": "1",
        "OLLAMA_NOPRUNE": "1",
        "OLLAMA_DEBUG_LOG_REQUESTS": "0",
        "OLLAMA_VULKAN": "0",
        "CUDA_VISIBLE_DEVICES": "-1",
        "HIP_VISIBLE_DEVICES": "-1",
        "ROCR_VISIBLE_DEVICES": "-1",
    }
    server = subprocess.Popen(
        [executable, "serve"],
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        timeout = httpx.Timeout(1800, connect=5)
        # Ignore system proxy settings so CV text goes straight to this local server.
        with httpx.Client(base_url=f"http://{host}", trust_env=False, timeout=timeout) as client:
            # Wait for the version endpoint to answer before handing the client to the caller.
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError(f"The project Ollama server exited at startup (code {server.returncode}).")
                try:
                    ready = client.get("/api/version", timeout=1)
                    if ready.is_success and ready.json().get("version"):
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.15)
            else:
                raise RuntimeError("The project Ollama server did not start within 30 seconds.")
            yield client
    finally:
        # Release the server and its memory even when startup or extraction fails.
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


@contextmanager
def model_session() -> Iterator[httpx.Client]:
    if not MODEL_DIR.is_dir():
        raise FileNotFoundError(f"Missing extraction model folder {MODEL_DIR}. Run python install.py.")
    # Extraction and ranking share the model and take turns using the machine's memory.
    with _model_lock, local_ollama() as client:
        yield client


def ask_json[T: BaseModel](
    client: httpx.Client,
    output: type[T],
    instructions: str,
    text: str,
    *,
    task: str = "extract this CV",
    keep_alive: str | int = 0,
    check: Callable[[T], str | None] | None = None,
    schema: dict | None = None,
) -> T:
    if schema is None:
        schema = output.model_json_schema()
    instructions += "\nJSON schema:\n" + json.dumps(schema, separators=(",", ":"))
    # Estimate prompt space in UTF-8 bytes and leave room for a larger reply on retry.
    prompt_bytes = len(text.encode("utf-8")) + len(instructions.encode("utf-8")) + 256
    for output_limit in (2048, 4096):
        response = client.post(
            "/api/chat",
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": text},
                ],
                "format": schema,
                "stream": False,
                "think": False,
                "truncate": False,
                "shift": False,
                "keep_alive": keep_alive,
                "options": {
                    "temperature": 0,
                    "num_gpu": 0,
                    "num_ctx": min(131072, max(8192, prompt_bytes + output_limit)),
                    "num_predict": output_limit,
                },
            },
        )
        if response.status_code == 404:
            raise RuntimeError(f"{MODEL} is missing from {MODEL_DIR}. Run python install.py.")
        if response.is_error:
            detail = response.reason_phrase
            try:
                body = response.json()
                if isinstance(body, dict):
                    detail = body.get("error") or detail
            except ValueError:
                pass
            raise RuntimeError(f"Ollama could not {task} (HTTP {response.status_code}): {detail}")

        correction = "Return all required keys in one complete JSON object. Keep entries concise."
        try:
            reply = response.json()
            if reply["done"] and reply.get("done_reason") != "length":
                result = output.model_validate_json(reply["message"]["content"])
                problem = check(result) if check else None
                if problem is None:
                    return result
                # Constraints such as valid evidence references depend on this particular CV.
                correction = problem
        except (KeyError, TypeError, ValueError):
            pass
        instructions += "\n" + correction
    if check:
        raise ValueError(f"Gemma could not {task} after two attempts. {correction}")
    raise ValueError(f"Gemma returned incomplete or invalid {output.__name__} data twice. No partial result was returned.")
