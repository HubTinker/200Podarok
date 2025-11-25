import sys
from pathlib import Path

# Ensure project root (parent of tests/) is on sys.path so local modules can be imported
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scrape_market import scrape_yandex_market_alternatives


class MockDriver:
    def __init__(self, html):
        self.page_source = html

    def get(self, url):
        # nothing to do, page_source already set
        pass

    def find_element(self, *args, **kwargs):
        # WebDriverWait calls find_element; return a truthy placeholder
        class Dummy:
            def get_attribute(self, name):
                return ""

        return Dummy()


def main():
    try:
        with open("debug_page.html", "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print(
            "debug_page.html not found in project root — run the scraper once to generate it."
        )
        return

    driver = MockDriver(html)
    alts = scrape_yandex_market_alternatives(driver, "test query", num_results=8)
    print(f"Got {len(alts)} alternatives:")
    for i, a in enumerate(alts):
        print(
            i + 1,
            (a.get("name") or "")[:80],
            "|",
            a.get("price"),
            "|",
            a.get("purchaseUrl"),
        )

    # exit non-zero if nothing found so test harnesses will notice
    if len(alts) == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
