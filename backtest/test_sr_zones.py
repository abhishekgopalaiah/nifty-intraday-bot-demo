import pandas as pd
from core.support_resistance.zone_multiframe import build_zones_multi_tf


def load_csv_data():
    return {
        '5m': pd.read_csv('sample_data/nifty_spot_5m.csv', parse_dates=['timestamp']),
        '15m': pd.read_csv('sample_data/nifty_spot_15m.csv', parse_dates=['timestamp']),
        '1h': pd.read_csv('sample_data/nifty_spot_1h.csv', parse_dates=['timestamp']),
    }


def count_passed_zones(zones, ltp):
    """
    Count how many support/resistance zones have been passed by the current LTP.
    """
    passed_support = 0
    passed_resistance = 0

    for z in zones:
        low, high = z['band']
        if z['type'] == 'support' and high < ltp:
            passed_support += 1
        elif z['type'] == 'resistance' and low > ltp:
            passed_resistance += 1

    return passed_support, passed_resistance


def print_zones(zones, price):
    support = [z for z in zones if z['type'] == 'support']
    resistance = [z for z in zones if z['type'] == 'resistance']
    vp = [z for z in zones if z['type'] == 'vp_zone']
    vwap = [z for z in zones if z.get('vwap_zone')]

    passed_s, passed_r = count_passed_zones(zones, price)

    print(f"\n🔍 LTP: {price}")
    print(f"Passed Zones: Support={passed_s} | Resistance={passed_r}")
    print(f"SUPPORT ZONES:")
    for z in support:
        print(f"  - Band: {z['band']}, Score: {z.get('score')}, TF: {z.get('timeframes')}")

    print(f"\nRESISTANCE ZONES:")
    for z in resistance:
        print(f"  - Band: {z['band']}, Score: {z.get('score')}, TF: {z.get('timeframes')}")

    print(f"\nVOLUME PROFILE ZONES:")
    for z in vp:
        print(f"  - Band: {z['band']}, TF: {z.get('timeframes')}")

    print(f"\VWAP ZONES:")
    for z in vwap:
        print(f"  - Band: {z['band']}, TF: {z.get('timeframes')}")

    nearest = min(zones, key=lambda z: abs(z['price'] - price), default=None)
    if nearest:
        distance = abs(nearest['price'] - price)
        if distance > 100:
            print(f"⚠️ WARNING: Nearest zone {nearest['type']} is {distance:.2f} pts away from LTP {price}")


def main():
    spot_dict = load_csv_data()
    all_timestamps = spot_dict['5m']['timestamp']

    for ts in all_timestamps:
        spot_sliced = {
            tf: df[df['timestamp'] <= ts] for tf, df in spot_dict.items()
        }

        if any(len(df) < 20 for df in spot_sliced.values()):
            continue  # skip early timestamps without enough data

        zones = build_zones_multi_tf(spot_sliced)
        ltp = spot_sliced['5m'].iloc[-1]['close']

        print(f"\n===== {ts} | LTP: {ltp} =====")
        print_zones(zones, ltp)


if __name__ == '__main__':
    main()
