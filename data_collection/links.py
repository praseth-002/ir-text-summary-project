# import os, hashlib
# from bs4 import BeautifulSoup

# url = "https://en.wikivoyage.org/wiki/Cambodia"
# path = os.path.join("raw_pages", hashlib.md5(url.encode()).hexdigest() + ".html")
# soup = BeautifulSoup(open(path, encoding="utf-8").read(), "html.parser")

# boxes = soup.select("div.mw-parser-output")
# content = max(boxes, key=lambda b: len(b.get_text().split()))

# seen = set()
# for a in content.select("a[href^='/wiki/']"):
#     href = a["href"]
#     if ":" in href or "#" in href or href in seen:   # skip special pages and section links
#         continue
#     seen.add(href)
#     print("https://en.wikivoyage.org" + href, "|", a.get_text(strip=True))

import os, hashlib
from bs4 import BeautifulSoup

url = "https://en.wikivoyage.org/wiki/Cambodia"
path = os.path.join("raw_pages", hashlib.md5(url.encode()).hexdigest() + ".html")
soup = BeautifulSoup(open(path, encoding="utf-8").read(), "html.parser")

boxes = soup.select("div.mw-parser-output")
content = max(boxes, key=lambda b: len(b.get_text().split()))

already = open("skeleton.py", encoding="utf-8").read()   # so we can hide pages you already have

seen = set()
prefix = "https://en.wikivoyage.org/wiki/"
for a in content.find_all("a", href=True):
    href = a["href"]
    if not href.startswith(prefix):                  # skips external sites and edit links
        continue
    name = href[len(prefix):]
    if ":" in name or "#" in name or "?" in name:    # skips File:, Special:, section links
        continue
    if href in seen or href in already:
        continue
    seen.add(href)
    print(href, "|", a.get_text(strip=True))


# all_links = content.find_all("a", href=True)
# print("links inside the article box:", len(all_links))
# print("links on the whole page:", len(soup.find_all("a", href=True)))

# print("\nfirst 25 hrefs in the article box:")
# for a in all_links[:25]:
#     print("  ", a["href"], "|", a.get_text(strip=True))