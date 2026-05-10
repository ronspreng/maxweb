"""Streamlit GUI for MaxWeb Affiliate System — Logical workflow."""
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
from src.module4_presell.maxweb_detector import MaxWebDetector
from src.module2_competitive.analyzer import PatternAnalyzer
from src.module2_competitive.models import NativeAd
from src.module2_competitive.reporter import IntelReporter
from src.module3_creative.generator import CreativeGenerator
from src.module4_presell.generator import AdvertorialGenerator
from src.module4_presell.builder import AdvertorialBuilder
from src.module4_presell.site_builder import PresellSiteBuilder

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

# Initialize session state
if "selected_offers" not in st.session_state:
    st.session_state.selected_offers = []
if "selected_offer" not in st.session_state:
    st.session_state.selected_offer = None
if "vsl_info" not in st.session_state:
    st.session_state.vsl_info = None
if "ranked_offers" not in st.session_state:
    st.session_state.ranked_offers = None

# 5-tab workflow
tabs = st.tabs([
    "1. Ranking (Module 1)",
    "2. VSL Detection (Module 4A)",
    "3. Competition (Module 2)",
    "4. Creatives (Module 3)",
    "5. Pre-sell (Module 4B)"
])

# ===== TAB 1: OFFER RANKING =====
with tabs[0]:
    st.header("Step 1: Offer Ranking")
    st.write("Upload MaxWeb offers and rank by potential")

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
                st.session_state.selected_offers = []

        # Display results
        if st.session_state.ranked_offers:
            ranked = st.session_state.ranked_offers
            st.subheader("Top Ranked Offers")

            col_check, col_rank, col_name, col_payout, col_epc, col_score = st.columns(
                [0.8, 0.5, 2.5, 1, 1, 1]
            )
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

            for idx, item in enumerate(ranked[:20]):
                col_check, col_rank, col_name, col_payout, col_epc, col_score = st.columns(
                    [0.8, 0.5, 2.5, 1, 1, 1]
                )

                checkbox_key = f"offer_check_{idx}"

                with col_check:
                    if checkbox_key not in st.session_state:
                        st.session_state[checkbox_key] = False

                    is_checked = st.checkbox(
                        "",
                        key=checkbox_key,
                        label_visibility="collapsed"
                    )

                    if is_checked and st.session_state.selected_offer != item.offer.name:
                        st.session_state.selected_offer = item.offer.name

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

            if st.session_state.selected_offer:
                st.success(f"✓ Selected: **{st.session_state.selected_offer}**")
                st.info("Go to Step 2 (VSL Detection) to continue →")

        temp_path.unlink(missing_ok=True)
    else:
        st.info("Upload CSV to start")


# ===== TAB 2: VSL DETECTION =====
with tabs[1]:
    st.header("Step 2: VSL Detection (MaxWeb)")
    st.write("Detect the angle/hook from MaxWeb VSL")

    if st.session_state.selected_offer:
        st.success(f"📌 Offer: **{st.session_state.selected_offer}**")
    else:
        st.warning("💡 Go to Step 1 and select an offer first")

    maxweb_url = st.text_input(
        "MaxWeb VSL URL",
        placeholder="https://maxweb.com/offer/... (copy from MaxWeb after login)",
        key="vsl_url",
        help="Login to MaxWeb, copy VSL URL, paste here"
    )

    if st.button("Detect VSL Angle", type="primary", key="detect_vsl_btn"):
        if not maxweb_url:
            st.error("Please enter MaxWeb URL")
        else:
            with st.spinner("Scraping MaxWeb VSL..."):
                try:
                    detector = MaxWebDetector()
                    vsl_info = detector.detect(maxweb_url)

                    if vsl_info:
                        st.session_state.vsl_info = vsl_info
                        st.success("✓ VSL angle detected!")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Angle:**")
                            st.write(vsl_info["angle"])
                            st.write("**Hook Type:**")
                            st.write(vsl_info["hook_type"])
                        with col2:
                            st.write("**Main Claim:**")
                            st.write(vsl_info["main_claim"])
                            st.write("**Emotional Trigger:**")
                            st.write(vsl_info["emotional_trigger"])

                        st.info("Go to Step 3 (Competition) to find supporting painpoints →")
                    else:
                        st.error("Could not detect angle from URL")
                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"VSL detection error: {e}")


