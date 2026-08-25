from __future__ import annotations

import asyncio
import concurrent.futures
import os
import platform
import shutil
import subprocess
import threading
import webbrowser
from pathlib import Path
from typing import Optional

_OS = platform.system()


def _playwright_imports():
    from playwright.async_api import (
        async_playwright,
        BrowserContext,
        Page,
        Playwright,
        TimeoutError as PlaywrightTimeout,
    )
    return async_playwright, BrowserContext, Page, Playwright, PlaywrightTimeout


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return "about:blank"
    if "://" in url:
        return url
    if "." not in url:
        url += ".com"
    return "https://" + url


def _user_agent() -> str:
    if _OS == "Windows":
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    if _OS == "Darwin":
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def _real_profile_dir(browser: str) -> str:
    home = Path.home()
    local = os.environ.get("LOCALAPPDATA", "")
    roam = os.environ.get("APPDATA", "")
    candidates: list[Path] = []
    if _OS == "Windows":
        m = {
            "chrome": [Path(local) / "Google" / "Chrome" / "User Data"],
            "edge": [Path(local) / "Microsoft" / "Edge" / "User Data"],
            "brave": [Path(local) / "BraveSoftware" / "Brave-Browser" / "User Data"],
            "vivaldi": [Path(local) / "Vivaldi" / "User Data"],
            "opera": [Path(roam) / "Opera Software" / "Opera Stable", Path(local) / "Opera Software" / "Opera Stable"],
            "operagx": [Path(roam) / "Opera Software" / "Opera GX Stable", Path(local) / "Opera Software" / "Opera GX Stable"],
        }
        candidates = m.get(browser, [])
    elif _OS == "Darwin":
        lib = home / "Library" / "Application Support"
        m = {
            "chrome": [lib / "Google" / "Chrome" / "User Data"],
            "edge": [lib / "Microsoft Edge" / "User Data"],
            "brave": [lib / "BraveSoftware" / "Brave-Browser" / "User Data"],
            "vivaldi": [lib / "Vivaldi" / "User Data"],
            "opera": [lib / "com.operasoftware.Opera"],
            "operagx": [lib / "com.operasoftware.OperaGX"],
        }
        candidates = m.get(browser, [])
    else:
        cfg = home / ".config"
        m = {
            "chrome": [cfg / "google-chrome", cfg / "chromium"],
            "edge": [cfg / "microsoft-edge"],
            "brave": [cfg / "BraveSoftware" / "Brave-Browser"],
            "vivaldi": [cfg / "vivaldi"],
            "opera": [cfg / "opera"],
            "operagx": [cfg / "opera-gx"],
        }
        candidates = m.get(browser, [])
    for p in candidates:
        if p.exists():
            print(f"[Browser] Real profile found for {browser}: {p}")
            return str(p)
    fallback = home / ".jarvis_profiles" / browser
    fallback.mkdir(parents=True, exist_ok=True)
    print(f"[Browser] Real profile not found for {browser}, using: {fallback}")
    return str(fallback)


def _firefox_profile_dir() -> Optional[str]:
    home = Path.home()
    if _OS == "Windows":
        base = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox"
    elif _OS == "Darwin":
        base = home / "Library" / "Application Support" / "Firefox"
    else:
        base = home / ".mozilla" / "firefox"
    ini = base / "profiles.ini"
    if not ini.exists():
        return None
    current: dict[str, str] = {}
    default_path: Optional[str] = None
    for line in ini.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("["):
            p = current.get("Path", "")
            if p and current.get("Default") == "1":
                default_path = str(base / p) if current.get("IsRelative", "1") == "1" else p
            current = {}
        elif "=" in line:
            k, _, v = line.partition("=")
            current[k.strip()] = v.strip()
    p = current.get("Path", "")
    if p and current.get("Default") == "1":
        default_path = str(base / p) if current.get("IsRelative", "1") == "1" else p
    return default_path


# NOTE: the rest of the original browser-control implementation follows.
# Playwright is intentionally imported only inside _playwright_imports(), so merely
# loading this module no longer initializes Playwright's Python-side machinery.
