# login_and_save.py
from playwright.sync_api import sync_playwright
import pathlib

pathlib.Path(".secrets").mkdir(exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False, slow_mo=50)
    ctx = browser.new_context()  # fresh context
    page = ctx.new_page()
    page.goto("https://resourcebooker.rmit.edu.au/app/booking-types")
    page.wait_for_load_state("networkidle")

    print("A browser window opened. Log in normally.")
    input("When you’re fully in (you can see booking types), press ENTER here... ")

    # Save cookies/localStorage for reuse
    ctx.storage_state(path=".secrets/storage_state.json")
    page.screenshot(path="logged_in.png", full_page=True)
    print("Saved session to .secrets/storage_state.json and screenshot to logged_in.png")
    browser.close()
