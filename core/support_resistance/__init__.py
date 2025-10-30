# Directory: core/support_resistance/
# Module: __init__.py

"""
Support & Resistance Detection Toolkit (Intraday Grade)

Submodules:
- swing_detector: Detects swing highs/lows
- zone_cluster: Clusters swing levels using DBSCAN or fallback
- volume_profile: Constructs price-volume histogram zones
- multi_tf_merger: Merges zones from multiple timeframes
- zone_scorer: Scores zones by strength, recency, volume
- anchor_vwap: Anchored VWAP zone detection
- zone_filter: Applies rules like min gap, zone width, fallback

Usage:
from core.support_resistance.main import calculate_active_zones

Author: Abhishek G
"""

from .swing_detector import detect_swings
from .zone_cluster import cluster_zones
from .volume_profile import get_volume_profile_zones
from .multi_tf_merger import merge_timeframe_zones
from .zone_scorer import score_zones
from .anchor_vwap import get_vwap_zones
from .zone_filter import filter_and_validate_zones
