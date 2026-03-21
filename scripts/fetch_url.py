import sys
import time
import cloudscraper

url = sys.argv[1]
out = sys.argv[2]

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "darwin", "mobile": False}
)

for attempt in range(1, 4):
    try:
        r = scraper.get(url, timeout=45)
        r.raise_for_status()
        with open(out, "wb") as f:
            f.write(r.content)
        print("saved", out, "bytes", len(r.content))
        break
    except Exception as e:
        print("attempt", attempt, "failed:", e)
        if attempt == 3:
            raise
        time.sleep(3)
