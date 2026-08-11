import re

from bs4 import BeautifulSoup


def clean_email_text(text):
    text = str(text or "").replace("\xa0", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_text(html):
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style"]):
        element.decompose()

    for link in soup.find_all("a"):
        href = link.get("href")
        if href:
            link.append(f" {href}")

    return clean_email_text(soup.get_text("\n"))
