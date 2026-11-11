import json, re, time, random, os, hashlib
import requests
from bs4 import BeautifulSoup

# Wikimedia asks scrapers to identify themselves with a way to contact you.
HEADERS = {"User-Agent": "information-retrieval-student-project/1.0 (course project; contact: prasethsokha@gmail.com)"}

urls = [
    # first batch: main cities
    "https://en.wikivoyage.org/wiki/Siem_Reap",
    "https://en.wikivoyage.org/wiki/Phnom_Penh",
    "https://en.wikivoyage.org/wiki/Kampot",
    "https://en.wikivoyage.org/wiki/Battambang",
    # second batch: country page, Angkor, more cities
    "https://en.wikivoyage.org/wiki/Cambodia",
    "https://en.wikivoyage.org/wiki/Angkor",
    "https://en.wikivoyage.org/wiki/Sihanoukville",
    "https://en.wikivoyage.org/wiki/Kep",
    "https://en.wikivoyage.org/wiki/Kratie",
    "https://en.wikivoyage.org/wiki/Kampong_Cham",
    "https://en.wikivoyage.org/wiki/Koh_Kong",
    "https://en.wikivoyage.org/wiki/Mondulkiri",
    # third batch: provinces and towns
    "https://en.wikivoyage.org/wiki/Pailin",
    "https://en.wikivoyage.org/wiki/Pursat",
    "https://en.wikivoyage.org/wiki/Anlong_Veng",
    "https://en.wikivoyage.org/wiki/Sisophon",
    "https://en.wikivoyage.org/wiki/Poipet",
    "https://en.wikivoyage.org/wiki/Preah_Vihear",
    "https://en.wikivoyage.org/wiki/Kompong_Thom",
    "https://en.wikivoyage.org/wiki/Banlung",
    "https://en.wikivoyage.org/wiki/Stung_Treng",
    # fourth batch: islands, sights, topic pages
    "https://en.wikivoyage.org/wiki/Koh_Rong",
    "https://en.wikivoyage.org/wiki/Koh_Rung_Sanloem",
    "https://en.wikivoyage.org/wiki/Kampong_Chhnang",
    "https://en.wikivoyage.org/wiki/Banteay_Chhmar",
    "https://en.wikivoyage.org/wiki/Koh_Ker",
    "https://en.wikivoyage.org/wiki/Bokor_National_Park",
    "https://en.wikivoyage.org/wiki/Tonle_Sap_Lake",
    "https://en.wikivoyage.org/wiki/Cambodian_cuisine",
    "https://en.wikivoyage.org/wiki/Bangkok_to_Ho_Chi_Minh_City_overland",
]

CACHE_DIR = "raw_pages"
os.makedirs(CACHE_DIR, exist_ok=True)


# ---------------------------------------------------------------
# Step 1: download (with a local cache so each page is fetched once)
# ---------------------------------------------------------------
def get_html(url):
    """Return the page HTML, downloading it only if we don't already have a saved copy."""
    path = os.path.join(CACHE_DIR, hashlib.md5(url.encode()).hexdigest() + ".html")
    if os.path.exists(path):                       # already downloaded, so no request
        with open(path, encoding="utf-8") as f:
            return f.read()
    response = requests.get(url, headers=HEADERS, timeout=15)
    time.sleep(3)                                  # wait after every real request, even failed ones
    if response.status_code == 429:
        raise SystemExit("Rate limited (429). Stop now and try again much later.")
    response.raise_for_status()                    # other errors (404 etc.) skip just this page
    with open(path, "w", encoding="utf-8") as f:
        f.write(response.text)
    return response.text


# ---------------------------------------------------------------
# Step 2: parse the page into (section, line) pairs
# ---------------------------------------------------------------
def fetch_page(url):
    """Parse one page and return (title, items) where items is a list of (section, line)."""
    soup = BeautifulSoup(get_html(url), "html.parser")

    # Title: try the real article heading first, then fall back to the <title> tag
    h1 = soup.select_one("h1#firstHeading")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(" ", strip=True)
    else:
        title = soup.title.get_text(strip=True).split(" – ")[0]

    # Content: there are several boxes, so pick the one with the most text
    boxes = soup.select("div.mw-parser-output")
    content = max(boxes, key=lambda b: len(b.get_text().split()))

    for junk in content.select("script, style, table, sup, .mw-editsection, .navbox, .thumb, .toc, .noprint"):
        junk.decompose()

    items = []                                     # list of (section, line)
    section, sub = "Overview", ""
    for el in content.find_all(["h2", "h3", "p", "li"]):
        text = el.get_text(" ", strip=True)
        if el.name == "h2":
            section, sub = text, ""
        elif el.name == "h3":
            sub = text
        else:
            items.append((f"{section} – {sub}" if sub else section, text))
    return title, items


