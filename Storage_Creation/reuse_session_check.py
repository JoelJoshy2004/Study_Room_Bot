# reuse_session_check.py
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(storage_state=".secrets/storage_state.json")
    page = ctx.new_page()
    page.goto("https://resourcebooker.rmit.edu.au/app/booking-types")
    page.wait_for_load_state("networkidle")
    print("Final URL:", page.url)
    # Optional: check for a logged-in element text; tweak if needed.
    # Example:
    # assert page.locator("text=Booking Types").first.is_visible()
    browser.close()
