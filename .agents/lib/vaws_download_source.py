"""Choose a configured PyPI mirror without changing locked artifacts."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
import os
import re
import time
import tomllib
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

PYPI = "https://pypi.org/simple"
FILES = "https://files.pythonhosted.org/packages/"
PROBE_BYTES = 256 * 1024
PROBE_SECONDS = 4


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(value for name, value in attrs if name == "href" and value)


def _mirror_prefix(index: str, package: str, artifact: dict) -> str:
    page = index.rstrip("/") + "/" + package + "/"
    with urlopen(Request(page, headers={"Accept": "text/html"}), timeout=PROBE_SECONDS) as response:
        content = response.read(4 * 1024 * 1024 + 1)
    if len(content) > 4 * 1024 * 1024:
        raise ValueError("mirror index response is too large")
    parser = _Links()
    parser.feed(content.decode("utf-8"))
    suffix = artifact["url"][len(FILES):]
    for href in parser.links:
        candidate = urlsplit(urljoin(page, href))
        if not candidate.path.endswith("/" + suffix) or candidate.query:
            continue
        if candidate.scheme not in {"http", "https"} or candidate.username or candidate.password:
            continue
        if candidate.scheme == "http" and (urlsplit(index).scheme != "http" or candidate.hostname not in {"localhost", "127.0.0.1", "::1"}):
            continue
        if candidate.fragment and candidate.fragment != artifact["hash"].replace(":", "=", 1):
            continue
        url = candidate._replace(fragment="").geturl()
        return url[:-len(suffix)]
    raise ValueError("mirror does not expose the locked artifact with a compatible packages path")


def _probe(url: str) -> dict:
    started = time.monotonic()
    count = 0
    try:
        request = Request(url, headers={"Range": f"bytes=0-{PROBE_BYTES-1}"})
        with urlopen(request, timeout=PROBE_SECONDS) as response:
            while count < PROBE_BYTES and time.monotonic() - started < PROBE_SECONDS:
                data = response.read1(min(64 * 1024, PROBE_BYTES-count))
                if not data:
                    break
                count += len(data)
        seconds = max(time.monotonic()-started, 0.001)
        return {"bytes": count, "seconds": round(seconds, 3), "bytes_per_second": count/seconds}
    except Exception as exc:
        return {"bytes": count, "seconds": round(time.monotonic()-started, 3),
                "bytes_per_second": 0, "error": type(exc).__name__}


def select_pypi_transport(lock: bytes, *, offline: bool = False) -> tuple[bytes, list[str], dict]:
    """Probe only cold installs with an explicit, credential-free mirror setting.

    Only the temporary installation copy changes registry/artifact locations.
    uv still checks --locked and each original artifact hash; receipt inputs and
    ready cache keys continue to describe the canonical lock.
    """
    if offline:
        return lock, [], {"source": "locked_default", "probe": "offline"}
    configured = os.environ.get("VAWS_PYPI_MIRROR", "").strip().rstrip("/")
    if not configured:
        return lock, [], {"source": "locked_default", "probe": "not_configured"}
    parsed = urlsplit(configured)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("VAWS_PYPI_MIRROR must be an HTTP(S) index URL without credentials, query or fragment")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("VAWS_PYPI_MIRROR must use HTTPS outside loopback")
    document = tomllib.loads(lock.decode("utf-8"))
    candidates = [(package["name"], wheel) for package in document.get("package", [])
                  if package.get("source", {}).get("registry") == PYPI
                  for wheel in package.get("wheels", [])
                  if wheel.get("url", "").startswith(FILES) and wheel.get("hash", "").startswith("sha256:")]
    if not candidates:
        return lock, [], {"source": "locked_default", "probe": "no_pypi_artifacts"}
    universal = [item for item in candidates if item[1]["url"].endswith("-py3-none-any.whl")]
    pool = universal or candidates
    large = [item for item in pool if item[1].get("size", 0) >= PROBE_BYTES]
    name, sample = min(large, key=lambda item: item[1].get("size", 0)) if large else max(pool, key=lambda item: item[1].get("size", 0))
    try:
        prefix = _mirror_prefix(configured, name, sample)
        mirror_url = prefix + sample["url"][len(FILES):]
        with ThreadPoolExecutor(max_workers=2) as executor:
            default_future = executor.submit(_probe, sample["url"])
            mirror_future = executor.submit(_probe, mirror_url)
            default, mirror = default_future.result(), mirror_future.result()
    except Exception as exc:
        return lock, [], {"source": "locked_default", "probe": "mirror_unavailable", "error": type(exc).__name__}
    evidence = {"source": "locked_default", "default": default, "mirror": mirror}
    if not mirror["bytes_per_second"] or mirror["bytes_per_second"] < default["bytes_per_second"] * 1.25:
        return lock, [], evidence
    sections = re.split(r"(?m)(?=^\[\[package\]\])", lock.decode("utf-8"))
    for position, section in enumerate(sections):
        if not section.startswith("[[package]]"):
            continue
        package = tomllib.loads(section)["package"][0]
        if package.get("source", {}).get("registry") != PYPI:
            continue
        sections[position] = section.replace(json.dumps(PYPI), json.dumps(configured)).replace(
            '"' + FILES, '"' + prefix)
    mirrored = "".join(sections).encode("utf-8")
    # Round-trip the location mapping before handing anything to the installer.
    original_packages = document["package"]
    mirror_packages = tomllib.loads(mirrored.decode("utf-8"))["package"]
    for original, changed in zip(original_packages, mirror_packages, strict=True):
        if original.get("source", {}).get("registry") == PYPI:
            restored = json.loads(json.dumps(changed).replace(json.dumps(configured), json.dumps(PYPI)).replace('"' + prefix, '"' + FILES))
            if restored != original:
                raise ValueError("mirror changed locked dependency metadata")
        elif changed != original:
            raise ValueError("mirror changed a non-PyPI source")
    return mirrored, ["--default-index", configured], {**evidence, "source": "configured_mirror"}
