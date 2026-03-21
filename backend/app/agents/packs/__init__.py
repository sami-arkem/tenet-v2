"""
Jurisdiction pack modules — organized by jurisdiction.
Each module defines a complete jurisdiction pack with all domains and controls.
"""

from app.agents.packs.us_pack import US_PACK_V1
from app.agents.packs.uae_pack import UAE_PACK_V1
from app.agents.packs.eu_pack import EU_PACK_V1
from app.agents.packs.sg_pack import SG_PACK_V1
from app.agents.packs.hk_pack import HK_PACK_V1
from app.agents.packs.au_pack import AU_PACK_V1
from app.agents.packs.ca_pack import CA_PACK_V1
from app.agents.packs.in_pack import IN_PACK_V1

__all__ = [
    "US_PACK_V1",
    "UAE_PACK_V1",
    "EU_PACK_V1",
    "SG_PACK_V1",
    "HK_PACK_V1",
    "AU_PACK_V1",
    "CA_PACK_V1",
    "IN_PACK_V1",
]
