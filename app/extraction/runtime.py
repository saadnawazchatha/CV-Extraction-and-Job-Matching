import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

MODEL = "gemma4:e4b"
MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "extractor model"


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
