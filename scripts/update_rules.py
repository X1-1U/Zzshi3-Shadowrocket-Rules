#!/usr/bin/env python3
"""Build the self-hosted Shadowrocket rule bundle from sources.conf."""

from __future__ import annotations

import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "sources.conf"
RULES_DIR = ROOT / "rules"
OUTPUT_CONF = ROOT / "Shadowrocket-Rules.conf"
EXPECTED_SOURCES = 56
EXPECTED_FILES = 56
MINIMUM_RULES = 150_000
OUTPUT_NAMES = [
    "Custom-Proxy.list",
    "Adult.list",
    "Media-Server.list",
    "Custom-Direct.list",
    "Test.list",
    "Block.list",
    "ChatGPT.list",
    "Claude.list",
    "Meta-AI.list",
    "Perplexity.list",
    "Copilot.list",
    "Gemini.list",
    "Groq.list",
    "Grok.list",
    "Twitch.list",
    "Reddit.list",
    "GitHub.list",
    "Telegram.list",
    "Telegram-IP.list",
    "WhatsApp.list",
    "Facebook.list",
    "Apple.list",
    "Apple-CN.list",
    "Apple-Custom.list",
    "Microsoft.list",
    "Crypto.list",
    "OKX.list",
    "Bybit.list",
    "Binance.list",
    "BiliBili.list",
    "YouTube.list",
    "TikTok.list",
    "Netflix.list",
    "Netflix-IP.list",
    "Disney.list",
    "Amazon.list",
    "Crunchyroll.list",
    "Popcorn.list",
    "HBO.list",
    "Spotify.list",
    "Steam.list",
    "Epic.list",
    "EA.list",
    "Blizzard.list",
    "Ubisoft.list",
    "PlayStation.list",
    "Nintendo.list",
    "Google.list",
    "Google-IP.list",
    "Nvidia.list",
    "Proxy.list",
    "Global.list",
    "Direct.list",
    "China.list",
    "China-IP.list",
    "Private.list",
]


@dataclass(frozen=True)
class Source:
    url: str
    policy: str
    no_resolve: bool


def parse_sources() -> list[Source]:
    sources: list[Source] = []
    for number, raw_line in enumerate(SOURCE_FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line.startswith("RULE-SET,"):
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) not in (3, 4) or (len(parts) == 4 and parts[3] != "no-resolve"):
            raise ValueError(f"Invalid source definition on line {number}: {raw_line}")
        sources.append(Source(parts[1], parts[2], len(parts) == 4))

    if len(sources) != EXPECTED_SOURCES:
        raise ValueError(f"Expected {EXPECTED_SOURCES} sources, found {len(sources)}")
    urls = [source.url for source in sources]
    if len(set(urls)) != len(urls):
        raise ValueError("sources.conf contains duplicate URLs")
    return sources


def raw_github_url(url: str) -> str:
    """Bypass CDN caching when GitHub Actions refreshes an upstream file."""
    prefix = "https://cdn.jsdelivr.net/gh/"
    if not url.startswith(prefix):
        return url
    spec = url[len(prefix) :]
    match = re.fullmatch(r"([^/]+/[^/@]+)@([^/]+)/(.+)", spec)
    if not match:
        raise ValueError(f"Unsupported jsDelivr GitHub URL: {url}")
    repository, ref, path = match.groups()
    return f"https://raw.githubusercontent.com/{repository}/{ref}/{path}"


def source_label(url: str) -> str:
    spec = url.removeprefix("https://cdn.jsdelivr.net/gh/")
    match = re.fullmatch(r"([^/]+/[^/@]+)@[^/]+/(.+)", spec)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.netloc}{parsed.path}"


def fetch(source: Source) -> list[str]:
    request = urllib.request.Request(
        raw_github_url(source.url),
        headers={"User-Agent": "Zzshi3-Shadowrocket-Rules/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Failed to download {source.url}: {exc}") from exc

    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"Upstream is not UTF-8 text: {source.url}") from exc

    rules: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        if line in {"payload:", "rules:"}:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        if len(line) >= 2 and line[0] == line[-1] and line[0] in {"'", '"'}:
            line = line[1:-1].strip()
        if "," not in line or not re.fullmatch(r"[A-Z0-9-]+", line.split(",", 1)[0]):
            raise RuntimeError(f"Unrecognized rule from {source.url}: {raw_line}")
        rules.append(line)

    if not rules:
        raise RuntimeError(f"Upstream returned no usable rules: {source.url}")
    return rules


def build() -> None:
    sources = parse_sources()
    downloaded = {source.url: fetch(source) for source in sources}
    if len(OUTPUT_NAMES) != EXPECTED_FILES or len(set(OUTPUT_NAMES)) != EXPECTED_FILES:
        raise ValueError("OUTPUT_NAMES must contain 56 unique filenames")

    RULES_DIR.mkdir(parents=True, exist_ok=True)
    expected_paths: set[Path] = set()
    total_rules = 0
    crypto_rules: list[str] = []

    for index, (source, filename) in enumerate(zip(sources, OUTPUT_NAMES), 1):
        path = RULES_DIR / filename
        expected_paths.add(path)
        lines = [
            f"# Zzshi3 Shadowrocket source {index:02d}",
            f"# Policy: {source.policy}",
            "",
            f"# Source: {source_label(source.url)}",
        ]
        rules = downloaded[source.url]
        lines.extend(rules)
        total_rules += len(rules)
        if source.policy == "Crypto":
            crypto_rules.extend(rules)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for stale in RULES_DIR.glob("*.list"):
        if stale not in expected_paths:
            stale.unlink()

    repository = os.environ.get("GITHUB_REPOSITORY", "X1-1U/Zzshi3-Shadowrocket-Rules")
    branch = os.environ.get("RULES_BRANCH", "main")
    base = f"https://raw.githubusercontent.com/{repository}/{branch}/rules"
    config_lines = [
        "[Rule]",
        "# Zzshi3 Shadowrocket self-hosted rules",
        f"# {EXPECTED_SOURCES} unique upstream sources in {EXPECTED_FILES} ordered files.",
    ]
    for source, filename in zip(sources, OUTPUT_NAMES):
        suffix = ",no-resolve" if source.no_resolve else ""
        config_lines.append(
            f"RULE-SET,{base}/{filename},{source.policy}{suffix}"
        )
    config_lines.append("FINAL,其他")
    OUTPUT_CONF.write_text("\n".join(config_lines) + "\n", encoding="utf-8")

    if total_rules < MINIMUM_RULES:
        raise RuntimeError(f"Only {total_rules} rules were generated; expected at least {MINIMUM_RULES}")
    crypto_text = "\n".join(crypto_rules).lower()
    missing = [keyword for keyword in ("binance", "okx", "bybit") if keyword not in crypto_text]
    if missing:
        raise RuntimeError(f"Crypto validation failed; missing: {', '.join(missing)}")

    print(
        f"Generated {EXPECTED_FILES} files with {total_rules} rules "
        f"from {EXPECTED_SOURCES} unique upstream sources."
    )


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:  # concise diagnostics for GitHub Actions
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