# ===== TAB 3: COMPETITIVE RESEARCH =====
with tabs[2]:
    st.header("Step 3: Competitive Research")
    st.write("Scrape Reddit/competitors to find supporting painpoints")

    if st.session_state.selected_offer:
        st.success(f"📌 Offer: **{st.session_state.selected_offer}**")
    else:
        st.warning("💡 Go to Step 1 and select an offer first")

    if st.session_state.vsl_info:
        st.info(f"📌 VSL Angle: {st.session_state.vsl_info['angle']}")
        st.write("Reddit scraping will focus on validating this angle...")
    else:
        st.warning("💡 Go to Step 2 and detect VSL angle first")

    col1, col2 = st.columns(2)
    with col1:
        niche = st.selectbox("Niche", ["brain-health", "lung-health", "mens-health"], key="niche_select")
    with col2:
        sources = st.multiselect(
            "Sources",
            ["reddit", "amazon", "quora", "dailymail", "msn", "yahoo"],
            default=["reddit"],
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
                env = os.environ.copy()
                api_key = env.get('ANTHROPIC_API_KEY', 'NOT_FOUND')
                st.write(f"[DEBUG] API Key: {api_key[:30]}... (len={len(api_key)})")

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
                    st.session_state.niche = niche

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


# ===== TAB 4: AD CREATION =====
with tabs[3]:
    st.header("Step 4: Native Ad Creation")
    st.write("Generate native ads aligned with VSL angle + competitive insights")

    if st.session_state.selected_offer:
        st.success(f"📌 Offer: **{st.session_state.selected_offer}**")
    else:
        st.warning("💡 Go to Step 1 and select an offer first")

    if st.session_state.vsl_info:
        st.info(f"📌 VSL Angle: {st.session_state.vsl_info['angle']}")
    else:
        st.warning("💡 Go to Step 2 and detect VSL angle first")

    col1, col2 = st.columns(2)
    with col1:
        niche = st.selectbox("Niche", ["brain-health", "lung-health", "mens-health"], key="creative_niche_select")
    with col2:
        reports = list(Path("output/reports").glob(f"competitive_intel_*_{niche}.json"))
        report_status = "✓ Patterns loaded" if reports else "⚠ Generic mode"
        st.write(f"Report status: {report_status}")

    if st.button("Generate Creatives", type="primary", key="creative_generate_btn"):
        if not st.session_state.selected_offer:
            st.error("Please select an offer in Step 1")
        elif not st.session_state.vsl_info:
            st.error("Please detect VSL angle in Step 2")
        else:
            with st.spinner("Generating creatives with Claude..."):
                try:
                    generator = CreativeGenerator()
                    creative_set = generator.generate(
                        offer_name=st.session_state.selected_offer,
                        niche=niche,
                        auto_load_report=True,
                        vsl_angle=st.session_state.vsl_info["angle"]
                    )

                    st.subheader(f"Generated Creatives ({len(creative_set.creatives)} variations)")

                    df_data = []
                    for creative in creative_set.creatives:
                        df_data.append({
                            "Hook Type": creative.hook_type.capitalize(),
                            "Headline": creative.headline,
                            "Description": creative.description,
                        })

                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)

                    csv_content = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv_content,
                        file_name=f"creatives_{niche}_{st.session_state.selected_offer.lower().replace(' ', '')}_{creative_set.generated_at.strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        key="creative_download_csv"
                    )

                    st.success("✓ Ads generated aligned with VSL angle!")
                    st.info("Go to Step 5 (Pre-sell) to build the landing page →")

                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"Creative error: {e}")


# ===== TAB 5: PRESELL PAGE =====
with tabs[4]:
    st.header("Step 5: Pre-sell Page Generation")
    st.write("Add presell page to your presell website")

    st.info("""
    **Setup (one-time):**
    ```
    python -m src.module4_presell init-site --domain your-domain.com
    ```
    This creates a website with 8 generic health articles ready for presell pages.
    """)

    if st.session_state.selected_offer:
        st.success(f"📌 Offer: **{st.session_state.selected_offer}**")
    else:
        st.warning("💡 Go to Step 1 and select an offer first")

    if st.session_state.vsl_info:
        st.info(f"📌 VSL Angle: {st.session_state.vsl_info['angle']}")
    else:
        st.warning("💡 Go to Step 2 and detect VSL angle first")

    col1, col2 = st.columns(2)
    with col1:
        offer_url = st.text_input(
            "Affiliate URL",
            placeholder="https://maxweb.com/offer/...",
            key="presell_url"
        )
    with col2:
        niche = st.selectbox("Niche", ["brain-health", "lung-health", "mens-health"], key="presell_niche_select")

    if st.button("Generate Pre-sell Page", type="primary", key="presell_generate_btn"):
        if not st.session_state.selected_offer or not offer_url:
            st.error("Please select offer and enter URL")
        elif not st.session_state.vsl_info:
            st.error("Please detect VSL angle in Step 2")
        else:
            with st.spinner("Generating presell page with Claude..."):
                try:
                    generator = AdvertorialGenerator()
                    page = generator.generate(
                        offer_name=st.session_state.selected_offer,
                        offer_category="supplement",
                        niche=niche,
                        offer_url=offer_url,
                        auto_load_report=True,
                        vsl_angle=st.session_state.vsl_info["angle"]
                    )

                    # Build presell page HTML
                    html_content = AdvertorialBuilder.build(page)

                    # Add to website
                    site_builder = PresellSiteBuilder()
                    article_path = site_builder.add_article(page, html_content)

                    st.success(f"✓ Article added: `{article_path.name}`")

                    st.subheader("Preview")
                    st.components.v1.html(html_content, height=700, scrolling=True)

                    st.write("---")
                    st.info(f"""
                    **Article saved to:**
                    `output/presell_site/articles/{article_path.name}`

                    **URL will be:**
                    `https://your-domain.com/articles/{article_path.stem}.html`

                    Continue adding more presell pages, then deploy the entire `presell_site/` folder.
                    """)

                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"Presell error: {e}")
