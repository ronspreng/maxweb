"""Export creatives to ad platform formats (MGID, Taboola, etc)."""

import csv
from io import StringIO
from .models import CreativeSet


class CreativeExporter:
    """Export CreativeSet to various ad platform formats."""

    @staticmethod
    def to_mgid_csv(creative_set: CreativeSet) -> str:
        """
        Export creatives to MGID-compatible CSV format.

        MGID format:
        - Title: max 75 chars
        - Description: max 160 chars
        - Can include multiple variations

        Returns:
            CSV string ready to copy-paste into MGID dashboard
        """
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["Title", "Description", "Hook Type"])
        
        writer.writeheader()
        for creative in creative_set.creatives:
            writer.writerow({
                "Title": creative.headline[:75],  # MGID max
                "Description": creative.description[:160],  # MGID max
                "Hook Type": creative.hook_type
            })
        
        return output.getvalue()

    @staticmethod
    def to_taboola_csv(creative_set: CreativeSet) -> str:
        """
        Export creatives to Taboola-compatible CSV format.

        Taboola format:
        - Headline: max 60 chars
        - Description: max 150 chars

        Returns:
            CSV string ready to copy-paste into Taboola dashboard
        """
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["Headline", "Description", "Hook Type"])
        
        writer.writeheader()
        for creative in creative_set.creatives:
            writer.writerow({
                "Headline": creative.headline[:60],  # Taboola max
                "Description": creative.description[:150],  # Taboola max
                "Hook Type": creative.hook_type
            })
        
        return output.getvalue()

    @staticmethod
    def to_generic_csv(creative_set: CreativeSet) -> str:
        """
        Generic CSV format with all info.

        Returns:
            CSV string with full creative details
        """
        output = StringIO()
        writer = csv.DictWriter(
            output, 
            fieldnames=["Offer", "Niche", "Headline", "Description", "Hook Type"]
        )
        
        writer.writeheader()
        for creative in creative_set.creatives:
            writer.writerow({
                "Offer": creative_set.offer_name,
                "Niche": creative_set.niche,
                "Headline": creative.headline,
                "Description": creative.description,
                "Hook Type": creative.hook_type
            })
        
        return output.getvalue()
