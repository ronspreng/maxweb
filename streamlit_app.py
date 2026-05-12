"""Streamlit GUI for MaxWeb Affiliate System — Logical workflow."""
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
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
from src.module3_creative.exporter import CreativeExporter
from src.module4_presell.generator import AdvertorialGenerator
from src.module4_presell.builder import AdvertorialBuilder
from src.module4_presell.site_builder import PresellSiteBuilder
from src.module4_presell.publisher import PresellPublisher
from src.module5_feedback.scraper import ClickHubScraper
from src.module5_feedback.analyzer import CampaignAnalyzer
from src.module5_feedback.reporter import CampaignReporter

# Load .env at startup
load_dotenv()

# ===== AUTHENTICATION (HF Spaces) =====
def check_authentication() -> bool:
    """Check if user is authenticated via password."""
    auth_enabled = os.getenv("STREAMLIT_AUTH_ENABLED", "false").lower() == "true"
    if not auth_enabled:
        return True

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.set_page_config(page_title="MaxWeb System - Login", layout="centered")
        st.title("MaxWeb Affiliate System")
        st.write("**Secure Access Required**")

        password = st.text_input("Enter password:", type="password")
        if st.button("Login"):
            correct_password = os.getenv("STREAMLIT_PASSWORD", "change_me_in_hf_secrets")
            if password == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        return False

    return True

if not check_authentication():
    st.stop()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API key from environment
def _load_api_key():
    """Load API key from environment or .env file."""
    # Try environment first (works on Streamlit Cloud)
    if "ANTHROPIC_API_KEY" in os.environ:
        return os.environ["ANTHROPIC_API_KEY"]

    # Fallback to .env file (local development)
    try:
        from pathlib import Path
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        os.environ["ANTHROPIC_API_KEY"] = key
                        return key
    except Exception:
        pass

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

# 6-tab workflow
tabs = st.tabs([
    "1. Ranking (Module 1)",
    "2. VSL Detection (Module 4A)",
    "3. Competition (Module 2)",
    "4. Creatives (Module 3)",
    "5. Pre-sell (Module 4B)",
    "6. Analytics (Module 5)"
])

# ===== TAB 1: OFFER RANKING =====
CAMPAIGNS_CSV = Path("data/campaigns.csv")
SCRAPER_PATH = Path(".claude/skills/maxweb-campaigns/scripts/maxweb_scraper.py")


def _age_str(mtime: datetime) -> str:
    age = datetime.now() - mtime
    s = age.total_seconds()
    if s < 60:
        return "zojuist"
    if s < 3600:
        return f"{int(s // 60)} min geleden"
    if s < 86400:
        return f"{int(s // 3600)} uur geleden"
    return f"{age.days} dag(en) geleden"


