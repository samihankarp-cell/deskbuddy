"""Looking something up on the web without opening a tab."""
import html
import re
import urllib.parse
import urllib.request

from deskbuddy.brain.tools import Ctx, Outcome, tool

LINK = re.compile(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', re.S)
HREF = re.compile(r'href="([^"]+)"')
SNIPPET = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)
BLOCK = re.compile(r'<a[^>]*class="result__a".*?(?=<a[^>]*class="result__a"|$)', re.S)
TAGS = re.compile(r"<[^>]+>")
AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/130.0 Safari/537.36")


def _clean(fragment: str) -> str:
    return " ".join(html.unescape(TAGS.sub("", fragment)).split())


def search(query: str, limit: int = 8) -> list[dict]:
    """Search results as [{'title', 'url', 'snippet'}]. Empty if the search fails."""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
    request = urllib.request.Request(
        url, headers={"User-Agent": AGENT, "Accept-Language": "en-US,en;q=0.9"})
    try:
        page = urllib.request.urlopen(request, timeout=12).read().decode("utf-8", "replace")
    except Exception:
        return []
    results = []
    for block in BLOCK.findall(page):
        title, link = LINK.search(block), HREF.search(block[:block.find(">") + 1])
        if not title or not link:
            continue
        target = html.unescape(link.group(1))
        target = urllib.parse.parse_qs(urllib.parse.urlparse(target).query).get("uddg", [target])[0]
        if target.startswith("//"):
            target = "https:" + target
        if "duckduckgo.com/y.js" in target:  # an advert
            continue
        snippet = SNIPPET.search(block)
        results.append({"title": _clean(title.group(1)), "url": target,
                        "snippet": _clean(snippet.group(1)) if snippet else ""})
        if len(results) >= limit:
            break
    return results


@tool("web_lookup", "Look something up on the web quickly, without opening a browser tab. "
      "Returns titles, links and short descriptions.", {"query": "string: what to look up"},
      label=lambda a: f"Looking up {a.get('query', '')[:40]}", reads_only=True)
def web_lookup(ctx: Ctx, query: str) -> Outcome:
    results = search(query)
    if not results:
        return Outcome(False, "The web search returned nothing. Use browser_search instead.")
    lines = [f"- {r['title']} | {r['url']}\n  {r['snippet'][:200]}" for r in results]
    return Outcome(True, "\n".join(lines), verified=True)
