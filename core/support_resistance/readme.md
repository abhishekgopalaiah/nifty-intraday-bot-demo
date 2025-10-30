Perfect — here's a clean, modular breakdown of **all the scripts/modules** I’d provide to build a **world-class intraday Support & Resistance system** inside your `core/support_resistance/` directory.

---

## 📁 Proposed Files in `core/support_resistance/`

| Filename | Purpose |
| -------- | ------- |

### 🔹 **1. `swing_detector.py`**

> Detects swing highs/lows using a centered rolling window.

* Optionally filters based on volume.
* Supports both price-based and wicks-based detection.

---

### 🔹 **2. `zone_cluster.py`**

> Uses DBSCAN or fallback quantiles to cluster swing points into zones.

* Adds zone width control and minimum required points.
* Returns `(zone_low, zone_high, strength, last_touched)`.

---

### 🔹 **3. `volume_profile.py`**

> Constructs **price-volume histogram** (from NIFTY Futures).

* Identifies:

  * POC (Point of Control)
  * HVNs (High Volume Nodes)
  * LVNs (Low Volume Nodes)
* Translates these into valid S/R zones.

---

### 🔹 **4. `multi_tf_merger.py`**

> Runs zone detection on 5m, 15m, 1h timeframes.

* Merges overlapping zones (within tolerance).
* Increases score for zones that appear across TFs.

---

### 🔹 **5. `zone_scorer.py`**

> Assigns a composite score to each zone:

* Recency decay
* Touch frequency
* Volume validation
* Timeframe alignment
* Pattern reject memory

---

### 🔹 **6. `anchor_vwap.py`**

> Anchors VWAP from meaningful points (open, yesterday's high/low, breakout bar).

* Converts VWAP rejection points into zones.
* Helps confirm S/R zones from price structure.

---

### 🔹 **7. `zone_filter.py`**

> Final validation rules:

* Min/max zone width
* Min gap between S/R
* Rejects overlapping or too-tight zones
* Enforces volatility-aware zone adjustments

---

### 🔹 **8. `zone_builder.py` (or `main.py`)**

> **Main pipeline** that:

* Calls all submodules
* Merges zone sources (swings + volume profile + VWAP)
* Scores + filters zones
* Outputs standardized format used by `signal_engine.py`

```python
from support_resistance.zone_builder import get_active_zones
```

---

### 🔹 **9. `__init__.py`**

> Clean re-exports for ease of importing:

```python
from .zone_builder import get_active_zones
```

---

## ✅ Output from the System:

Each zone object will look like:

```python
{
  "type": "resistance",
  "band": (25520, 25540),
  "score": 9.2,
  "sources": ["swing", "vwap"],
  "timeframes": ["5m", "15m"],
  "touch_count": 3,
  "volume_cluster": True,
  "flipped": False,
  "last_touched": "2025-07-03 13:15"
}
```

This is what your `signal_engine.py` will consume — clean, scored, and explainable.

---

## 🎯 Ready to Begin?

Let me know where you'd like to start:

* `swing_detector.py` (first building block), or
* `zone_builder.py` (top-down flow first)?

I’ll generate the full code module by module.
