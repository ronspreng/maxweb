"""
MaxWeb Affiliate Decision Support System — Streamlit GUI

Run with: streamlit run streamlit_app.py
"""

import json
import logging
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.module1_offers.importer import CSVImporter
from src.module1_offers.models import RankedOffer
from src.module1_offers.ranker import OfferRanker
from src.module2_competitive.analyzer import PatternAnalyzer
from src.module2_competitive.deduplicator import AdDeduplicator
from src.module2_competitive.models import NativeAd
from src.module2_competitive.reporter import IntelReporter
from src.module2_competitive.scrapers.dailymail import DailyMailScraper
from src.module2_competitive.scrapers.msn import MSNScraper
from src.module2_competitive.scrapers.yahoo import YahooScraper

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="MaxWeb Affiliate System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path("data")
UPLOADS_DIR = DATA_DIR / "uploads"
REPORTS_DIR = Path("output/reports")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_file(uploaded_file) -> Path:
    """Save uploaded file to temp directory."""
    temp_dir = UPLOADS_DIR
    temp_path = temp_dir / uploaded_file.name
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return temp_path


def load_report_markdown(niche: str) -> str | None:
    """Try to load the most recent competitive intel report for a niche."""
    matching_files = sorted(REPORTS_DIR.glob(f"competitive_intel_*_{niche}.md"))
    if not matching_files:
        return None
    with open(matching_files[-1], encoding="utf-8") as f:
        return f.read()


def page_module1_offers() -> None:
    """Module 1: Offer Ranking."""
    st.header("📈 Module 1: Offer Ranking")
    st.write(
        "Upload your MaxWeb campaign data CSV, set a budget, and get ranked offers based on fit score."
    )

    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("Upload MaxWeb CSV", type="csv", key="csv_upload")
    with col2:
        budget = st.number_input("Campaign Budget ($)", value=200.0, min_value=50.0, max_value=10000.0)

    if uploaded_file:
        csv_path = save_uploaded_file(uploaded_file)
        st.success(f"✓ Uploaded: {uploaded_file.name}")

        top_n = st.slider("Display top N offers", 5, 50, 20)

        if st.button("🚀 Run Ranking", type="primary"):
            with st.spinner("Loading and ranking offers..."):
                try:
                    offers = CSVImporter.import_csv(csv_path)
                    st.info(f"Loaded {len(offers)} offers")

                    ranker = OfferRanker(budget_usd=budget)
                    ranked = ranker.rank_offers(offers)

                    st.success(f"✓ Ranked {len(ranked)} offers")

                    ranked_display = ranked[:top_n]
                    df_data = []
                    for item in ranked_display:
                        df_data.append(
                            {
                                "Rank": item.rank,
                                "Name": item.offer.name,
                                "Category": item.offer.category,
                                "Payout": f"${item.offer.payout:.2f}",
                                "EPC": f"${item.score.epc_score:.2f}",
                                "Refund %": f"{item.offer.refund_rate:.1f}%",
                                "Score": f"{item.score.overall_score:.3f}",
                            }
                        )

                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    with st.expander("View offer details & rationales"):
                        for item in ranked_display:
                            with st.container(border=True):
                                st.markdown(f"**#{item.rank} — {item.offer.name}**")
                                st.write(f"Category: {item.offer.category}")
                                st.write(f"Payout: ${item.offer.payout} | EPC: ${item.score.epc_score:.2f}")
                                st.markdown(f"_Rationale:_ {item.score.rationale}")

                    csv_export = df.to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv_export,
                        file_name=f"ranked_offers_{datetime.now().strftime('%Y-%m-%d')}.csv",
                        mime="text/csv",
                    )

                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("Upload a MaxWeb CSV to get started")


