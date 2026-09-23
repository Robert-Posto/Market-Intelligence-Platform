from playwright.sync_api import sync_playwright

urls = ["https://example.com/", "https://www.google.com/", "https://curs.bnr.ro/nbrfxrates.xml", "https://www.bnr.ro/"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    for url in urls:
        try:
            resp = page.goto(url, wait_until="load", timeout=20000)
            print(url, "->", resp.status if resp else None)
        except Exception as e:
            print(url, "-> ERROR:", str(e)[:120])
    browser.close()
