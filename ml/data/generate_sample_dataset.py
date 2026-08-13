"""
Generates a small synthetic network-traffic-style CSV for exercising the
Phase 2 pipeline end-to-end without waiting on a real dataset download
(CIC-IDS2017 is ~8GB; NSL-KDD requires registration).

Structurally mimics NSL-KDD: numeric flow features + a categorical
protocol_type column + a multi-class label. Includes two "rare" attack
classes (u2r, worm) explicitly meant to be marked UNKNOWN_HOLDOUT later,
simulating zero-day attacks the model never trains on.

Usage:
    python ml/data/generate_sample_dataset.py --rows 5000 --out sample_ids_dataset.csv
"""
import argparse

import numpy as np
import pandas as pd


CLASS_PROFILES = {
    # name: (fraction of rows, duration mean/std, bytes mean/std)
    "benign": (0.60, (5, 2), (500, 150)),
    "dos": (0.15, (0.5, 0.3), (50, 20)),
    "probe": (0.10, (3, 1), (200, 80)),
    "r2l": (0.08, (8, 3), (1000, 300)),
    "u2r": (0.04, (15, 5), (2000, 500)),      # intended as unknown-holdout
    "worm": (0.03, (0.2, 0.1), (10, 5)),       # intended as unknown-holdout
}

PROTOCOLS = ["tcp", "udp", "icmp"]


def generate(n_rows: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []

    for class_name, (fraction, (dur_mean, dur_std), (bytes_mean, bytes_std)) in CLASS_PROFILES.items():
        n = int(n_rows * fraction)
        durations = np.clip(rng.normal(dur_mean, dur_std, n), 0.01, None)
        byte_counts = np.clip(rng.normal(bytes_mean, bytes_std, n), 1, None)
        protocols = rng.choice(PROTOCOLS, n)
        src_bytes = byte_counts * rng.uniform(0.4, 0.6, n)
        dst_bytes = byte_counts - src_bytes
        wrong_fragment = rng.poisson(0.1 if class_name in ("dos", "worm") else 0.01, n)

        for i in range(n):
            rows.append({
                "duration": round(float(durations[i]), 3),
                "protocol_type": protocols[i],
                "src_bytes": round(float(src_bytes[i]), 2),
                "dst_bytes": round(float(dst_bytes[i]), 2),
                "wrong_fragment": int(wrong_fragment[i]),
                "count": int(rng.poisson(20 if class_name == "dos" else 5)),
                "label": class_name,
            })

    df = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--out", type=str, default="sample_ids_dataset.csv")
    args = parser.parse_args()

    df = generate(args.rows)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out}")
    print(df["label"].value_counts())


if __name__ == "__main__":
    main()
