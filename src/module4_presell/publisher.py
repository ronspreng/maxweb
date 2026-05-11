"""Publish advertorial pages to presell website and push to GitHub."""

import logging
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PresellPublisher:
    """Publish generated advertorials to presell website."""

    @staticmethod
    def publish_to_website(
        offer_slug: str,
        html_content: str,
        commit_message: str = None,
        auto_push: bool = True,
    ) -> bool:
        """
        Write HTML to presell_site/articles and optionally commit+push to GitHub.

        Args:
            offer_slug: URL-safe filename (e.g. "gluco-savior")
            html_content: HTML string to write
            commit_message: Git commit message (auto-generated if None)
            auto_push: Whether to commit and push to GitHub

        Returns:
            True if successful, False otherwise
        """
        try:
            # Write HTML to presell site
            articles_dir = Path("output/presell_site/articles")
            articles_dir.mkdir(parents=True, exist_ok=True)

            filepath = articles_dir / f"{offer_slug}.html"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"[publisher] Wrote: {filepath}")

            # Commit and push if requested
            if auto_push:
                if commit_message is None:
                    commit_message = f"Add advertorial: {offer_slug}"

                try:
                    # Stage file
                    subprocess.run(
                        ["git", "add", str(filepath)],
                        check=True,
                        capture_output=True,
                        cwd=".",
                    )

                    # Commit
                    subprocess.run(
                        ["git", "commit", "-m", commit_message],
                        check=True,
                        capture_output=True,
                        cwd=".",
                    )

                    # Push to GitHub
                    subprocess.run(
                        ["git", "push", "origin", "master"],
                        check=True,
                        capture_output=True,
                        cwd=".",
                    )

                    logger.info(f"[publisher] Pushed to GitHub: {commit_message}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"[publisher] Git error: {e.stderr.decode()}")
                    return False

            return True

        except Exception as e:
            logger.error(f"[publisher] Error: {e}")
            return False
