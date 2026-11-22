"""Dependency-free checks for local assets, anchors, content and the theme setup."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def validate_page(filename):
    html = (ROOT / filename).read_text()
    page = Page(html)
    ids = [attrs["id"] for _, attrs in page.tags if "id" in attrs]
    assert len(ids) == len(set(ids)), f"Duplicate HTML IDs in {filename}"
    for tag, attrs in page.tags:
        if tag == "img":
            assert "alt" in attrs, "Image missing alternative text"
        for field in ("src", "href"):
            url = attrs.get(field, "")
            parsed = urlsplit(url)
            if not url or parsed.scheme or parsed.netloc:
                continue
            target = ROOT / unquote(parsed.path) if parsed.path else ROOT / filename
            assert target.is_file(), f"Missing asset: {url}"
            if parsed.fragment and target.suffix == ".html":
                target_ids = {a["id"] for _, a in Page(target.read_text()).tags if "id" in a}
                assert parsed.fragment in target_ids, f"Missing anchor: {url}"
        if attrs.get("target") == "_blank":
            assert "noopener" in attrs.get("rel", ""), "External tab missing noopener"
    return html, page


html, page = validate_page("index.html")
validate_page("event.html")

assert len(re.findall(r'<article class="publication-card', html)) == 9
assert sum(tag == "button" and "data-theme-toggle" in attrs for tag, attrs in page.tags) == 1
assert 'class="artwork"' not in html, "Paintings should not be displayed as standalone artwork"
assert all("images/monet/" not in attrs.get("src", "") for tag, attrs in page.tags if tag == "img")
assert 'class="ambient"' in html and 'aria-hidden="true"' in html
assert html.index('id="news"') < html.index('id="publications"') < html.index('id="experience"')
css = (ROOT / "index_css.css").read_text() + (ROOT / "event.css").read_text()
assert "prefers-reduced-motion" in css
for asset in re.findall(r'url\("([^"]+)"\)', css):
    assert (ROOT / asset).is_file(), f"Missing stylesheet asset: {asset}"

# Check the nine paper records against the previous committed homepage.
try:
    before = subprocess.check_output(["git", "show", "HEAD:index.html"], cwd=ROOT, text=True)
except subprocess.CalledProcessError:
    before = html
def paper_records(source):
    return re.findall(r'<div class="publication-copy">([\s\S]*?)\n                </div>', source)
normalize = lambda s: " ".join(s.split())
assert Counter(map(normalize, paper_records(before))) == Counter(map(normalize, paper_records(html))), "Publication content changed"
old_links = {a["href"] for t, a in Page(before).tags if t == "a" and a.get("href", "").startswith(("https:", "mailto:"))}
new_links = {a["href"] for t, a in page.tags if t == "a" and "href" in a}
assert old_links <= new_links, f"Existing links removed: {old_links - new_links}"
print("PASS: 9 unchanged papers; existing links retained; homepage and Event assets, navigation and anchors valid.")
