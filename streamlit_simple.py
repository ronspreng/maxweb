"""Streamlit GUI for MaxWeb Affiliate System."""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.module1_offers.importer import CSVImporter
from src.module1_offers.ranker import OfferRanker
from src.module2_competitive.analyzer import PatternAnalyzer
from src.module2_competitive.models import NativeAd
from src.module2_competitive.reporter import IntelReporter

# Load .env at startup
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Force reload ANTHROPIC_API_KEY directly from .env file
def _load_api_key():
    """Read API key directly from .env file."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    os.environ["ANTHROPIC_API_KEY"] = key
                    return key
    return None

_load_api_key()

st.set_page_config(page_title="MaxWeb System", layout="wide")

# Initialize session state (global, runs every rerun)
if "selected_offers" not in st.session_state:
    st.session_state.selected_offers = []

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Module 1: Offers", "🔍 Module 2: Intel", "✍️ Module 3: Creatives", "📝 Module 4: Pre-sell"])

# ===== MODULE 1 =====
with tab1:
    st.header("Module 1: Offer Ranking")

    uploaded_file = st.file_uploader("Upload MaxWeb CSV", type="csv")
    budget = st.number_input("Budget ($)", value=200.0, min_value=50.0)

    if uploaded_file:
        temp_path = Path("temp_upload.csv")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        if st.button("Rank Offers", key="rank_btn"):
            with st.spinner("Ranking..."):
                offers = CSVImporter.import_csv(temp_path)
                ranker = OfferRanker(budget_usd=budget)
                st.session_state.ranked_offers = ranker.rank_offers(offers)
                # Reset checkbox states and selected offers for new ranking
                st.session_state.selected_offers = []
                for i in range(20):
                    st.session_state[f"offer_check_{i}"] = False

        # Display results if we have ranked offers (persists across checkbox interactions)
        if "ranked_offers" in st.session_state and st.session_state.ranked_offers:
            ranked = st.session_state.ranked_offers

            st.subheader("Top Ranked Offers — Select for Module 2")

            # Display interactive table with checkboxes
            st.write("_Check offers to send to Module 2 for competitive intelligence_")

            # Create columns for header
            col_check, col_rank, col_name, col_payout, col_epc, col_score = st.columns([0.8, 0.5, 2.5, 1, 1, 1])
            with col_check:
                st.write("**✓**")
            with col_rank:
                st.write("**Rank**")
            with col_name:
                st.write("**Offer**")
            with col_payout:
                st.write("**Payout**")
            with col_epc:
                st.write("**EPC**")
            with col_score:
                st.write("**Score**")

            st.divider()

            # Display rows with checkboxes
            for idx, item in enumerate(ranked[:20]):
                col_check, col_rank, col_name, col_payout, col_epc, col_score = st.columns([0.8, 0.5, 2.5, 1, 1, 1])

                checkbox_key = f"offer_check_{idx}"

                with col_check:
                    # Initialize checkbox state on first load
                    if checkbox_key not in st.session_state:
                        st.session_state[checkbox_key] = item.offer.name in st.session_state.selected_offers

                    # Render checkbox - Streamlit auto-stores value in session_state
                    st.checkbox(
                        "",
                        key=checkbox_key,
                        label_visibility="collapsed"
                    )

                with col_rank:
                    st.write(str(item.rank))
                with col_name:
                    st.write(item.offer.name)
                with col_payout:
                    st.write(f"${item.offer.payout:.0f}")
                with col_epc:
                    st.write(f"${item.offer.epc:.2f}")
                with col_score:
                    st.write(f"{item.score.overall_score:.3f}")

            # Sync checkbox states with selected_offers list
            st.session_state.selected_offers = []
            for idx, item in enumerate(ranked[:20]):
                checkbox_key = f"offer_check_{idx}"
                if st.session_state.get(checkbox_key, False):
                    st.session_state.selected_offers.append(item.offer.name)

            # Summary section
            st.write("---")
            st.subheader("Sending to Module 2")
            if st.session_state.selected_offers:
                st.success(f"✓ **{len(st.session_state.selected_offers)} offers selected:**")
                for name in st.session_state.selected_offers:
                    st.write(f"  • {name}")
            else:
                st.info("Select offers above to send to Module 2")

        temp_path.unlink(missing_ok=True)
    else:
        st.info("Upload CSV to start")


# ===== MODULE 2 =====
with tab2:
    st.header("Module 2: Competitive Intelligence")
    st.write("Scrape native ads and analyze winning patterns with Claude")

    # Show selected offers from Module 1
    if "selected_offers" in st.session_state and st.session_state.selected_offers:
        st.info(f"📌 From Module 1: {', '.join(st.session_state.selected_offers)}")
    else:
        st.warning("💡 Go to Module 1 to select offers first")

    col1, col2 = st.columns(2)
    with col1:
        niche = st.selectbox("Niche", ["brain-health", "lung-health", "mens-health"], key="niche_select")
    with col2:
        sources = st.multiselect(
            "Sources",
            ["reddit", "amazon", "quora", "dailymail", "msn", "yahoo"],
            default=["reddit", "amazon", "quora"],
            key="sources_select",
        )

    skip_analysis = st.checkbox("Skip Claude analysis (scrape-only)", key="skip_analysis")

    if st.button("Start Scraping", type="primary", key="scrape_btn"):
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
            with st.spinner("Running scraper (5-15 min)..."):
                # Pass environment variables including API key to subprocess
                env = os.environ.copy()
                api_key = env.get('ANTHROPIC_API_KEY', 'NOT_FOUND')
                st.write(f"[DEBUG] API Key in Streamlit env: {api_key[:30]}... (len={len(api_key)})")

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
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
                        report_file = sorted(Path("output/reports").glob(f"competitive_intel_*_{niche}.md"))
                        if report_file:
                            with open(report_file[-1], encoding="utf-8") as f:
                                report_content = f.read()
                            st.markdown(report_content)
                            with open(report_file[-1], "r") as f:
                                st.download_button(
                                    label="Download Report",
                                    data=f.read(),
                                    file_name=report_file[-1].name,
                                    mime="text/markdown",
                                )
                else:
                    st.error(f"Scraper failed (exit code {proc.returncode})")

        except Exception as e:
            st.error(f"Error: {e}")

    # Re-analyze button
    if st.button("Re-analyze (cache)", key="reanalyze_btn"):
        cache_path = Path(f"data/competitive/{niche}_ads.json")
        if not cache_path.exists():
            st.error(f"No cache for {niche}")
        else:
            with st.spinner("Analyzing with Claude..."):
                with open(cache_path) as f:
                    ads = [NativeAd(**item) for item in json.load(f)]

                analyzer = PatternAnalyzer()
                report = analyzer.analyze(ads, niche)
                IntelReporter.save(report, Path("output/reports"))

                st.success("✓ Done!")
                st.markdown(IntelReporter.to_markdown(report))

                report_file = sorted(Path("output/reports").glob(f"competitive_intel_*_{niche}.md"))[-1]
                with open(report_file) as f:
                    st.download_button(
                        label="Download Report",
                        data=f.read(),
                        file_name=report_file.name,
                        mime="text/markdown",
                    )


# ===== MODULE 3 =====
with tab3:
    st.header("Module 3: Creative Generator")
    st.write("Generate native ad headlines + descriptions for A/B testing")

    col1, col2 = st.columns(2)

    with col1:
        if "selected_offers" in st.session_state and st.session_state.selected_offers:
            offer_options = st.session_state.selected_offers + ["--- Custom ---"]
            selected_offer = st.selectbox(
                "Select Offer",
                offer_options,
                key="creative_offer_select"
            )
            if selected_offer == "--- Custom ---":
                offer_name = st.text_input("Enter offer name", key="creative_offer_custom")
            else:
                offer_name = selected_offer
        else:
            st.warning("💡 Go to Module 1 and select offers first")
            offer_name = st.text_input("Enter offer name", key="creative_offer_manual")

    with col2:
        niche = st.selectbox(
            "Niche",
            ["brain-health", "lung-health", "mens-health"],
            key="creative_niche_select"
        )

    # VSL angle input
    vsl_angle = st.text_input(
        "VSL Angle (optional)",
        placeholder="e.g. 'Doctor reveals secret formula'",
        key="creative_vsl_angle",
        help="Leave blank or enter the main angle from the MaxWeb VSL to align ads with it"
    )

    # Check if Module 2 report exists
    reports = list(Path("output/reports").glob(f"competitive_intel_*_{niche}.json"))
    report_status = "✓ Patterns loaded" if reports else "⚠ Generic mode"
    st.write(f"Report status: {report_status}")

    if st.button("Generate Creatives", type="primary", key="creative_generate_btn"):
        if not offer_name:
            st.error("Please enter offer name")
        else:
            with st.spinner("Generating creatives with Claude..."):
                try:
                    from src.module3_creative.generator import CreativeGenerator

                    generator = CreativeGenerator()
                    creative_set = generator.generate(
                        offer_name=offer_name,
                        niche=niche,
                        auto_load_report=True,
                        vsl_angle=vsl_angle if vsl_angle else None
                    )

                    # Display creatives in a table
                    st.subheader(f"Generated Creatives ({len(creative_set.creatives)} variations)")

                    # Create dataframe for display
                    df_data = []
                    for idx, creative in enumerate(creative_set.creatives):
                        df_data.append({
                            "Hook Type": creative.hook_type.capitalize(),
                            "Headline": creative.headline,
                            "Description": creative.description,
                        })

                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)

                    # CSV export
                    csv_content = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv_content,
                        file_name=f"creatives_{niche}_{offer_name.lower().replace(' ', '')}_{creative_set.generated_at.strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        key="creative_download_csv"
                    )

                    if creative_set.report_used:
                        st.success("✓ Generated using Module 2 patterns")
                    else:
                        st.info("Generated without Module 2 patterns")

                except Exception as e:
                    st.error(f"Error generating creatives: {e}")
                    logger.error(f"Creative generation error: {e}")


# ===== MODULE 4 =====
with tab4:
    st.header("Module 4: Pre-sell Page Generator")
    st.write("Generate advertorial HTML pages using winning patterns from Module 2")

    col1, col2 = st.columns(2)

    with col1:
        # Offer selection
        if "selected_offers" in st.session_state and st.session_state.selected_offers:
            offer_options = st.session_state.selected_offers + ["--- Custom ---"]
            selected_offer = st.selectbox(
                "Select Offer",
                offer_options,
                key="presell_offer_select"
            )
            if selected_offer == "--- Custom ---":
                offer_name = st.text_input("Enter offer name", key="presell_offer_custom")
            else:
                offer_name = selected_offer
        else:
            st.warning("💡 Go to Module 1 and select offers first")
            offer_name = st.text_input("Enter offer name", key="presell_offer_manual")

    with col2:
        offer_url = st.text_input(
            "Affiliate URL",
            placeholder="https://maxweb.com/offer/...",
            key="presell_url"
        )
        maxweb_url = st.text_input(
            "MaxWeb VSL URL (for angle detection)",
            placeholder="https://maxweb.com/offer/...",
            key="presell_maxweb_url",
            help="Leave blank to auto-use affiliate URL or enter MaxWeb VSL URL directly"
        )

    col3, col4 = st.columns(2)
    with col3:
        niche = st.selectbox(
            "Niche",
            ["brain-health", "lung-health", "mens-health"],
            key="presell_niche_select"
        )

    with col4:
        # Check if Module 2 report exists
        report_path = Path(f"output/reports/competitive_intel_*_{niche}.md")
        reports = list(Path("output/reports").glob(f"competitive_intel_*_{niche}.md"))
        report_status = "✓ Report found" if reports else "⚠ No report (generic copy)"
        st.write(report_status)

    if st.button("Generate Advertorial", type="primary", key="presell_generate_btn"):
        if not offer_name or not offer_url:
            st.error("Please fill in offer name and URL")
        else:
            with st.spinner("Generating advertorial with Claude..."):
                try:
                    from src.module4_presell.generator import AdvertorialGenerator
                    from src.module4_presell.builder import AdvertorialBuilder
                    from src.module4_presell.maxweb_scraper import MaxWebScraper

                    # Detect VSL angle from MaxWeb if URL provided
                    vsl_angle = None
                    vsl_info = None
                    if maxweb_url:
                        with st.spinner("Detecting VSL angle from MaxWeb..."):
                            scraper = MaxWebScraper()
                            vsl_info = scraper.scrape_offer(maxweb_url)
                            if vsl_info:
                                vsl_angle = vsl_info["angle"]
                                st.info(f"📌 Detected angle: {vsl_angle} ({vsl_info['hook_type']} hook)")
                            else:
                                st.warning("Could not detect angle from MaxWeb URL")

                    generator = AdvertorialGenerator()
                    # Auto-load report for the niche (generator will try to load from JSON)
                    page = generator.generate(
                        offer_name=offer_name,
                        offer_category="supplement",
                        niche=niche,
                        offer_url=offer_url,
                        report=None,  # Will auto-load from JSON if available
                        auto_load_report=True,
                        vsl_angle=vsl_angle
                    )

                    # Build and display HTML
                    html_content = AdvertorialBuilder.build(page)
                    output_dir = Path("output/presell_pages")

                    # Save file
                    output_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"presell_{niche}_{offer_name.lower().replace(' ', '')}_{page.generated_at.strftime('%Y%m%d')}.html"
                    filepath = output_dir / filename

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(html_content)

                    st.success("✓ Advertorial generated!")

                    # Preview
                    st.subheader("Preview")
                    st.components.v1.html(html_content, height=700, scrolling=True)

                    # Download button
                    st.download_button(
                        label="Download HTML",
                        data=html_content,
                        file_name=filename,
                        mime="text/html",
                        key="presell_download_btn"
                    )

                except Exception as e:
                    st.error(f"Error generating advertorial: {e}")
                    logger.error(f"Presell generation error: {e}")
