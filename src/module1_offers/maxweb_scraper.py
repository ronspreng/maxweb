"""
MaxWeb dashboard scraper for offers data.

Usage:
    from src.module1_offers.maxweb_scraper import MaxWebScraper

    scraper = MaxWebScraper(email="...", password="...")
    offers_csv = scraper.scrape_offers()
"""

import asyncio
import csv
import json
import logging
import time
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class MaxWebScraper:
    """Scrape MaxWeb offers from affiliate dashboard."""

    BASE_URL = "https://affiliates-backoffice.maxweb.com/app"

    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = False,
        timeout_ms: int = 30000,
    ):
        """
        Initialize scraper with credentials.

        Args:
            email: MaxWeb account email
            password: MaxWeb account password
            headless: Run browser headless or visible (useful for debugging)
            timeout_ms: Page load timeout in milliseconds
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def scrape_offers(self) -> list[dict]:
        """
        Scrape offers from MaxWeb dashboard.

        Returns:
            List of offers as dicts with keys:
            - id / offer_id
            - name / offer_name
            - payout / commission
            - epc / earnings_per_click
            - refund_rate / refund
            - competition (inferred)
            - geo (inferred)
        """
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=self.headless)
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(self.timeout_ms)

            try:
                # Step 1: Login
                logger.info("Logging in...")
                await self._login()

                # Step 2: Navigate to campaigns/offers page
                logger.info("Navigating to offers page...")
                await self._navigate_to_offers()

                # Step 3: Wait for table to load
                await self.page.wait_for_selector("table, [role='table'], .offers-table", timeout=10000)
                await asyncio.sleep(2)  # Extra wait for dynamic content

                # Step 4: Extract offers
                logger.info("Extracting offers...")
                offers = await self._extract_offers_from_page()

                logger.info(f"Scraped {len(offers)} offers")
                return offers

            finally:
                await self.browser.close()

    async def _login(self) -> None:
        """Login to MaxWeb."""
        logger.info(f"Navigating to {self.BASE_URL}...")
        await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)  # Wait for JS to render

        # Find email input (try multiple selectors)
        email_input = None
        for selector in [
            "input[type='email']",
            "input[name*='email' i]",
            "input[placeholder*='email' i]",
            "input[id*='email' i]",
            "input",  # Last resort: first input
        ]:
            try:
                email_input = await self.page.query_selector(selector)
                if email_input:
                    logger.info(f"Found email input with selector: {selector}")
                    break
            except Exception:
                continue

        if not email_input:
            logger.error("Could not find email input. Page HTML preview:")
            html = await self.page.content()
            print(html[:2000])  # Print first 2000 chars for debugging
            raise ValueError("Login form not found")

        # Fill email
        await email_input.fill(self.email)
        logger.info(f"Filled email: {self.email}")
        await asyncio.sleep(1)

        # Find password input
        password_input = None
        for selector in [
            "input[type='password']",
            "input[name*='password' i]",
            "input[placeholder*='password' i]",
        ]:
            try:
                password_input = await self.page.query_selector(selector)
                if password_input:
                    logger.info(f"Found password input with selector: {selector}")
                    break
            except Exception:
                continue

        if password_input:
            await password_input.fill(self.password)
            logger.info("Password filled")
            await asyncio.sleep(1)

        # Find and click login button
        login_button = None
        for selector in [
            "button:has-text('Login')",
            "button:has-text('Sign in')",
            "button:has-text('Inloggen')",
            "button[type='submit']",
            "button",  # First button
        ]:
            try:
                login_button = await self.page.query_selector(selector)
                if login_button:
                    logger.info(f"Found login button with selector: {selector}")
                    await login_button.click()
                    break
            except Exception:
                continue

        if not login_button:
            logger.error("Could not find login button")

        logger.info("Waiting for post-login navigation...")
        try:
            await self.page.wait_for_url("**/app/**", timeout=15000)
        except Exception as e:
            logger.warning(f"URL redirect timeout: {e}, continuing anyway")

        await asyncio.sleep(4)  # Extra wait for page to fully load
        logger.info("Login completed")

    async def _navigate_to_offers(self) -> None:
        """Navigate to offers/campaigns page."""
        # Try multiple possible URLs/navigation patterns
        offers_urls = [
            f"{self.BASE_URL}#campaigns",
            f"{self.BASE_URL}#offers",
            f"{self.BASE_URL}#products",
            f"{self.BASE_URL}",
        ]

        for url in offers_urls:
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=5000)
                await asyncio.sleep(1)

                # Check if page has table/offers data
                has_table = await self.page.query_selector("table, [role='table'], .offers-table")
                if has_table:
                    logger.info(f"Found offers table at {url}")
                    return

            except Exception as e:
                logger.debug(f"URL {url} failed: {e}")
                continue

        logger.warning("Could not find offers table, trying current page anyway")

    async def _extract_offers_from_page(self) -> list[dict]:
        """Extract offers from current page."""
        offers = []

        # Try multiple extraction strategies
        # Strategy 1: Look for visible table rows
        try:
            rows = await self.page.query_selector_all("table tbody tr, [role='row']")

            for row in rows[:50]:  # Limit to first 50 for testing
                try:
                    cells = await row.query_selector_all("td, [role='cell']")
                    if len(cells) < 3:
                        continue

                    cell_texts = []
                    for cell in cells:
                        text = await cell.text_content()
                        cell_texts.append(text.strip() if text else "")

                    # Try to parse based on position
                    offer = self._parse_row(cell_texts)
                    if offer:
                        offers.append(offer)
                        logger.debug(f"Extracted: {offer.get('name', 'Unknown')}")

                except Exception as e:
                    logger.debug(f"Failed to parse row: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")

        # Strategy 2: Extract JSON from page data
        if not offers:
            try:
                json_data = await self.page.evaluate(
                    """() => {
                    // Look for React/Vue data
                    if (window.__data) return window.__data;
                    if (window.__INITIAL_STATE__) return window.__INITIAL_STATE__;

                    // Look in DOM for data attributes
                    const scripts = document.querySelectorAll('script[type="application/json"]');
                    for (let s of scripts) {
                        try {
                            return JSON.parse(s.textContent);
                        } catch (e) {}
                    }
                    return null;
                }"""
                )
                if json_data:
                    logger.info("Found JSON data in page")
                    offers = self._parse_json_data(json_data)

            except Exception as e:
                logger.debug(f"JSON extraction failed: {e}")

        return offers

    def _parse_row(self, cells: list[str]) -> Optional[dict]:
        """
        Parse a table row into an offer dict.

        Attempts to identify columns like: ID, Name, Payout, EPC, Refund Rate, etc.
        """
        if len(cells) < 3:
            return None

        # Try to find numeric columns (likely payout, epc, refund)
        offer = {}

        # Heuristic: first cell often ID/name, look for money values ($, numbers)
        for i, cell in enumerate(cells):
            cell_clean = cell.strip()

            # Skip empty cells
            if not cell_clean or cell_clean == "-":
                continue

            # ID / Name (usually first, alphanumeric)
            if not offer.get("id") and (i == 0 or i == 1):
                if not any(c in cell_clean for c in "$%€"):
                    offer["id"] = cell_clean[:50]
                    if not offer.get("name"):
                        offer["name"] = cell_clean

            # Payout (currency value, $50-200 range typical)
            if not offer.get("payout"):
                if "$" in cell_clean or "€" in cell_clean:
                    try:
                        value = float(cell_clean.replace("$", "").replace("€", "").strip())
                        if 20 <= value <= 500:  # Reasonable payout range
                            offer["payout"] = value
                            continue
                    except ValueError:
                        pass

            # EPC (small decimal, 0.5-5 typical)
            if not offer.get("epc"):
                try:
                    value = float(cell_clean.replace("$", "").strip())
                    if 0.1 <= value <= 10.0:  # Reasonable EPC range
                        offer["epc"] = value
                        continue
                except ValueError:
                    pass

            # Refund rate (percentage, 0-50%)
            if not offer.get("refund_rate"):
                if "%" in cell_clean:
                    try:
                        value = float(cell_clean.replace("%", "").strip())
                        if 0 <= value <= 100:
                            offer["refund_rate"] = value
                            continue
                    except ValueError:
                        pass

        # Require at least ID and payout to be valid
        if offer.get("id") and offer.get("payout"):
            return offer

        return None

    def _parse_json_data(self, data: dict) -> list[dict]:
        """Parse JSON data structure from page."""
        offers = []

        # Recursive search for offers array
        def find_offers(obj, depth=0):
            if depth > 5:  # Limit recursion
                return

            if isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        # Check if this looks like an offer
                        if any(k in item for k in ["payout", "epc", "refund_rate", "offer_id"]):
                            offers.append(item)
                        find_offers(item, depth + 1)

            elif isinstance(obj, dict):
                for v in obj.values():
                    find_offers(v, depth + 1)

        find_offers(data)
        return offers


async def scrape_maxweb_to_csv(
    email: str,
    password: str,
    output_path: str = "data/offers.csv",
    headless: bool = True,
) -> str:
    """
    Scrape MaxWeb offers and save to CSV.

    Args:
        email: MaxWeb account email
        password: MaxWeb account password
        output_path: Where to save CSV
        headless: Run browser visible or headless

    Returns:
        Path to saved CSV file
    """
    scraper = MaxWebScraper(email=email, password=password, headless=headless)
    offers = await scraper.scrape_offers()

    # Normalize columns
    csv_offers = []
    for offer in offers:
        csv_offers.append(
            {
                "id": offer.get("id", f"offer-{len(csv_offers)}"),
                "name": offer.get("name", "Unknown"),
                "payout": offer.get("payout", 0),
                "epc": offer.get("epc", 0),
                "refund_rate": offer.get("refund_rate", 0),
                "competition": offer.get("competition", "medium"),
                "geo": offer.get("geo", "US"),
            }
        )

    # Write CSV
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "name", "payout", "epc", "refund_rate", "competition", "geo"]
        )
        writer.writeheader()
        writer.writerows(csv_offers)

    logger.info(f"Saved {len(csv_offers)} offers to {output_path}")
    return str(output_path)


if __name__ == "__main__":
    # Example usage
    import os

    logging.basicConfig(level=logging.INFO)

    email = os.getenv("MAXWEB_EMAIL")
    password = os.getenv("MAXWEB_PASSWORD")

    if not email or not password:
        print("Set MAXWEB_EMAIL and MAXWEB_PASSWORD env vars")
        exit(1)

    csv_path = asyncio.run(scrape_maxweb_to_csv(email, password, headless=False))
    print(f"✓ Saved to {csv_path}")
