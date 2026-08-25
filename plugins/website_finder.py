"""
JARVIS Website Finder / Search Fallback Plugin

Purpose:
    Gives JARVIS a reliable fallback for finding websites and webpages.

Behavior:
    - If the input looks like a URL/domain, check it DIRECTLY.
    - If the direct website works, return its status/title/content.
    - If the direct check fails, automatically search for the website.
    - If the input is a normal search query, use DuckDuckGo.
    - Never claim a website does not exist just because search found nothing.

Examples:
    firstabide.netlify.app
    https://firstabide.netlify.app
    www.example.com
    "information about Roblox Studio"
"""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import quote

import requests


# ============================================================
# PLUGIN DEFINITION
# ============================================================

PLUGIN = {
    "name": "website_finder",
    "description": (
        "Fallback website finder and direct website checker. Use this when "
        "normal web search cannot find a website, domain, webpage, or online "
        "resource. If the user gives a URL or domain such as example.com, "
        "firstabide.netlify.app, a Netlify subdomain, GitHub Pages site, or "
        "Cloudflare Pages site, ALWAYS check the website directly instead of "
        "relying only on search indexing. If a direct check fails, search "
        "the web for references to the site. Do not claim that a website "
        "does not exist merely because search returned no results."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": (
                    "The website URL, domain, website name, or search query "
                    "to investigate."
                ),
            },
            "mode": {
                "type": "STRING",
                "description": (
                    "Optional mode: auto, direct, or search. URL/domain "
                    "detection always takes priority over search mode."
                ),
            },
        },
        "required": ["query"],
    },
}


# ============================================================
# SETTINGS
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0 Safari/537.36"
)

TIMEOUT = 15

MAX_PAGE_TEXT = 2500
MAX_SEARCH_RESULTS = 8


# ============================================================
# TEXT HELPERS
# ============================================================