def page_module2_intel() -> None:
    """Module 2: Competitive Intelligence."""
    st.header("🔍 Module 2: Competitive Intelligence")
    st.write("Scrape native ads from Daily Mail, MSN, Yahoo and analyze winning patterns with Claude.")

    col1, col2 = st.columns(2)
    with col1:
        niche = st.selectbox(
            "Select Niche",
            ["brain-health", "lung-health", "mens-health"],
            help="Which niche to scrape for",
        )
    with col2:
        sources = st.multiselect(
            "Ad Sources",
            ["dailymail", "msn", "yahoo"],
            default=["dailymail", "msn", "yahoo"],
            help="Which publisher sites to scrape",
        )

    skip_analysis = st.checkbox("Skip Claude analysis (scrape-only mode)", value=False)

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        scrape_btn = st.button("🚀 Start Scraping", type="primary")
    with col2:
        reanalyze_btn = st.button("♻️ Re-analyze (cache)", help="Reanalyze existing cached ads")

    if scrape_btn:
        st.write("---")
        st.subheader("Scrape Progress")

        log_container = st.empty()
        logs = []

        sources_arg = ",".join(sources)
        cmd = [
            sys.executable,
            "-m",
            "src.module2_competitive",
            "scrape",
            "--niche",
            niche,
            "--sources",
            sources_arg,
        ]
        if skip_analysis:
            cmd.append("--skip-analysis")

        try:
            with st.spinner("Running scraper (this may take 5-15 minutes)..."):
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                for line in proc.stdout:
                    line = line.rstrip()
                    logs.append(line)
                    log_container.code("\n".join(logs[-30:]), language="log")

                proc.wait()

                if proc.returncode == 0:
                    st.success("✓ Scraping completed!")

                    if not skip_analysis:
                        st.write("---")
                        st.subheader("Report")
                        report_md = load_report_markdown(niche)
                        if report_md:
                            st.markdown(report_md)
                            report_file = sorted(REPORTS_DIR.glob(f"competitive_intel_*_{niche}.md"))[-1]
                            with open(report_file, encoding="utf-8") as f:
                                st.download_button(
                                    label="Download Report (Markdown)",
                                    data=f.read(),
                                    file_name=report_file.name,
                                    mime="text/markdown",
                                )
                        else:
                            st.warning("No report found")
                else:
                    st.error(f"Scraper exited with code {proc.returncode}")

        except Exception as e:
            st.error(f"Error: {e}")

    if reanalyze_btn:
        st.write("---")
        st.subheader("Re-analyzing with Claude...")

        try:
            cache_path = Path(f"data/competitive/{niche}_ads.json")
            if not cache_path.exists():
                st.error(f"No cached ads found for {niche}. Run scrape first.")
            else:
                with st.spinner("Analyzing with Claude..."):
                    with open(cache_path, encoding="utf-8") as f:
                        raw = json.load(f)
                    ads = [NativeAd(**item) for item in raw]

                    analyzer = PatternAnalyzer()
                    report = analyzer.analyze(ads, niche)
                    IntelReporter.save(report, REPORTS_DIR)

                    st.success("✓ Analysis complete!")

                    st.subheader("Report")
                    st.markdown(IntelReporter.to_markdown(report))

                    report_file = sorted(REPORTS_DIR.glob(f"competitive_intel_*_{niche}.md"))[-1]
                    with open(report_file, encoding="utf-8") as f:
                        st.download_button(
                            label="Download Report (Markdown)",
                            data=f.read(),
                            file_name=report_file.name,
                            mime="text/markdown",
                        )

        except Exception as e:
            st.error(f"Error: {e}")


def page_about() -> None:
    """About page."""
    st.header("About MaxWeb System")
    st.markdown("""
    **MaxWeb Affiliate Decision Support System**

    A Claude Code-powered system for solo affiliate marketers running campaigns on MaxWeb.

    ### Modules

    - **Module 1: Offer Ranking** — Rank MaxWeb offers by fit score (payout, EPC, refund rate, etc.)
    - **Module 2: Competitive Intelligence** — Scrape native ads and identify winning patterns
    - **Module 3: Creative Generation** — Generate headlines based on winning patterns (coming soon)
    - **Module 4: Presell Page Builder** — Generate HTML pre-sell pages (coming soon)
    - **Module 5: Performance Feedback** — Analyze ClickHub data and optimize campaigns (coming soon)

    ### Quick Start

    1. Upload your MaxWeb CSV to Module 1
    2. Get ranked offers
    3. Run Module 2 to scrape and analyze competing ads
    4. Use winning angles for your presell pages
    5. Track performance and iterate

    **Owner:** Ron
    **Stack:** Python 3.11+ + Claude API + SQLite
    **Built with:** Claude Code
    """)


def main() -> None:
    """Main app entry point."""
    st.sidebar.title("🎯 MaxWeb System")

    page = st.sidebar.radio(
        "Navigation",
        ["📈 Module 1: Offers", "🔍 Module 2: Intel", "ℹ️ About"],
    )

    if "Module 1" in page:
        page_module1_offers()
    elif "Module 2" in page:
        page_module2_intel()
    else:
        page_about()


if __name__ == "__main__":
    main()
