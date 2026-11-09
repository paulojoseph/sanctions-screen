"""Download the official lists. This is the only module that touches the network."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from . import config

# source -> (file name in data/lists, official download URL)
SOURCES = {
    "ofac": (
        "ofac_sdn.xml",
        "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML",
    ),
    "un": (
        "un_consolidated.xml",
        "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
    ),
    "eu": (
        "eu_fsf.xml",
        "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token={token}",
    ),
    "uk": (
        "uk_consolidated.csv",
        "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv",
    ),
}


class FetchError(Exception):
    pass


def cache_dir() -> Path:
    return Path(os.environ.get("SANCTIONS_SCREEN_CACHE", ".cache"))


def _eu_token() -> str:
    # the Commission hands out the access token on the FSF page; it is not kept in the repo
    token = os.environ.get("SANCTIONS_SCREEN_EU_TOKEN", "")
    if not token:
        raise FetchError("eu: set SANCTIONS_SCREEN_EU_TOKEN to the token from the FSF page")
    return token


def fetch_one(source: str, dest_dir: Path, client: httpx.Client) -> Path:
    filename, url = SOURCES[source]
    if "{token}" in url:
        url = url.format(token=_eu_token())
    dest = dest_dir / filename
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with client.stream("GET", url, follow_redirects=True) as resp:
            if resp.status_code != 200:
                raise FetchError(f"{source}: {url} answered HTTP {resp.status_code}")
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_bytes():
                    fh.write(chunk)
    except httpx.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        raise FetchError(f"{source}: {exc}") from exc
    tmp.replace(dest)
    return dest


def fetch_all(dest_dir: str | Path, sources: list[str] | None = None) -> dict[str, Path]:
    """Download the requested lists (all of them by default) into `dest_dir`."""
    wanted = sources or list(SOURCES)
    unknown = [s for s in wanted if s not in SOURCES]
    if unknown:
        raise FetchError(f"unknown source(s): {', '.join(unknown)} (known: {', '.join(SOURCES)})")
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    headers = {"User-Agent": config.USER_AGENT}
    # FIXME: no retry or backoff. The EU server answers 429 when two fetches run close
    # together, and one failed source aborts the loop, leaving the lists we already
    # replaced mixed with old ones.
    with httpx.Client(timeout=config.FETCH_TIMEOUT_SECONDS, headers=headers) as client:
        for source in wanted:
            out[source] = fetch_one(source, dest, client)
    return out