with tabs[0]:
    st.header("Step 1: Offer Ranking")
    st.write("Rank MaxWeb offers by potential — live van de API of upload een eigen CSV")

    # --- Refresh-from-MaxWeb-bar ---
    status_col, refresh_col = st.columns([3, 1])

    with status_col:
        if CAMPAIGNS_CSV.exists():
            _mtime = datetime.fromtimestamp(CAMPAIGNS_CSV.stat().st_mtime)
            st.caption(
                f"`data/campaigns.csv` — laatst ververst **{_age_str(_mtime)}** "
                f"({_mtime.strftime('%a %d %b %H:%M')})"
            )
        else:
            st.caption(
                "Nog geen `data/campaigns.csv` — klik **Refresh from MaxWeb** om "
                "voor het eerst te scrapen."
            )
        if st.session_state.get("scrape_status") == "ok":
            st.success("Scrape geslaagd")
        elif st.session_state.get("scrape_status") == "expired":
            st.error(
                "Cookies verlopen. Refresh `MAXWEB_SESSID3` (en evt. `MAXWEB_TRUST2FA`) "
                "in je `.env` - DevTools -> Application -> Cookies."
            )
        elif st.session_state.get("scrape_status") == "error":
            st.error("Scraper-fout - zie details.")

    with refresh_col:
        st.write("")  # vertical spacer
        if st.button("Refresh from MaxWeb", type="primary", key="refresh_maxweb"):
            with st.spinner("Scraper draait..."):
                try:
                    _result = subprocess.run(
                        [sys.executable, str(SCRAPER_PATH)],
                        cwd=str(Path.cwd()),
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    st.session_state.scrape_stdout = _result.stdout
                    if _result.returncode == 0:
                        st.session_state.scrape_status = "ok"
                        st.session_state.scrape_error = None
                    else:
                        _err = (_result.stderr or _result.stdout).strip()
                        if "401" in _err or "Unauthorized" in _err:
                            st.session_state.scrape_status = "expired"
                        else:
                            st.session_state.scrape_status = "error"
                        st.session_state.scrape_error = _err
                except subprocess.TimeoutExpired:
                    st.session_state.scrape_status = "error"
                    st.session_state.scrape_error = "Scraper timeout (60s)"
                except Exception as _e:
                    st.session_state.scrape_status = "error"
                    st.session_state.scrape_error = f"{type(_e).__name__}: {_e}"
            st.rerun()

    if st.session_state.get("scrape_error"):
        with st.expander("Foutdetails laatste scrape", expanded=False):
            st.code(st.session_state.scrape_error[:3000])

    # --- Upload als fallback ---
    with st.expander("Of: upload een eigen CSV", expanded=False):
        uploaded_file = st.file_uploader("Upload MaxWeb CSV", type="csv")

    budget = st.number_input("Budget ($)", value=200.0, min_value=50.0)

    # --- Bron-CSV bepalen: upload > scrape-output ---
    source_csv = None
    temp_path = None
    if uploaded_file:
        temp_path = Path("temp_upload.csv")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        source_csv = temp_path
    elif CAMPAIGNS_CSV.exists():
        source_csv = CAMPAIGNS_CSV

    if source_csv:
        if st.button("Rank Offers", key="rank_btn"):
            with st.spinner("Ranking..."):
                offers = CSVImporter.import_csv(source_csv)
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

                # Auto-detect VSL
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🔍 Auto-detect VSL", type="primary", key="auto_detect_vsl"):
                        with st.spinner("Searching MaxWeb for VSL..."):
                            try:
                                detector = MaxWebDetector()
                                vsl_info = detector.detect(st.session_state.selected_offer)

                                if vsl_info:
                                    st.session_state.vsl_info = vsl_info
                                    st.success(f"✓ Found VSL: {vsl_info['angle']}")
                                    st.info("Go to Step 2 to confirm and continue →")
                                else:
                                    st.warning("Could not find VSL. Enter manually in Step 2.")
                            except Exception as e:
                                st.error(f"Error: {e}")

                with col2:
                    if st.session_state.vsl_info:
                        st.info(f"**VSL Angle:** {st.session_state.vsl_info['angle']}")
                    else:
                        st.info("Go to Step 2 (VSL Detection) to continue →")

        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    else:
        st.info("Klik **Refresh from MaxWeb** om data op te halen, of upload een eigen CSV.")


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

                    st.write("---")
                    st.subheader("📤 Export for Ad Platforms")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        mgid_csv = CreativeExporter.to_mgid_csv(creative_set)
                        st.download_button(
                            label="📌 MGID Format",
                            data=mgid_csv,
                            file_name=f"mgid_{niche}_{st.session_state.selected_offer.lower().replace(' ', '')}_{creative_set.generated_at.strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            key="creative_export_mgid"
                        )
                        st.caption("Copy-paste into MGID dashboard")

                    with col2:
                        taboola_csv = CreativeExporter.to_taboola_csv(creative_set)
                        st.download_button(
                            label="🎯 Taboola Format",
                            data=taboola_csv,
                            file_name=f"taboola_{niche}_{st.session_state.selected_offer.lower().replace(' ', '')}_{creative_set.generated_at.strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            key="creative_export_taboola"
                        )
                        st.caption("Copy-paste into Taboola dashboard")

                    with col3:
                        generic_csv = CreativeExporter.to_generic_csv(creative_set)
                        st.download_button(
                            label="📋 Full CSV",
                            data=generic_csv,
                            file_name=f"creatives_{niche}_{st.session_state.selected_offer.lower().replace(' ', '')}_{creative_set.generated_at.strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            key="creative_export_generic"
                        )
                        st.caption("All details for reference")

                    st.success("✓ Ads generated aligned with VSL angle!")
                    st.info("Go to Step 5 (Pre-sell) to build the landing page →")

                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"Creative error: {e}")


