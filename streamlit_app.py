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
from src.module3_creative.image_generator import ImageGenerator
from src.module3_creative.image_publisher import ImagePublisher
from src.module4_presell.generator import AdvertorialGenerator
from src.module4_presell.editorial_generator import EditorialGenerator
from src.module4_presell.builder import AdvertorialBuilder
from src.module4_presell.compliance_fixer import ComplianceFixer
from src.module4_presell.site_builder import PresellSiteBuilder
from src.module4_presell.publisher import PresellPublisher
from src.module5_feedback.scraper import ClickHubScraper
from src.module5_feedback.analyzer import CampaignAnalyzer
from src.module5_feedback.reporter import CampaignReporter

# Load .env at startup — override=True maakt .env de canonical bron
# (anders winnen stale Windows-environment variabelen)
load_dotenv(override=True)

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

# Load API key — .env wint van stale system-env (cloud blijft werken via env)
def _load_api_key():
    """Load ANTHROPIC_API_KEY: .env first, env fallback."""
    # Eerst .env (zodat updates in .env meteen werken zonder reboot)
    try:
        from pathlib import Path
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if key:
                            os.environ["ANTHROPIC_API_KEY"] = key
                            return key
    except Exception:
        pass

    # Cloud-fallback: env var (Streamlit Cloud / HF Spaces secrets)
    return os.environ.get("ANTHROPIC_API_KEY")

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
if "search_keywords" not in st.session_state:
    st.session_state.search_keywords = None

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


