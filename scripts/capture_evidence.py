
import os
import sys
import time
from playwright.sync_api import sync_playwright

EVIDENCE_PATH = "report.html"
DASHBOARD_SHOT = "assets/dashboard_evidence.png"
LOG_SHOT = "assets/log_evidence.png"

def capture():
    if not os.path.exists(EVIDENCE_PATH):
        print(f"CRITICAL ERROR: Report file not found at {EVIDENCE_PATH}")
        sys.exit(1)

    # Ensure assets directory exists
    os.makedirs("assets", exist_ok=True)
    
    # Get absolute path for file URL
    abs_path = os.path.abspath(EVIDENCE_PATH)
    file_url = f"file:///{abs_path.replace(os.sep, '/')}"

    print(f"Loading report from: {file_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        
        try:
            page.goto(file_url)
            
            # WAIT for the canvas to verify JS execution
            print("Waiting for #driftChart...")
            try:
                 page.wait_for_selector("canvas#driftChart", state="visible", timeout=5000)
                 print("Chart detected! JS executed successfully.")
            except Exception as e:
                print("CRITICAL ERROR: Drift Chart did not render in 5 seconds.")
                raise e

            # Full page screenshot
            print(f"Capturing dashboard to {DASHBOARD_SHOT}...")
            page.screenshot(path=DASHBOARD_SHOT, full_page=True)

            # Element screenshot
            print(f"Capturing logs to {LOG_SHOT}...")
            log_table = page.locator("#driftLog")
            if log_table.is_visible():
                log_table.screenshot(path=LOG_SHOT)
            else:
                 print("WARNING: Drift Log table not visible/found.")

        except Exception as e:
            print(f"Capture failed: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    capture()
