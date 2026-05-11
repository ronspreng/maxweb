#!/usr/bin/env python
"""Quick script to scrape MaxWeb offers."""

import asyncio
import logging
from src.module1_offers.maxweb_scraper import scrape_maxweb_to_csv

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

try:
    csv_path = asyncio.run(scrape_maxweb_to_csv(
        email='rspreng@rvandes.com',
        password='D@sktop1969',
        output_path='data/offers.csv',
        headless=False  # Browser window visible
    ))
    print(f'\n✓ Scraped! Saved to {csv_path}')
except Exception as e:
    print(f'\n✗ Error: {e}')
    import traceback
    traceback.print_exc()