def _lookup_offer_url(offer_name):
    """Find an offer's company_website (VSL URL) uit data/campaigns.csv."""
    if not CAMPAIGNS_CSV.exists():
        return None
    try:
        df = pd.read_csv(CAMPAIGNS_CSV)
    except Exception:
        return None
    needle = (offer_name or "").strip().lower()
    for _, row in df.iterrows():
        if str(row.get("name", "")).strip().lower() == needle:
            url = str(row.get("company_website", "")).strip()
            return url or None
    return None


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
                        # Lookup VSL-URL voor Module 2 (auto-prefill)
                        st.session_state.selected_offer_url = _lookup_offer_url(item.offer.name)

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

            # Display selected offer and niche (outside the for loop)
            if st.session_state.selected_offer and st.session_state.ranked_offers:
                st.success(f"✓ Selected: **{st.session_state.selected_offer}**")

                # Find selected offer and extract niche from category
                selected_item = None
                for item in st.session_state.ranked_offers:
                    if item.offer.name == st.session_state.selected_offer:
                        selected_item = item
                        break

                if selected_item:
                    # Use MaxWeb category directly as niche
                    st.session_state.selected_niche = selected_item.offer.category
                    st.write(f"**Niche:** {selected_item.offer.category}")

                    # Optional: Custom search keywords for scraping
                    col_kw1, col_kw2 = st.columns([2, 1])
                    with col_kw1:
                        custom_keywords = st.text_input(
                            "Search keywords (optional, comma-separated)",
                            placeholder="e.g. brain fog, memory loss, aging",
                            help="Leave empty to auto-extract from niche"
                        )
                        if custom_keywords:
                            st.session_state.search_keywords = [k.strip() for k in custom_keywords.split(",")]
                        else:
                            st.session_state.search_keywords = None

                    st.info("Go to Step 2 (VSL Detection) to analyze the VSL →")

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

    # Auto-prefill URL als selected_offer veranderd is.
    # Streamlit-pattern: session_state setten VOOR de widget, anders sticky.
    _current_offer = st.session_state.get("selected_offer")
    _last_offer = st.session_state.get("_vsl_last_offer")
    if _current_offer and _current_offer != _last_offer:
        _new_url = st.session_state.get("selected_offer_url", "") or ""
        st.session_state["vsl_url"] = _new_url
        st.session_state["_vsl_last_offer"] = _current_offer

    if st.session_state.get("vsl_url"):
        st.caption("VSL-URL automatisch overgenomen uit campaigns.csv — pas aan als je een andere URL wil scrapen")

    maxweb_url = st.text_input(
        "MaxWeb VSL URL",
        placeholder="https://... (direct VSL of tracking-redirect)",
        key="vsl_url",
        help="Wordt automatisch ingevuld als je een offer selecteert in Stap 1. Anders: plak handmatig."
    )

    if st.button("Detect VSL Angle", type="primary", key="detect_vsl_btn"):
        if not maxweb_url:
            st.error("Please enter MaxWeb URL")
        else:
            with st.spinner("Scraping MaxWeb VSL..."):
                try:
                    detector = MaxWebDetector()
                    vsl_info = detector._detect_from_url(maxweb_url)

                    if vsl_info and vsl_info.get("error"):
                        st.error(f"VSL-detectie mislukt: {vsl_info['error']}")
                        vsl_info = None

                    if vsl_info:
                        st.session_state.vsl_info = vsl_info
                        st.success("✓ VSL angle detected!")
                    else:
                        st.error("Could not detect angle from URL")
                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"VSL detection error: {e}")

    # Display saved VSL info (outside button block so it persists)
    if hasattr(st.session_state, 'vsl_info') and st.session_state.vsl_info:
        st.write("---")
        st.subheader("✓ Detected VSL Angle")
        vsl = st.session_state.vsl_info
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Angle:**")
            st.write(vsl["angle"])
            st.write("**Hook Type:**")
            st.write(vsl["hook_type"])
        with col2:
            st.write("**Main Claim:**")
            st.write(vsl["main_claim"])
            st.write("**Emotional Trigger:**")
            st.write(vsl["emotional_trigger"])

        st.info("Go to Step 3 (Competition) to find supporting painpoints →")


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
        # Use niche from offer selection in Tab 1
        if st.session_state.get("selected_niche"):
            niche = st.session_state.selected_niche
            st.write(f"**Niche:** {niche}")
        else:
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
        # Add custom keywords if provided
        if st.session_state.get("search_keywords"):
            keywords_arg = ",".join(st.session_state.search_keywords)
            cmd.extend(["--keywords", keywords_arg])
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
                        report_file = sorted(Path("output/reports").glob(f"competitive_intel_*_{niche}.md"))
                        if report_file:
                            with open(report_file[-1], encoding="utf-8") as f:
                                report_content = f.read()
                            st.session_state.competitive_report = report_content
                            st.session_state.competitive_report_file = report_file[-1].name
                else:
                    st.error(f"Scraper failed (exit code {proc.returncode})")

        except Exception as e:
            st.error(f"Error: {e}")

    # Display saved competitive report (outside button block so it persists)
    if hasattr(st.session_state, 'competitive_report') and st.session_state.competitive_report:
        st.write("---")
        st.subheader("📊 Report")
        st.markdown(st.session_state.competitive_report)
        with open(Path("output/reports") / st.session_state.competitive_report_file, "r") as f:
            st.download_button(
                label="📥 Download Report",
                data=f.read(),
                file_name=st.session_state.competitive_report_file,
                mime="text/markdown",
                key="download_competitive_report"
            )


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
        # Use niche from offer selection in Tab 1
        if st.session_state.get("selected_niche"):
            niche = st.session_state.selected_niche
            st.write(f"**Niche:** {niche}")
        else:
            niche = st.selectbox("Niche", ["brain-health", "lung-health", "mens-health"], key="creative_niche_select")
            st.session_state.selected_niche = niche
    with col2:
        reports = list(Path("output/reports").glob(f"competitive_intel_*_{niche}.json"))
        report_status = "✓ Patterns loaded" if reports else "⚠ Generic mode"
        st.write(f"Report status: {report_status}")

    col_gen1, col_gen2, col_gen3 = st.columns(3)

    def _generate_creatives_batch(append_to_existing: bool = False):
        """Helper to generate creatives batch."""
        if not st.session_state.selected_offer:
            st.error("Please select an offer in Step 1")
            return
        if not st.session_state.vsl_info:
            st.error("Please detect VSL angle in Step 2")
            return

        with st.spinner("Generating creatives with Claude..."):
            try:
                generator = CreativeGenerator()
                # VSL-info uit Module 2 ophalen voor weighted distribution + image-prompt context
                _vsl_hook = None
                _vsl_main_claim = None
                _vsl_emot = None
                if st.session_state.get("vsl_info"):
                    _vsl_hook = st.session_state.vsl_info.get("hook_type")
                    _vsl_main_claim = st.session_state.vsl_info.get("main_claim")
                    _vsl_emot = st.session_state.vsl_info.get("emotional_trigger")
                new_set = generator.generate(
                    offer_name=st.session_state.selected_offer,
                    niche=niche,
                    auto_load=True,
                    vsl_hook=_vsl_hook,
                    vsl_main_claim=_vsl_main_claim,
                    vsl_emotional_trigger=_vsl_emot,
                )

                # Merge or replace
                if append_to_existing and hasattr(st.session_state, 'creative_set') and st.session_state.creative_set:
                    # Append new creatives to existing set by extending the list
                    st.session_state.creative_set.creatives.extend(new_set.creatives)
                    action_msg = f"Added {len(new_set.creatives)} more creatives"
                else:
                    # Replace entire set
                    st.session_state.creative_set = new_set
                    action_msg = f"Generated {len(new_set.creatives)} new creatives"

                # Rebuild dataframe
                df_data = []
                for i, creative in enumerate(st.session_state.creative_set.creatives):
                    df_data.append({
                        "Select": True,
                        "Hook Type": creative.hook_type.capitalize(),
                        "Headline": creative.headline,
                        "Description": creative.description,
                    })

                df = pd.DataFrame(df_data)
                st.session_state.creative_df_editor = df
                st.session_state.selected_creative_indices = list(range(len(st.session_state.creative_set.creatives)))

                st.success(f"✓ {action_msg}! Select which ones to use for presell pages →")

            except Exception as e:
                st.error(f"Error: {e}")
                logger.error(f"Creative error: {e}")

    with col_gen1:
        if st.button("🚀 Generate Creatives", type="primary", key="creative_generate_btn"):
            _generate_creatives_batch(append_to_existing=False)

    with col_gen2:
        if st.button("➕ Generate More", key="creative_generate_more_btn"):
            if not hasattr(st.session_state, 'creative_set') or not st.session_state.creative_set:
                st.error("Generate creatives first")
            else:
                _generate_creatives_batch(append_to_existing=True)

    with col_gen3:
        if st.button("🔄 Generate New", key="creative_generate_new_btn"):
            _generate_creatives_batch(append_to_existing=False)

    # Display creatives table if available (OUTSIDE button block so it persists)
    if hasattr(st.session_state, 'creative_set') and st.session_state.creative_set:
        col_title, col_select = st.columns([4, 1])
        with col_title:
            st.subheader(f"Generated Creatives ({len(st.session_state.creative_set.creatives)} variations)")

        with col_select:
            select_col1, select_col2 = st.columns(2)
            with select_col1:
                if st.button("✓ All", key="select_all_creatives", help="Select all creatives"):
                    st.session_state.creative_df_editor["Select"] = True
                    st.rerun()
            with select_col2:
                if st.button("✗ None", key="deselect_all_creatives", help="Deselect all creatives"):
                    st.session_state.creative_df_editor["Select"] = False
                    st.rerun()

        edited_df = st.data_editor(
            st.session_state.creative_df_editor,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Select": st.column_config.CheckboxColumn(width="small"),
                "Hook Type": st.column_config.TextColumn(width="small"),
                "Headline": st.column_config.TextColumn(width="medium"),
                "Description": st.column_config.TextColumn(width="large"),
            },
            key="creative_data_editor"
        )

        selected_indices = [i for i, row in enumerate(edited_df.itertuples(index=False)) if row.Select]
        st.session_state.selected_creative_indices = selected_indices
        st.caption(f"{len(selected_indices)} of {len(st.session_state.creative_set.creatives)} selected for presell")

        # Image generation section
        st.divider()
        st.subheader("🎨 AI Image Generation")

        _has_openai_key = bool(os.environ.get("OPENAI_API_KEY", "").strip())
        _n_creatives = len(st.session_state.creative_set.creatives)
        _already_generated = sum(1 for c in st.session_state.creative_set.creatives if c.image_url)

        img_col1, img_col2 = st.columns([2, 1])
        with img_col1:
            if _already_generated > 0:
                st.success(f"✓ {_already_generated} of {_n_creatives} creatives have an image_url")
            _quality = st.radio(
                "gpt-image-2 quality",
                ["low", "medium", "high"],
                index=1,  # default 'medium' — sweet spot voor native ads
                horizontal=True,
                key="gptimage_quality",
                help="low=$0.015 / medium=$0.058 / high=$0.230 per 1536x1024 image",
            )
            _price_map = {"low": 0.015, "medium": 0.058, "high": 0.230}
            _unit_price = _price_map[_quality]
            _est_cost = _n_creatives * _unit_price
            st.caption(
                f"Estimate: **${_est_cost:.2f}** for {_n_creatives} images @ ${_unit_price:.2f}/image"
            )
        with img_col2:
            st.write("")
            if not _has_openai_key:
                st.warning("OPENAI_API_KEY niet gezet in .env")
            _gen_disabled = not _has_openai_key
            if st.button(
                "🎨 Generate Images (gpt-image-2)",
                type="primary",
                disabled=_gen_disabled,
                key="generate_images_btn",
            ):
                try:
                    img_gen = ImageGenerator()
                    offer_slug = (st.session_state.selected_offer or "offer").lower().replace(" ", "-")
                    out_dir = Path("output") / "images" / offer_slug
                    progress = st.progress(0, text="Starting gpt-image-2 generation...")
                    status = st.empty()

                    def _cb(idx, total, msg):
                        progress.progress((idx + 1) / total, text=f"Image {idx + 1}/{total}: {msg}")
                        status.write(f"  ↳ creative {idx + 1}: {msg}")

                    batch = img_gen.generate_for_creative_set(
                        st.session_state.creative_set,
                        output_dir=out_dir,
                        offer_slug=offer_slug,
                        quality=_quality,
                        progress_callback=_cb,
                    )
                    progress.empty()
                    status.empty()
                    if batch.failed:
                        st.warning(
                            f"⚠ {batch.succeeded}/{batch.total} succeeded "
                            f"(${batch.total_cost_usd:.2f}), {batch.failed} failed — zie logs."
                        )
                    else:
                        st.success(
                            f"✓ All {batch.succeeded} images generated! "
                            f"Cost: ${batch.total_cost_usd:.2f}. "
                            f"Files saved to `{out_dir}`"
                        )
                    # Note: image URLs valid only ~1h on OpenAI CDN. Lokale files in out_dir/.
                except Exception as exc:
                    st.error(f"Image generation failed: {type(exc).__name__}: {exc}")
                    logger.exception("Image generation error")

        st.divider()
        st.subheader("📋 Image Prompts (manual fallback)")
        st.write("Niet automatisch gegenereerd? Gebruik deze prompts handmatig met DALL-E 3, Midjourney, of Stable Diffusion (600×500px)")

        # Show each creative's image prompt + generated image in a collapsible view
        for i, creative in enumerate(st.session_state.creative_set.creatives, 1):
            _has_img = bool(creative.image_url)
            _badge = "🖼️" if _has_img else "📝"
            with st.expander(
                f"{_badge} Creative {i} — [{creative.hook_type.upper()}] {creative.headline[:40]}...",
                expanded=False,
            ):
                st.write(f"**Hook Type:** {creative.hook_type}")
                st.write(f"**Headline:** {creative.headline}")
                st.write(f"**Description:** {creative.description}")
                st.divider()
                if _has_img:
                    try:
                        st.image(creative.image_url, caption="Generated by gpt-image-2", width=400)
                    except Exception:
                        st.warning("Image URL expired (Local file in output/images/). Check local file in output/images/.")
                    st.caption("✓ Lokaal opgeslagen in output/images/ (permanent)")
                st.write("**AI Image Prompt (600×500px):**")
                st.code(creative.image_prompt, language="text")
                if not _has_img:
                    st.caption("Klik bovenaan op 'Generate Images' of copy deze prompt naar DALL-E/Midjourney")

                # Copy-to-clipboard button (manual copy)
                st.text_input(
                    f"Image prompt {i} (copy-paste to AI tool)",
                    value=creative.image_prompt,
                    key=f"image_prompt_{i}",
                    disabled=True,
                    label_visibility="collapsed"
                )

        st.divider()
        st.subheader("🌐 Publish Images (for MGID/Taboola)")
        st.caption(
            "MGID accepteert geen lokale bestanden — images moeten op een publieke URL staan. "
            "Klik 'Publish' om alle images naar je presell-site (Vercel) te pushen via git. "
            "Daarna staan ze publiek op `{PRESELL_SITE_URL}/ad-images/<offer>/`."
        )

        _presell_url = os.environ.get("PRESELL_SITE_URL", "").strip().rstrip("/")
        if not _presell_url:
            st.warning(
                "⚠️ `PRESELL_SITE_URL` niet gezet in `.env`. "
                "MGID-CSV-export werkt wel maar Image URLs zullen relatief zijn → MGID rejecteert. "
                "Voeg toe aan .env: `PRESELL_SITE_URL=https://your-site.vercel.app`"
            )
        else:
            st.caption(f"Public base: `{_presell_url}`")

        _has_local_images = any(c.image_url and Path(c.image_url).exists() for c in st.session_state.creative_set.creatives)
        _offer_slug = (st.session_state.selected_offer or "offer").lower().replace(" ", "-")

        pub_col1, pub_col2 = st.columns([2, 1])
        with pub_col1:
            click_url = st.text_input(
                "ClickHub Campaign URL (voor 'Click URL' kolom in MGID-CSV)",
                value=st.session_state.get("clickhub_campaign_url", ""),
                placeholder="https://petalvane.com/t/<uuid>",
                key="clickhub_campaign_url",
                help="Plak hier de tracking-URL van je ClickHub-campagne (zie ClickHub → Campaigns → Edit → Campaign URL)",
            )
        with pub_col2:
            st.write("")  # spacer
            _publish_disabled = not _has_local_images
            if st.button(
                "📤 Publish Images to Vercel",
                type="primary",
                disabled=_publish_disabled,
                key="publish_images_btn",
                help="Kopieert lokale PNG-files naar presell_site/ad-images/<offer>/ en git push. Vercel deploy't automatisch.",
            ):
                with st.spinner("Pushing to Vercel (1-3 min deploy)..."):
                    try:
                        local_dir = Path("output") / "images" / _offer_slug
                        result = ImagePublisher.publish_images_for_offer(
                            offer_slug=_offer_slug,
                            local_images_dir=local_dir,
                            site_url=_presell_url or None,
                            auto_push=True,
                        )
                        if result.get("success"):
                            st.success(
                                f"✓ {result['copied']} images pushed to Vercel. "
                                f"Deploy duurt 1-3 min. "
                                f"Daarna live op `{_presell_url}/ad-images/{_offer_slug}/`"
                            )
                            with st.expander("Public URLs (voor MGID-CSV)", expanded=False):
                                for url in result["public_urls"]:
                                    st.code(url, language=None)
                        else:
                            st.error(f"❌ Publish faalde: {result.get('error', 'unknown')}")
                    except Exception as exc:
                        st.error(f"Error: {type(exc).__name__}: {exc}")
                        logger.exception("Publish error")
            if _publish_disabled:
                st.caption("⚠️ Genereer eerst images (knop bovenaan)")

        st.divider()
        st.subheader("📤 Export for Ad Platforms")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            mgid_csv = CreativeExporter.to_mgid_csv(
                st.session_state.creative_set,
                offer_slug=_offer_slug,
                site_url=_presell_url or None,
                click_url=st.session_state.get("clickhub_campaign_url", "") or None,
            )
            st.download_button(
                label="📌 MGID Format",
                data=mgid_csv,
                file_name=f"mgid_{niche}_{st.session_state.selected_offer.lower().replace(' ', '')}_{st.session_state.creative_set.generated_at.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="creative_export_mgid"
            )
            st.caption("Copy-paste into MGID dashboard")

        with col2:
            taboola_csv = CreativeExporter.to_taboola_csv(
                st.session_state.creative_set,
                offer_slug=_offer_slug,
                site_url=_presell_url or None,
                click_url=st.session_state.get("clickhub_campaign_url", "") or None,
            )
            st.download_button(
                label="🎯 Taboola Format",
                data=taboola_csv,
                file_name=f"taboola_{niche}_{st.session_state.selected_offer.lower().replace(' ', '')}_{st.session_state.creative_set.generated_at.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="creative_export_taboola"
            )
            st.caption("Copy-paste into Taboola dashboard")

        with col3:
            image_gen_csv = CreativeExporter.to_image_generation_csv(st.session_state.creative_set)
            st.download_button(
                label="🎨 Image Prompts",
                data=image_gen_csv,
                file_name=f"image_prompts_{niche}_{st.session_state.selected_offer.lower().replace(' ', '')}_{st.session_state.creative_set.generated_at.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="creative_export_images"
            )
            st.caption("For DALL-E 3 / Midjourney")

        with col4:
            generic_csv = CreativeExporter.to_generic_csv(st.session_state.creative_set)
            st.download_button(
                label="📋 Full CSV",
                data=generic_csv,
                file_name=f"creatives_{niche}_{st.session_state.selected_offer.lower().replace(' ', '')}_{st.session_state.creative_set.generated_at.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="creative_export_generic"
            )
            st.caption("All details for reference")

        st.info("Go to Step 5 (Pre-sell) to build landing pages for selected creatives →")