# ---------------------------------------------------------------
# Step 3: clean
# ---------------------------------------------------------------
def clean_items(items):
    """Tidy each line, strip noise, and keep its section label."""
    cleaned = []
    for section, line in items:
        line = re.sub(r"\[\s*\d+\s*\]", "", line)                       # citation marks like [3]
        line = re.sub(r"\[edit\]", "", line)                            # leftover [edit] tags
        line = re.sub(r"\(\s*updated [A-Za-z]+ \d{4}\s*\)", "", line)   # ( updated Sep 2016 )
        line = re.sub(r"☏\s*\+?[\d\s\-]+", "", line)                    # phone numbers
        line = re.sub(r"\S+@\S+\.\S+", "", line)                        # email addresses
        line = re.sub(r"(\s*,){2,}", ",", line)                         # commas left behind
        line = re.sub(r"\s+", " ", line).strip()
        if len(line.split()) >= 4:                                      # drop menu-like fragments
            cleaned.append((section, line))
    return cleaned


def drop_nested_duplicates(items):
    """Nested bullets get read twice (inside the parent and on their own).
    If a line is fully contained in another line of the same section, drop the shorter one."""
    by_section = {}
    for section, line in items:
        by_section.setdefault(section, []).append(line)
    kept = []
    for section, line in items:
        contained = any(line != other and line in other for other in by_section[section])
        if not contained:
            kept.append((section, line))
    return kept


# ---------------------------------------------------------------
# Step 4: chunk (whole lines only, one section at a time)
# ---------------------------------------------------------------
def chunk_lines(lines, size=150):
    """Pack whole lines into chunks of about `size` words. Never cut a line in the middle."""
    chunks, current, count = [], [], 0
    for line in lines:
        current.append(line)
        count += len(line.split())
        if count >= size:                              # chunk is full, so close it
            chunks.append(" ".join(current))
            current, count = [], 0
    if current:                                        # leftover lines at the end of the section
        if count >= 40 or not chunks:
            chunks.append(" ".join(current))
        else:
            chunks[-1] += " " + " ".join(current)      # too short alone, so attach to the last chunk
    return chunks


def chunk_items(items, title, size=150):
    """Chunk each section separately, so a chunk never mixes two sections.
    Each chunk starts with 'Page - Section.' so it names its own topic."""
    groups = {}
    for section, line in items:
        groups.setdefault(section, []).append(line)
    chunks = []
    for section, lines in groups.items():
        for chunk in chunk_lines(lines, size):
            chunks.append((section, f"{title} – {section}. {chunk}"))
    return chunks


# ---------------------------------------------------------------
# Step 5: build and save the corpus
# ---------------------------------------------------------------
def build_corpus(url_list):
    corpus = {}                                    # {chunk_id: {url, title, section, text}}
    seen_titles = set()
    for url in url_list:
        print("Fetching", url)
        try:
            title, items = fetch_page(url)
        except Exception as e:
            print("  SKIPPED:", e)
            continue
        if title in seen_titles:                   # redirects can point at a page we already have
            print("  SKIPPED duplicate page:", title)
            continue
        seen_titles.add(title)

        items = drop_nested_duplicates(clean_items(items))
        slug = url.split("/wiki/")[-1].lower()
        page_chunks = chunk_items(items, title)
        print(f"  {title}: {len(page_chunks)} chunks")
        for n, (section, chunk) in enumerate(page_chunks, start=1):
            corpus[f"{slug}_{n:02d}"] = {"url": url, "title": title, "section": section, "text": chunk}
    return corpus, seen_titles


def main():
    corpus, seen_titles = build_corpus(urls)

    # Check BEFORE saving, so a broken run never overwrites a good corpus.json
    if not corpus:
        raise SystemExit("No chunks were created. Check fetch_page and clean_items.")

    with open("corpus.json", "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    lengths = [len(c["text"].split()) for c in corpus.values()]
    print(f"\n{len(corpus)} chunks from {len(seen_titles)} pages, "
          f"average {sum(lengths) / len(lengths):.0f} words each")

    # Eyeball test: three random chunks
    for cid in random.sample(list(corpus), min(3, len(corpus))):
        print(f"\n--- {cid} ---\n{corpus[cid]['text']}")


if __name__ == "__main__":
    main()