# ===== TAB 5: PRESELL PAGE =====
with tabs[4]:
    st.header("Step 5: Pre-sell Page Generation")
    st.write("Add presell page to your presell website")

    st.success("✓ Website is ready! (8 generic articles + compliance pages)")

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
                    `https://presellsite.vercel.app/articles/{article_path.stem}.html`
                    """)

                    # Publish to GitHub button
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("🚀 Publish to Website", type="primary", key="presell_publish_btn"):
                            with st.spinner("Publishing to GitHub..."):
                                success = PresellPublisher.publish_to_website(
                                    offer_slug=article_path.stem,
                                    html_content=html_content,
                                    commit_message=f"Add presell: {st.session_state.selected_offer}",
                                    auto_push=True
                                )
                                if success:
                                    st.success("✓ Published to GitHub! Vercel will redeploy in ~30s.")
                                else:
                                    st.error("Failed to publish. Check logs.")
                    with col2:
                        st.info("Vercel auto-deploys when files push to GitHub → live in ~30 seconds")

                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"Presell error: {e}")


# ===== TAB 6: ANALYTICS (MODULE 5) =====
with tabs[5]:
    st.header("Step 6: Campaign Analytics & Optimization")
    st.write("Analyze ClickHub campaign data and get optimization recommendations")

    col1, col2 = st.columns(2)
    with col1:
        campaign_name = st.text_input(
            "Campaign Name (from ClickHub)",
            placeholder="e.g., Gluco Savior",
            key="analytics_campaign_name"
        )
    with col2:
        days = st.slider("Days to analyze", min_value=1, max_value=90, value=7, key="analytics_days")

    if st.button("📊 Analyze Campaign", type="primary", key="analytics_analyze_btn"):
        if not campaign_name:
            st.error("Please enter campaign name")
        else:
            with st.spinner("Connecting to ClickHub and fetching data..."):
                try:
                    # Scrape ClickHub
                    scraper = ClickHubScraper()
                    if not scraper.login():
                        st.error("Failed to login to ClickHub. Check credentials in .env")
                    else:
                        analysis = scraper.analyze_campaign(campaign_name, days=days)

                        if not analysis:
                            st.error(f"Campaign '{campaign_name}' not found in ClickHub")
                        else:
                            # Show summary
                            st.success(f"✓ Loaded: {campaign_name}")

                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Clicks", f"{analysis.total_clicks:,}")
                            with col2:
                                st.metric("Conversions", f"{analysis.total_conversions:,}")
                            with col3:
                                st.metric("Spend", f"${analysis.total_spend:,.2f}")
                            with col4:
                                roi_color = "green" if analysis.overall_roi > 0 else "red"
                                st.metric("ROI", f"{analysis.overall_roi:.1f}%")

                            st.write("---")

                            # Generate recommendations
                            analyzer = CampaignAnalyzer(roi_target=20.0)
                            recommendations = analyzer.analyze(analysis)

                            if recommendations:
                                st.subheader("🎯 Recommendations")

                                for action in ["scale", "optimize", "kill", "maintain"]:
                                    action_recs = [r for r in recommendations if r.action == action]
                                    if action_recs:
                                        with st.expander(f"{action.upper()} ({len(action_recs)})"):
                                            for rec in action_recs:
                                                icon = "🚀" if action == "scale" else "⚙️" if action == "optimize" else "🔴" if action == "kill" else "✓"
                                                st.write(f"{icon} **{rec.sub_id}**")
                                                st.write(f"   {rec.reason}")
                                                st.write(f"   Current {rec.metric}: {rec.current_value:.1f}%")
                            else:
                                st.info("Need more data to generate recommendations. (Minimum 50 clicks per variant)")

                            # Show all Sub-IDs table
                            st.subheader("📊 All Variants (Sub-IDs)")
                            df_sub_ids = pd.DataFrame([
                                {
                                    "Sub-ID": sid.sub_id,
                                    "Clicks": sid.clicks,
                                    "Conversions": sid.conversions,
                                    "Revenue": f"${sid.revenue:.2f}",
                                    "Spend": f"${sid.spend:.2f}",
                                    "ROI": f"{sid.roi:.1f}%",
                                    "CPA": f"${sid.cpa:.2f}",
                                    "EPC": f"${sid.epc:.2f}",
                                }
                                for sid in sorted(analysis.sub_ids, key=lambda x: x.roi, reverse=True)
                            ])
                            st.dataframe(df_sub_ids, use_container_width=True)

                            # Generate and download report
                            st.write("---")
                            report = CampaignReporter.generate_markdown(analysis, recommendations)

                            st.download_button(
                                label="📥 Download Full Report (Markdown)",
                                data=report,
                                file_name=f"campaign_analysis_{campaign_name.lower().replace(' ', '_')}_{days}d.md",
                                mime="text/markdown",
                                key="analytics_download_report"
                            )
                            st.info("Report includes all metrics, rankings, and recommendations")

                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"Analytics error: {e}")
