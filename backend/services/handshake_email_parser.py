import re
from html import unescape
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup
import requests

CTA_TEXT = {
    "view job",
    "view posting",
    "view details",
    "apply now",
    "apply",
    "see job",
    "see posting",
}

TRACKING_PATTERNS = (
    "unsubscribe",
    "preferences",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    "click.",
    "track.",
    "/track",
    "pixel",
)


def normalize_link_text(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def unwrap_tracking_url(href):
    """Return a nested URL when a tracking link carries one as a query param."""
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    for key in ("url", "u", "target", "redirect", "redirect_url"):
        values = query.get(key)
        if values and values[0].startswith(("http://", "https://")):
            return unquote(values[0])
    return href


def extract_html_links(html):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()

    for tag in soup.find_all("a", href=True):
        href = unescape(tag.get("href", "")).strip()
        if not href or href.startswith(("mailto:", "tel:", "#")):
            continue

        href = unwrap_tracking_url(href)
        visible_text = normalize_link_text(tag.get_text(" "))
        key = (href, visible_text)
        if key in seen:
            continue
        seen.add(key)
        links.append({"href": href, "text": visible_text})

    return links


def is_handshake_posting_url(href):
    """True only when the URL's *path* looks like a real Handshake posting.

    This checks urlparse(href).path specifically, not the whole URL string.
    A login-page redirect like
    ".../login?next=%2Fjob-search%2F11263669" or even the unencoded
    ".../login?next=/job-search/11263669" must NOT match here — the path is
    "/login", the posting reference is just sitting in a query parameter.
    Checking the full string (the previous behavior) treated those as valid
    postings, which is how "Apply" ended up sending people to a Handshake
    sign-in page instead of the actual listing.
    """
    href_lower = (href or "").lower()
    if "joinhandshake.com" not in href_lower:
        return False

    path = urlparse(href_lower).path
    return any(marker in path for marker in ("/postings/", "/stu/postings/", "/jobs/", "/job-search/"))


def is_login_or_auth_url(href):
    """True when the URL's path points at a login/auth/session page rather
    than content — regardless of domain. A resolved or picked link that
    lands here is not something we should ever label "Apply"."""
    path = urlparse((href or "").lower()).path
    return any(
        marker in path
        for marker in ("/login", "/signin", "/sign-in", "/sign_in", "/session", "/sessions", "/auth")
    )


def is_placeholder_url(href):
    return "example.com" in (href or "").lower()


def is_handshake_tracking_url(href):
    href_lower = (href or "").lower()
    return "joinhandshake.com" in href_lower and (
        "/c/" in href_lower
        or "email." in href_lower
        or "notifications." in href_lower
        or "g.joinhandshake.com" in href_lower
    )


def is_tracking_or_low_value_url(href):
    href_lower = (href or "").lower()
    return any(pattern in href_lower for pattern in TRACKING_PATTERNS)


def is_real_apply_url(href, trusted_cta=False):
    """Single source of truth for "is this a link we're confident enough
    about to label Apply and send someone to." Used by extraction, the
    persistent job store's sanitizer, and the chatbot — nobody else should
    reimplement this check.

    trusted_cta=True means the link's own visible text was something like
    "Apply" or "View Job" in the source email, so we trust it regardless of
    which domain it points to (Handshake, or the employer's own career
    page) — matching the fact that either kind of link is a legitimate way
    to apply.
    """
    if not href or not re.match(r"^https?://", href, re.IGNORECASE):
        return False
    if is_placeholder_url(href):
        return False
    if is_login_or_auth_url(href):
        return False
    if is_handshake_tracking_url(href):
        return False
    if trusted_cta:
        return True
    return is_handshake_posting_url(href)


def resolve_handshake_tracking_url(href, timeout=8):
    """Resolve a Handshake email redirect into its first real posting URL.

    Handshake email buttons often point at email.notifications.joinhandshake.com
    tracking links. A single unauthenticated request returns a 302 Location
    header containing the clean app.joinhandshake.com/job-search/... URL.
    We intentionally do not follow redirects, because following may land on a
    login page and hide the useful Location header.
    """
    if not is_handshake_tracking_url(href):
        return href

    try:
        response = requests.get(
            href,
            allow_redirects=False,
            timeout=timeout,
            headers={"User-Agent": "CareerCopilot/1.0"},
        )
    except requests.RequestException:
        return None

    location = response.headers.get("location") or response.headers.get("Location")
    if location and is_handshake_posting_url(location):
        return location

    return None


def extract_plain_text_links(text):
    links = re.findall(r"https?://[^\s\"'>]+", text or "")
    cleaned = []

    for link in links:
        link = link.rstrip(".,)]}")
        if link not in cleaned:
            cleaned.append(link)

    return cleaned


def pick_application_link(html=None, text=None):
    """Return {"href": ..., "is_cta": bool} for the best application link
    found in the email, or None if nothing usable was found.

    is_cta tells the caller whether the link's own visible text was an
    explicit call-to-action ("Apply", "View Job", ...) — that's a strong
    enough signal to trust the link even if it points somewhere other than
    joinhandshake.com (e.g. the employer's own career page).

    Note: this deliberately does NOT try to follow tracking-redirect links
    (e.g. click.joinhandshake.com/...) server-side. An unauthenticated
    server-side request to a Handshake email-tracking link almost always
    lands on a Handshake login page rather than the real posting, since
    there's no browser session to satisfy — code that used to do this
    (resolve_handshake_redirect_url) was misclassifying those login pages
    as valid postings and sending people to a sign-in screen instead of the
    job listing. The original tracking link is left as-is; when the person
    actually clicks it in their own logged-in browser, Handshake's redirect
    works exactly as intended.
    """
    links = extract_html_links(html)

    for link in links:
        if link["text"] in CTA_TEXT:
            return {"href": link["href"], "is_cta": True}

    for link in links:
        if is_handshake_posting_url(link["href"]):
            return {"href": link["href"], "is_cta": False}

    for link in links:
        if not is_tracking_or_low_value_url(link["href"]):
            return {"href": link["href"], "is_cta": False}

    for href in extract_plain_text_links(text):
        href = unwrap_tracking_url(href)
        if is_handshake_posting_url(href):
            return {"href": href, "is_cta": False}

    for href in extract_plain_text_links(text):
        href = unwrap_tracking_url(href)
        if not is_tracking_or_low_value_url(href):
            return {"href": href, "is_cta": False}

    return None


def extract_all_links(html=None, text=None):
    links = []

    for link in extract_html_links(html):
        href = link["href"]
        if href not in links:
            links.append(href)

    for href in extract_plain_text_links(text):
        href = unwrap_tracking_url(href)
        if href not in links:
            links.append(href)

    return links