# ===== TAB 5: PRESELL PAGES (PER ANGLE) =====
with tabs[4]:
    st.header("Step 5: Pre-sell Pages (One per Hook Angle)")
    st.write(
        "Genereer **K landers, één per unieke hook-angle** uit Step 4. "
        "Alle creatives met dezelfde hook routeren naar dezelfde lander."
    )

    st.success("✓ Website is ready! (8 generic articles + compliance pages)")

    if st.session_state.selected_offer:
        st.success(f"📌 Offer: **{st.session_state.selected_offer}**")
    else:
        st.warning("💡 Go to Step 1 and select an offer first")

    # Check if creatives are available
    if hasattr(st.session_state, "creative_set") and st.session_state.creative_set:
        _all_creatives = st.session_state.creative_set.creatives
        _selected_idx = getattr(st.session_state, "selected_creative_indices", list(range(len(_all_creatives))))
        _creatives_to_use = [_all_creatives[i] for i in _selected_idx]
        _unique_hooks = sorted({c.hook_type for c in _creatives_to_use})
        st.success(
            f"✓ {len(_creatives_to_use)} creatives geselecteerd, "
            f"verdeeld over **{len(_unique_hooks)} unieke hook-angles**: "
            f"{', '.join('[' + h.upper() + ']' for h in _unique_hooks)}"
        )
    else:
        _creatives_to_use = []
        _unique_hooks = []
        st.warning("💡 Go to Step 4 and generate creatives first")

    # CTA URL info
    _cta_url = os.environ.get("CLICKHUB_CTA_URL", "https://petalvane.com/click")
    st.info(
        f"CTA-URL: `{_cta_url}` — uit `.env` (`CLICKHUB_CTA_URL`). "
        f"JS in de gegenereerde lander hangt automatisch `?clickid=<value>` eraan."
    )

    # Hook & niche & variant selection
    col1, col2 = st.columns([2, 1])
    with col1:
        if _unique_hooks:
            _hooks_to_build = st.multiselect(
                "Landers genereren voor deze hook-angles:",
                options=_unique_hooks,
                default=_unique_hooks,
                key="presell_hooks_select",
                help="Eén lander per geselecteerde hook. Alle creatives met die hook routeren erheen.",
            )
        else:
            _hooks_to_build = []
            st.selectbox("Hooks", [], disabled=True, key="presell_hooks_select_empty")

        # Layout variants — A/B test op visuele style binnen één hook
        _available_variants = ["news", "story"]
        _variants_to_build = st.multiselect(
            "Layout variants (A/B testing binnen hook):",
            options=_available_variants,
            default=["news"],
            key="presell_variants_select",
            help=(
                "Per hook genereren we 1 lander per variant. "
                "'news' = klassiek artikel-style. 'story' = persoonlijk verhaal-style. "
                "Selecteer beide voor visueel A/B-testen — zelfde content, andere look."
            ),
        )
    with col2:
        if st.session_state.get("selected_niche"):
            niche = st.session_state.selected_niche
            st.write(f"**Niche:** {niche}")
        else:
            niche = st.selectbox(
                "Niche",
                ["brain-health", "lung-health", "mens-health"],
                key="presell_niche_select",
            )
            st.session_state.selected_niche = niche

    if _hooks_to_build and _creatives_to_use and _variants_to_build:
        _preview_rows = []
        for h in _hooks_to_build:
            matched = [c for c in _creatives_to_use if c.hook_type == h]
            for v in _variants_to_build:
                _preview_rows.append(f"• **lp-{h}-{v}** ← {len(matched)} creative(s)")
        _total = len(_hooks_to_build) * len(_variants_to_build)
        st.caption(f"**{_total} landers** worden gegenereerd ({len(_hooks_to_build)} hooks × {len(_variants_to_build)} variants):\n\n" + "\n\n".join(_preview_rows))

    if st.button("Generate Landers", type="primary", key="presell_generate_all_btn"):
        if not st.session_state.selected_offer:
            st.error("Please select offer first (Step 1)")
        elif not _creatives_to_use:
            st.error("Please generate creatives in Step 4 first")
        elif not _hooks_to_build:
            st.error("Selecteer minstens 1 hook-angle")
        elif not _variants_to_build:
            st.error("Selecteer minstens 1 layout-variant")
        else:
            _total_landers = len(_hooks_to_build) * len(_variants_to_build)
            with st.spinner(f"Generating {_total_landers} landers ({len(_hooks_to_build)} hooks × {len(_variants_to_build)} variants)..."):
                try:
                    presell_pages = []
                    generator = AdvertorialGenerator()
                    site_builder = PresellSiteBuilder()

                    # Cache: per hook genereren we de PresellPage 1× (zelfde content),
                    # en renderen 'm in N variant-templates. Bespaart Claude-calls.
                    _page_cache = {}
                    idx = 0
                    for hook in _hooks_to_build:
                        matched = [c for c in _creatives_to_use if c.hook_type == hook]
                        vsl_angle = f"{hook.capitalize()} angle"

                        # Genereer page 1x per hook (cached)
                        if hook not in _page_cache:
                            _page_cache[hook] = generator.generate(
                                offer_name=st.session_state.selected_offer,
                                offer_category="supplement",
                                niche=niche,
                                offer_url=_cta_url,
                                auto_load_report=True,
                                vsl_angle=vsl_angle,
                            )
                        page = _page_cache[hook]

                        for variant in _variants_to_build:
                            idx += 1
                            html_content, _compliance_violations, _is_compliant = AdvertorialBuilder.build_and_check(page, variant=variant)
                            article_path = site_builder.add_article(
                                page, html_content, folder="presell-ads"
                            )

                            presell_pages.append({
                                "index": idx,
                                "hook": hook,
                                "variant": variant,
                                "matched_creatives": matched,
                                "page": page,
                                "html": html_content,
                                "path": article_path,
                                "slug": f"lp-{hook}-{variant}",
                                "compliance_violations": _compliance_violations,
                                "is_compliant": _is_compliant,
                                # Legacy compat
                                "creative": matched[0] if matched else None,
                            })

                    st.session_state.presell_pages = presell_pages
                    _unique_creatives_count = len(set(id(c) for p in presell_pages for c in p["matched_creatives"]))
                    st.success(
                        f"✓ {len(presell_pages)} landers gegenereerd "
                        f"({len(_hooks_to_build)} hooks × {len(_variants_to_build)} variants), "
                        f"covering {_unique_creatives_count} creatives"
                    )
                    st.info("✅ Compliance-check uitgevoerd — klaar om te publishen!")

                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"Presell batch error: {e}")

    # Display presell pages if they exist
    if hasattr(st.session_state, "presell_pages") and st.session_state.presell_pages:
        st.write("---")
        st.subheader("Generated Landers")

        for page_data in st.session_state.presell_pages:
            i = page_data["index"]
            hook = page_data.get("hook", "?")
            matched = page_data.get("matched_creatives", [])
            html = page_data["html"]
            n = len(matched)

            _is_ok = page_data.get("is_compliant", True)
            _viols = page_data.get("compliance_violations", [])
            _err_count = sum(1 for v in _viols if getattr(v, "severity", "") == "error")
            _badge = "✅" if _is_ok else f"⚠️ {_err_count}-violation{'s' if _err_count != 1 else ''}"
            _variant = page_data.get("variant", "news")
            with st.expander(
                f"Lander {i} — [{hook.upper()}] · {_variant.upper()} layout · {_badge} (covers {n} creative{'s' if n != 1 else ''})",
                expanded=(i == 1),
            ):
                if not _is_ok:
                    with st.container():
                        st.error(f"❌ {_err_count} compliance error(s) in final rendered HTML — fix vóór publish!")
                        for v in _viols:
                            if getattr(v, "severity", "") == "error":
                                st.write(f"  • **{v.location}**: {v.message}")
                                if v.suggested_fix:
                                    st.caption(f"    Fix: {v.suggested_fix}")

                        # Auto-fix knop — alleen voor content-violations (niet structurele issues)
                        _has_fixable = any(
                            getattr(v, "violation_type", "") in ("hard_claim", "forbidden_pattern")
                            and getattr(v, "severity", "") == "error"
                            for v in _viols
                        )
                        if _has_fixable:
                            if st.button(
                                f"🔧 Auto-fix with Claude (lander {i})",
                                key=f"autofix_{i}",
                                help="Claude rewrites de violating velden compliant. Re-check daarna.",
                            ):
                                with st.spinner("Claude herschrijft compliant..."):
                                    try:
                                        fixer = ComplianceFixer()
                                        fixed_page, new_viols, now_compliant = fixer.fix_page(
                                            page_data["page"], _viols
                                        )
                                        # Rebuild HTML met de gefixte page
                                        new_html, new_v2, new_ok = AdvertorialBuilder.build_and_check(fixed_page)
                                        # Update session_state
                                        page_data["page"] = fixed_page
                                        page_data["html"] = new_html
                                        page_data["compliance_violations"] = new_v2
                                        page_data["is_compliant"] = new_ok
                                        # Schrijf gefixte HTML ook naar bestaand artikel-pad
                                        if page_data.get("path"):
                                            Path(page_data["path"]).write_text(new_html, encoding="utf-8")
                                        if new_ok:
                                            st.success("✓ Alle compliance-errors gefixt! Refresh om bij te werken.")
                                        else:
                                            _remain = sum(1 for v in new_v2 if getattr(v, "severity", "") == "error")
                                            st.warning(f"⚠ {_remain} error(s) over (niet auto-fixable, bv. structureel/disclaimer)")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Auto-fix faalde: {type(exc).__name__}: {exc}")
                                        logger.exception("Compliance fix error")
                elif _viols:
                    st.warning(f"{len(_viols)} warning(s) — review aanbevolen maar niet blokkerend")
                col1, col2 = st.columns([3, 1])
                with col1:
                    if matched:
                        st.caption("**Creatives die hierheen routeren:**")
                        for c in matched:
                            st.markdown(f"- _{c.headline}_")
                        st.write("---")
                    st.components.v1.html(html, height=400, scrolling=True)
                with col2:
                    st.download_button(
                        label="📥 Download",
                        data=html,
                        file_name=f"lp-{hook}-{_variant}.html",
                        mime="text/html",
                        key=f"presell_download_{i}",
                    )

        st.write("---")
        st.write("**Select which landers to publish:**")

        to_publish = []
        for page_data in st.session_state.presell_pages:
            i = page_data["index"]
            hook = page_data.get("hook", "?")
            n = len(page_data.get("matched_creatives", []))
            if st.checkbox(
                f"Lander {i} — [{hook.upper()}] ({n} creatives)",
                value=True,
                key=f"pub_sel_{i}",
            ):
                to_publish.append(page_data)

        st.caption(f"{len(to_publish)} of {len(st.session_state.presell_pages)} selected")

        if st.button("🚀 Publish Selected", type="primary", key="presell_publish_selected_btn"):
            if not to_publish:
                st.error("Select at least one page to publish")
            else:
                with st.spinner(f"Publishing {len(to_publish)} pages to GitHub..."):
                    try:
                        published_count = 0
                        for page_data in to_publish:
                            path = page_data["path"]
                            html = page_data["html"]

                            success = PresellPublisher.publish_to_website(
                                offer_slug=path.stem,
                                html_content=html,
                                commit_message=f"Add presell: {st.session_state.selected_offer}",
                                auto_push=True
                            )
                            if success:
                                published_count += 1
                            else:
                                st.error(f"Failed to publish {path.name} — check logs")

                        if published_count > 0:
                            st.success(f"✓ Published {published_count} of {len(to_publish)} pages! Vercel redeploys in ~30s.")
                            st.info("Check your presell site in a few moments")
                        else:
                            st.error(f"Failed to publish any pages. Check git/GitHub access.")

                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.error(f"Presell publish error: {e}")

    # ===== MANAGE ARTICLES =====
    st.divider()
    st.subheader("🗑️ Manage Published Articles")

    site_builder = PresellSiteBuilder()
    col1, col2 = st.columns(2)

    with col1:
        with st.expander("Presell Ads (/presell-ads/)"):
            presell_ads = site_builder.list_articles(folder="presell-ads")
            if presell_ads:
                for ad in presell_ads:
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.caption(f"📄 {ad['title']}")
                        st.text(f"`{ad['filename']}`", help=ad['filename'])
                    with cols[1]:
                        if st.button("🗑️", key=f"delete_presell_{ad['filename']}", help="Delete"):
                            if site_builder.delete_article(ad['filename'], folder="presell-ads"):
                                st.success(f"Deleted & pushed: {ad['filename']}")
                                st.rerun()
                            else:
                                st.error(f"Failed to delete: {ad['filename']}")
            else:
                st.info("No presell ads yet")

    with col2:
        with st.expander("Editorial Articles (/articles/)"):
            articles = site_builder.list_articles(folder="articles")
            if articles:
                for article in articles:
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.caption(f"📄 {article['title']}")
                        st.text(f"`{article['filename']}`", help=article['filename'])
                    with cols[1]:
                        if st.button("🗑️", key=f"delete_article_{article['filename']}", help="Delete"):
                            if site_builder.delete_article(article['filename'], folder="articles"):
                                st.success(f"Deleted & pushed: {article['filename']}")
                                st.rerun()
                            else:
                                st.error(f"Failed to delete: {article['filename']}")
            else:
                st.info("No articles yet")

    # ===== GENERATE EDITORIAL ARTICLES =====
    st.divider()
    st.subheader("📝 Generate Editorial Article")

    col1, col2 = st.columns([2, 1])

    with col1:
        keywords_input = st.text_input(
            "Keywords (komma-gescheiden)",
            placeholder="brain fog, memory loss, aging",
            help="Enter multiple keywords separated by commas"
        )

    with col2:
        # Use niche from offer selection in Tab 1
        if st.session_state.get("selected_niche"):
            niche_edit = st.session_state.selected_niche
            st.write(f"**Niche:** {niche_edit}")
        else:
            st.warning("Select an offer in Step 1 first")

    if st.button("🚀 Generate Editorial Article", type="primary", key="generate_editorial_btn"):
        if not st.session_state.get("selected_niche"):
            st.error("Select an offer in Step 1 first to set the niche")
        elif not keywords_input.strip():
            st.error("Please enter at least one keyword")
        else:
            keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
            niche_edit = st.session_state.selected_niche

            with st.spinner(f"Generating editorial article from {len(keywords)} keywords..."):
                try:
                    editor = EditorialGenerator()
                    page = editor.generate(keywords, niche=niche_edit)

                    # Store in session state for preview + publish
                    st.session_state.editorial_page = page
                    # body_html already contains <h1>, so just use it directly
                    st.session_state.editorial_html = page.body_html

                    st.success(f"✓ Generated: {page.headline}")

                except Exception as e:
                    st.error(f"Generation failed: {e}")
                    logger.error(f"Editorial generation error: {e}")

    # Preview & Publish section
    if hasattr(st.session_state, "editorial_page") and st.session_state.editorial_page:
        st.divider()

        with st.expander("📄 Preview Generated Article", expanded=True):
            page = st.session_state.editorial_page
            st.subheader(page.headline)
            st.caption(page.subheadline)
            st.markdown(st.session_state.editorial_html, unsafe_allow_html=True)

        col_pub, col_edit = st.columns(2)

        with col_pub:
            if st.button("✅ Publish to /articles/", key="publish_editorial_btn"):
                with st.spinner("Publishing to GitHub..."):
                    try:
                        # Add article to site (goes to /articles/)
                        site_builder = PresellSiteBuilder()
                        article_path = site_builder.add_article(
                            page,
                            st.session_state.editorial_html,
                            folder="articles"
                        )

                        # Git commit + push
                        subprocess.run(
                            ["git", "add", "-f", str(article_path)],
                            check=True,
                            capture_output=True,
                            cwd=".",
                        )

                        subprocess.run(
                            ["git", "add", "-f", "output/presell_site/index.html"],
                            check=True,
                            capture_output=True,
                            cwd=".",
                        )

                        subprocess.run(
                            ["git", "commit", "-m", f"Publish: Editorial article '{page.headline}'"],
                            check=True,
                            capture_output=True,
                            cwd=".",
                        )

                        subprocess.run(
                            ["git", "push", "origin", "master"],
                            check=True,
                            capture_output=True,
                            cwd=".",
                        )

                        st.success("✓ Published to /articles/ + Vercel deploying!")
                        st.session_state.editorial_page = None
                        st.rerun()

                    except subprocess.CalledProcessError as e:
                        st.error(f"Git error: {e.stderr.decode()}")
                    except Exception as e:
                        st.error(f"Publish failed: {e}")
                        logger.error(f"Editorial publish error: {e}")

        with col_edit:
            if st.button("🔄 Generate New", key="regenerate_editorial_btn"):
                st.session_state.editorial_page = None
                st.rerun()


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