def _clean_text(text: str, limit: int = MAX_PAGE_TEXT) -> str:
    """
    Convert HTML/text into a reasonably readable string.
    """

    if not text:
        return ""

    try:
        text = html.unescape(text)

        # Remove scripts.
        text = re.sub(
            r"<script\b[^>]*>.*?</script>",
            " ",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove styles.
        text = re.sub(
            r"<style\b[^>]*>.*?</style>",
            " ",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove noscript.
        text = re.sub(
            r"<noscript\b[^>]*>.*?</noscript>",
            " ",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove HTML comments.
        text = re.sub(
            r"<!--.*?-->",
            " ",
            text,
            flags=re.DOTALL,
        )

        # Remove HTML tags.
        text = re.sub(
            r"<[^>]+>",
            " ",
            text,
        )

        # Decode entities again in case tags contained entities.
        text = html.unescape(text)

        # Normalize whitespace.
        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        if len(text) > limit:
            text = text[:limit].rstrip() + "..."

        return text

    except Exception:
        return str(text)[:limit]


def _extract_title(page: str) -> str:
    """
    Extract the HTML <title>.
    """

    if not page:
        return ""

    try:
        match = re.search(
            r"<title\b[^>]*>(.*?)</title>",
            page,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return ""

        return _clean_text(
            match.group(1),
            300,
        )

    except Exception:
        return ""


# ============================================================
# URL DETECTION
# ============================================================

def _looks_like_url(value: str) -> bool:
    """
    Detect domains and URLs.

    Examples recognized:

        example.com
        www.example.com
        https://example.com
        http://example.com
        firstabide.netlify.app
        something.github.io
    """

    if not value:
        return False

    value = value.strip()

    # Remove common punctuation accidentally spoken/typed after URLs.
    value = value.rstrip(".,!?;:)")

    lowered = value.lower()

    # Explicit URL.
    if lowered.startswith("http://"):
        return True

    if lowered.startswith("https://"):
        return True

    # Remove www for domain matching.
    check = lowered

    if check.startswith("www."):
        check = check[4:]

    # Domain pattern.
    #
    # Supports:
    # example.com
    # example.co.uk
    # foo.netlify.app
    # foo.github.io
    #
    domain_pattern = (
        r"^[a-z0-9]"
        r"(?:[a-z0-9.-]*[a-z0-9])?"
        r"\."
        r"[a-z]{2,}"
        r"(?:\.[a-z]{2,})?"
        r"(?:[/:?#].*)?$"
    )

    return bool(
        re.match(
            domain_pattern,
            check,
            flags=re.IGNORECASE,
        )
    )


def _normalise_url(value: str) -> str:
    """
    Convert a domain into an HTTPS URL.
    """

    value = value.strip()

    # Remove punctuation accidentally attached to the URL.
    value = value.rstrip(".,!?;:)")

    if not value.startswith(
        (
            "http://",
            "https://",
        )
    ):
        value = "https://" + value

    return value


# ============================================================
# DIRECT WEBSITE CHECK
# ============================================================

def _direct_check(url: str) -> tuple[bool, str]:
    """
    Directly request a website.

    Returns:

        (success, result_text)
    """

    url = _normalise_url(url)

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
            },
            timeout=TIMEOUT,
            allow_redirects=True,
        )

        final_url = response.url
        status = response.status_code

        content_type = response.headers.get(
            "content-type",
            "unknown",
        )

        title = ""

        if "text/html" in content_type.lower():
            title = _extract_title(
                response.text
            )

        output = []

        output.append(
            "DIRECT WEBSITE CHECK"
        )

        output.append(
            f"Requested URL: {url}"
        )

        output.append(
            f"Final URL: {final_url}"
        )

        output.append(
            f"HTTP status: {status}"
        )

        output.append(
            f"Content type: {content_type}"
        )

        if title:
            output.append(
                f"Page title: {title}"
            )

        # --------------------------------------------------------
        # Successful website
        # --------------------------------------------------------

        if 200 <= status < 400:

            output.append(
                "Result: The website responded successfully."
            )

            if "text/html" in content_type.lower():

                page_text = _clean_text(
                    response.text,
                    MAX_PAGE_TEXT,
                )

                if page_text:

                    output.append("")
                    output.append(
                        "Page text:"
                    )
                    output.append(
                        page_text
                    )

            return True, "\n".join(output)

        # --------------------------------------------------------
        # Restricted website
        # --------------------------------------------------------

        if status in (
            401,
            403,
        ):

            output.append(
                "Result: The website exists, but "
                "access is restricted."
            )

            return True, "\n".join(output)

        # --------------------------------------------------------
        # Not found
        # --------------------------------------------------------

        if status == 404:

            output.append(
                "Result: The server responded with HTTP 404. "
                "The domain/server is reachable, but this specific "
                "page was not found."
            )

            return True, "\n".join(output)

        # --------------------------------------------------------
        # Other HTTP error
        # --------------------------------------------------------

        output.append(
            f"Result: The server responded with HTTP {status}."
        )

        return True, "\n".join(output)

    except requests.exceptions.SSLError:

        return (
            False,
            (
                f"I reached {url}, but the secure connection failed "
                "because of an SSL/TLS certificate problem. "
                "This does not prove that the website does not exist."
            ),
        )

    except requests.exceptions.ConnectionError:

        return (
            False,
            (
                f"I could not establish a connection to {url}. "
                "This does not prove that the website does not exist."
            ),
        )

    except requests.exceptions.Timeout:

        return (
            False,
            (
                f"{url} took too long to respond. "
                "This does not prove that the website does not exist."
            ),
        )

    except requests.exceptions.RequestException as e:

        return (
            False,
            (
                f"I could not directly check {url}. "
                f"Request error: {e}"
            ),
        )

    except Exception as e:

        return (
            False,
            (
                f"Unexpected error while checking {url}: {e}"
            ),
        )


# ============================================================
# DUCKDUCKGO SEARCH
# ============================================================

def _search_duckduckgo(query: str) -> str:
    """
    Search DuckDuckGo's HTML endpoint.

    No API key required.
    """

    search_url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    try:

        response = requests.get(
            search_url,
            headers={
                "User-Agent": USER_AGENT,
            },
            timeout=TIMEOUT,
        )

        if not response.ok:

            return (
                "DuckDuckGo fallback search returned "
                f"HTTP {response.status_code}."
            )

        page = response.text

        results = []

        # DuckDuckGo result links.
        matches = re.findall(
            r'class=["\']result__a["\'][^>]*'
            r'href=["\']([^"\']+)["\'][^>]*>'
            r'(.*?)</a>',
            page,
            flags=re.IGNORECASE | re.DOTALL,
        )

        for href, title_html in matches[
            :MAX_SEARCH_RESULTS
        ]:

            title = _clean_text(
                title_html,
                300,
            )

            href = html.unescape(
                href
            )

            if title and href:

                results.append(
                    f"- {title}\n"
                    f"  {href}"
                )

        if not results:

            return (
                f"No indexed DuckDuckGo results were found "
                f"for '{query}'. "
                "This does NOT prove that the website or resource "
                "does not exist."
            )

        return (
            f"WEB SEARCH RESULTS FOR: {query}\n\n"
            + "\n\n".join(results)
        )

    except requests.exceptions.RequestException as e:

        return (
            "I could not perform the fallback web search. "
            f"Request error: {e}"
        )

    except Exception as e:

        return (
            "Unexpected fallback search error: "
            f"{e}"
        )


# ============================================================
# SEARCH WITH URL FALLBACK
# ============================================================

def _search_with_fallback(query: str) -> str:
    """
    Search a normal query.

    If it looks like a URL, DIRECTLY check it first.
    """

    query = query.strip()

    if not query:

        return (
            "Sir, I need a website, domain, "
            "or search query."
        )

    # --------------------------------------------------------
    # CRITICAL FIX
    #
    # A URL ALWAYS gets directly checked first.
    # Gemini cannot accidentally force it into search-only mode.
    # --------------------------------------------------------

    if _looks_like_url(query):

        success, direct_result = _direct_check(
            query
        )

        if success:
            return direct_result

        # Direct connection failed.
        # Search for references anyway.

        search_result = _search_duckduckgo(
            query
        )

        return (
            "DIRECT CHECK:\n"
            + direct_result
            + "\n\n"
            "FALLBACK SEARCH:\n"
            + search_result
        )

    # Normal search query.
    return _search_duckduckgo(
        query
    )


# ============================================================
# JARVIS ENTRY POINT
# ============================================================

def run(
    parameters: dict,
    player=None,
    session_memory=None,
) -> str:
    """
    Main JARVIS plugin entry point.

    Never intentionally raises an exception.
    """

    try:

        parameters = (
            parameters
            if isinstance(parameters, dict)
            else {}
        )

        query = str(
            parameters.get(
                "query",
                "",
            )
        ).strip()

        mode = str(
            parameters.get(
                "mode",
                "auto",
            )
        ).strip().lower()

        if not query:

            return (
                "Sir, please give me a website, "
                "domain, or search query."
            )

        # ====================================================
        # URL OVERRIDE
        # ====================================================
        #
        # Even if Gemini says mode="search", a URL gets
        # checked directly.
        #
        # This is the important part that fixes your issue.
        # ====================================================

        if _looks_like_url(query):

            success, direct_result = _direct_check(
                query
            )

            if success:

                result_text = direct_result

            else:

                fallback_result = (
                    _search_duckduckgo(
                        query
                    )
                )

                result_text = (
                    "DIRECT WEBSITE CHECK:\n"
                    + direct_result
                    + "\n\n"
                    "FALLBACK WEB SEARCH:\n"
                    + fallback_result
                )

        # ====================================================
        # Explicit direct mode
        # ====================================================

        elif mode == "direct":

            success, direct_result = _direct_check(
                query
            )

            result_text = direct_result

        # ====================================================
        # Explicit search mode
        # ====================================================

        elif mode == "search":

            result_text = _search_duckduckgo(
                query
            )

        # ====================================================
        # Automatic mode
        # ====================================================

        else:

            result_text = _search_with_fallback(
                query
            )

        # ====================================================
        # JARVIS LOG
        # ====================================================

        if player:

            try:

                player.write_log(
                    "JARVIS: "
                    + result_text[:1500]
                )

            except Exception:
                pass

        # ====================================================
        # Prevent gigantic spoken responses
        # ====================================================

        if len(result_text) > 6000:

            result_text = (
                result_text[:6000]
                + "\n[Output truncated.]"
            )

        return result_text

    except Exception as e:

        error = (
            "Sir, the website finder encountered "
            f"an unexpected error: {e}"
        )

        if player:

            try:

                player.write_log(
                    "JARVIS: "
                    + error
                )

            except Exception:
                pass

        return error