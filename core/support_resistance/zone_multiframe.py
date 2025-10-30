from .zone_builder import get_active_zones
from .multi_tf_merger import merge_timeframe_zones
import logging

logger = logging.getLogger("ZoneMultiTF")


def build_zones_multi_tf(df_dict, fut_df_dict=None, include_vwap=True, top_n=None):
    """
    Run S/R zone detection across multiple timeframes and merge the results.

    Args:
        df_dict (dict): { '5m': DataFrame, '15m': DataFrame, ... }
        fut_df_dict (dict): Matching futures dataframes by timeframe.
        include_vwap (bool): Whether to include VWAP zones
        top_n (int, optional): Return only top N zones by normalized_score

    Returns:
        List of merged zone dicts.
    """
    zones_by_tf = {}
    all_atrs = []
    # Compute avg ATR across timeframes
    for tf, df in df_dict.items():
        if 'atr' in df.columns:
            all_atrs.append(df['atr'].dropna().mean())
    avg_atr = sum(all_atrs) / len(all_atrs) if all_atrs else 20
    # Dynamic proximity (based on volatility)
    proximity = max(avg_atr * 0.75, 15)

    for tf in df_dict:
        try:
            zones = get_active_zones(
                df_dict[tf],
                fut_df=fut_df_dict.get(tf) if fut_df_dict else None,
                include_vwap=include_vwap,
                tf_label=tf
            )
            zones_by_tf[tf] = zones
            logger.info(f"[{tf}] Zones generated: {len(zones)}")
        except Exception as e:
            logger.warning(f"[{tf}] Zone generation failed: {e}")
            zones_by_tf[tf] = []

    merged_zones = merge_timeframe_zones(zones_by_tf, proximity=proximity)
    logger.info(f"[MERGE] Total merged zones: {len(merged_zones)}")

    # Sort and optionally trim
    merged_zones.sort(key=lambda z: z.get("normalized_score", 0), reverse=True)
    if top_n:
        merged_zones = merged_zones[:top_n]
        logger.info(f"[TRIM] Top {top_n} zones retained")

    return merged_zones
