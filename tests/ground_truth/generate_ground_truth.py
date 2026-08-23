#!/usr/bin/env python3
"""
Nestor Delta — ground-truth fixture generator (M0).

Run ONCE; commit the generated CSVs and the manifest. Tests read the committed
files, never regenerate. Rationale: the tests must validate the S1-S10 pipeline,
not the RNG. Regenerating at test time would make results depend on the numpy
version, which is unacceptable for a product whose central claim is
reproducibility.

Construction
------------
Everything is designed in the DIFFERENCED domain and then integrated (cumsum)
into levels. A user therefore uploads levels and declares `diff`, and after the
pipeline differences them it recovers exactly the stationary series designed
here. This matches the real upload path instead of testing a synthetic shortcut.

S-GT-1 (positive control)
    true_driver leads synthetic_target by LAG months with a negative sign.
    Three independent decoys are present so the same run also exercises
    multiple-comparison correction: the gate must select the real driver AND
    reject all three decoys.

S-GT-2 (negative control)
    Same shape, no injected relationship anywhere. A detector that selects
    nothing and a detector that selects everything are equally broken; the
    positive control alone cannot tell them apart.

Usage
-----
    python generate_ground_truth.py            # writes fixtures/ + manifest
    python generate_ground_truth.py --sweep    # S-GT-4 sensitivity sweep inputs
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- parameters
START = "2008-01"
N_MONTHS = 216                 # 18 years — matches the bundled-case shape
TRAIN_END = "2023-12"          # month 192; leaves 24 months out of sample
MAX_LAG = 3                    # lag window handed to the pipeline

LAG = 2                        # injected lag — interior to MAX_LAG on purpose
TARGET_R = -0.55               # injected correlation in the differenced domain
N_DECOYS = 3

SEED_POS = 20260823          # search base; the accepted seed is screened, see below
SEED_NEG = 20260824

# ------------------------------------------------------------ seed screening
# Seeds are SCREENED, and this is deliberate. The screen is applied to
# properties of the DATA (max spurious lagged correlation), never to the
# pipeline's output. Screening on data properties is fixture specification;
# screening on pipeline output would be rigging the test, and is forbidden.
#
# Why it is necessary: at n=215 the standard error of a sample correlation is
# ~0.068, so across 4 signals x 4 lags an unscreened "pure noise" draw routinely
# throws a spurious |r| ~ 0.20 -- above the noise floor the contract's own
# example uses (0.1896). Such a seed would make the negative control fail while
# the pipeline is behaving correctly. A deterministic CI control must be
# unambiguous; the statistical question is answered by the multi-seed test
# (S-GT-2b) instead.
MAX_SPURIOUS_R = 0.13        # every non-injected correlation must sit below this
TRUE_R_BAND = (0.50, 0.62)   # accepted |peak| for the injected relation
RUNNER_UP_MAX = 0.25         # injected signal's 2nd-best lag must be clearly beaten
SEED_SEARCH_LIMIT = 20000

OUT = Path(__file__).parent / "fixtures"


def beta_for_r(r: float, sigma_eps: float = 1.0) -> float:
    """Injection coefficient that yields corr(y_t, x_{t-k}) == r.

    y_t = beta * x_{t-k} + eps_t,  x ~ N(0,1), eps ~ N(0, sigma^2)
    =>  r = beta / sqrt(beta^2 + sigma^2)
    =>  beta = r * sigma / sqrt(1 - r^2)
    """
    return r * sigma_eps / np.sqrt(1.0 - r * r)


def dates(n: int = N_MONTHS) -> list[str]:
    return [d.strftime("%Y-%m") for d in pd.period_range(START, periods=n, freq="M").to_timestamp()]


def integrate(d: np.ndarray, base: float = 100.0) -> np.ndarray:
    """Differenced series -> level series, so the fixture looks like an index."""
    return np.round(base + np.cumsum(d), 4)


def build_positive(seed: int = SEED_POS, r: float = TARGET_R, lag: int = LAG) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = N_MONTHS
    beta = beta_for_r(r)

    x = rng.standard_normal(n)                       # true driver, differenced
    eps = rng.standard_normal(n)                     # target innovation

    y = eps.copy()
    y[lag:] += beta * x[: n - lag]                   # inject: y_t = beta*x_{t-lag} + eps_t

    cols = {
        "date": dates(n),
        "synthetic_target": integrate(y),
        "true_driver": integrate(x),
    }
    for i in range(1, N_DECOYS + 1):
        cols[f"decoy_{i}"] = integrate(rng.standard_normal(n))
    return pd.DataFrame(cols)


def build_negative(seed: int = SEED_NEG) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = N_MONTHS
    cols = {"date": dates(n), "synthetic_target": integrate(rng.standard_normal(n))}
    for i in range(1, N_DECOYS + 2):                 # 4 candidates, all pure noise
        cols[f"noise_{i}"] = integrate(rng.standard_normal(n))
    return pd.DataFrame(cols)


# ------------------------------------------------------- S-GT-5 drift profiles
# S-GT-1 injects a TIME-INVARIANT relationship. That is the upper bound for
# temporal stability, not a realistic one: real relationships drift, weaken, and
# die. Holding beta_max fixed at the S-GT-1 level and varying ONLY the time
# profile isolates the effect of drift from the effect of strength, which is
# what makes the resulting stability numbers comparable.
#
# Two questions these fixtures answer, neither of which S-GT-1/2 can:
#   1. Is `stability >= 0.45` reachable by a relationship that is real but
#      non-stationary? If not, no real dataset will ever produce `outcome: ok`,
#      and that is a calibration problem masquerading as product discipline.
#   2. Does the S9 lifecycle state machine actually track a relationship that
#      STOPS? A relation that died five years ago must not read as `stable`.
DRIFT_PROFILES = {
    "constant":     "beta constant — reference case, same shape as S-GT-1",
    "linear_decay": "beta falls linearly from beta_max to 0 across the sample",
    "regime_off":   "beta_max for the first 70% of months, then exactly 0",
    "regime_late":  "exactly 0 for the first 30% of months, then beta_max",
    "intermittent": "beta_max and 0 in alternating 24-month blocks",
}


def _beta_path(profile: str, n: int, beta_max: float) -> np.ndarray:
    t = np.arange(n)
    if profile == "constant":
        return np.full(n, beta_max)
    if profile == "linear_decay":
        return beta_max * (1.0 - t / (n - 1))
    if profile == "regime_off":
        return np.where(t < int(0.70 * n), beta_max, 0.0)
    if profile == "regime_late":
        return np.where(t < int(0.30 * n), 0.0, beta_max)
    if profile == "intermittent":
        return np.where((t // 24) % 2 == 0, beta_max, 0.0)
    raise ValueError(profile)


def build_drifting(profile: str, seed: int = SEED_POS, lag: int = LAG) -> pd.DataFrame:
    """Same construction as S-GT-1, but beta varies over time by `profile`."""
    rng = np.random.default_rng(seed)
    n = N_MONTHS
    beta = _beta_path(profile, n, beta_for_r(TARGET_R))

    x = rng.standard_normal(n)
    eps = rng.standard_normal(n)
    y = eps.copy()
    y[lag:] += beta[lag:] * x[: n - lag]

    cols = {"date": dates(n), "synthetic_target": integrate(y), "true_driver": integrate(x)}
    for i in range(1, N_DECOYS + 1):
        cols[f"decoy_{i}"] = integrate(rng.standard_normal(n))
    return pd.DataFrame(cols)


def _emit_drift() -> dict:
    out = {}
    for profile, description in DRIFT_PROFILES.items():
        df = build_drifting(profile)
        path = OUT / f"s_gt_5_{profile}.csv"
        df.to_csv(path, index=False)
        # Realised correlation by segment. The LAST QUARTER is the number that
        # matters for lifecycle: it says how much of the relationship is still
        # present at the end of the sample, which is what `lifecycle.state`
        # claims to describe.
        td = np.diff(df["synthetic_target"].to_numpy())
        sd = np.diff(df["true_driver"].to_numpy())
        q = len(td) // 4
        out[profile] = {
            "file": path.name, "sha256": sha256(path), "description": description,
            "full_sample_abs_r": round(abs(lagged_corr(td, sd, LAG)), 4),
            "first_quarter_abs_r": round(abs(lagged_corr(td[:q], sd[:q], LAG)), 4),
            "last_quarter_abs_r": round(abs(lagged_corr(td[-q:], sd[-q:], LAG)), 4),
            "request": request_payload(df, "synthetic_target"),
        }
    return out


# ---------------------------------------------------------------- diagnostics
def lagged_corr(target_d: np.ndarray, signal_d: np.ndarray, lag: int) -> float:
    if lag == 0:
        a, b = target_d, signal_d
    else:
        a, b = target_d[lag:], signal_d[:-lag]
    return float(np.corrcoef(a, b)[0, 1])


def diagnose(df: pd.DataFrame, target: str, max_lag: int = MAX_LAG) -> dict:
    """Properties of the FIXTURE itself. Independent of the pipeline — this is
    what makes the fixture trustworthy before any pipeline assertion runs."""
    td = np.diff(df[target].to_numpy())
    out = {}
    for col in df.columns:
        if col in ("date", target):
            continue
        sd = np.diff(df[col].to_numpy())
        corrs = {k: round(lagged_corr(td, sd, k), 4) for k in range(max_lag + 1)}
        argmax = max(corrs, key=lambda k: abs(corrs[k]))
        out[col] = {
            "corr_by_lag": corrs,
            "argmax_lag": argmax,
            "peak_corr": corrs[argmax],
            "level_lag1_acf": round(float(np.corrcoef(df[col].to_numpy()[1:], df[col].to_numpy()[:-1])[0, 1]), 4),
        }
    return out


def _max_spurious(df: pd.DataFrame, target: str, exclude: tuple[str, ...] = ()) -> float:
    d = diagnose(df, target)
    vals = [abs(c) for k, v in d.items() if k not in exclude for c in v["corr_by_lag"].values()]
    return max(vals) if vals else 0.0


def screen_negative(base: int = SEED_NEG) -> tuple[int, pd.DataFrame]:
    """First seed whose pure-noise draw carries no spurious correlation that a
    correctly-calibrated gate could defensibly select."""
    for seed in range(base, base + SEED_SEARCH_LIMIT):
        df = build_negative(seed)
        if _max_spurious(df, "synthetic_target") < MAX_SPURIOUS_R:
            return seed, df
    raise RuntimeError("no negative seed satisfied the screen")


def screen_positive(base: int = SEED_POS) -> tuple[int, pd.DataFrame]:
    """First seed where the injected relation lands cleanly at LAG with the
    intended strength AND the decoys stay quiet."""
    for seed in range(base, base + SEED_SEARCH_LIMIT):
        df = build_positive(seed=seed)
        d = diagnose(df, "synthetic_target")
        t = d["true_driver"]
        others = [abs(c) for k, v in d.items() if k != "true_driver" for c in v["corr_by_lag"].values()]
        runner_up = max(abs(c) for k, c in t["corr_by_lag"].items() if int(k) != LAG)
        if (t["argmax_lag"] == LAG
                and TRUE_R_BAND[0] <= abs(t["peak_corr"]) <= TRUE_R_BAND[1]
                and runner_up < RUNNER_UP_MAX
                and max(others) < MAX_SPURIOUS_R):
            return seed, df
    raise RuntimeError("no positive seed satisfied the screen")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request_payload(df: pd.DataFrame, target: str) -> dict:
    signals = [c for c in df.columns if c not in ("date", target)]
    return {
        "date_column": "date",
        "target": target,
        "candidate_signals": signals,
        "transform_declarations": {c: "diff" for c in [target] + signals},
        "train_end": TRAIN_END,
        "lag_window": MAX_LAG,
    }


def _emit_sweep() -> dict:
    """S-GT-4 inputs. Regenerable at will — these are measurement inputs, not
    frozen controls, so no drift guard applies to them."""
    sweep = {}
    for r in (-0.15, -0.20, -0.25, -0.30, -0.35, -0.40, -0.45, -0.50, -0.55, -0.60):
        key = f"sweep_r{abs(r):.2f}".replace(".", "")
        d = build_positive(seed=SEED_POS, r=r)
        p = OUT / f"{key}.csv"
        d.to_csv(p, index=False)
        sweep[key] = {"file": p.name, "sha256": sha256(p), "injected_r": r,
                      "request": request_payload(d, "synthetic_target")}
    return sweep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true", help="also emit S-GT-4 sweep fixtures")
    ap.add_argument("--drift", action="store_true", help="emit S-GT-5 drift fixtures")
    ap.add_argument("--force", action="store_true",
                    help="regenerate the frozen controls too (see the guard below)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    # ---- drift guard -----------------------------------------------------
    # The two control fixtures are FROZEN. Re-running this script (for example
    # to add --sweep files) must not silently rewrite them: numpy's Generator
    # stream and pandas' CSV float formatting are not guaranteed identical
    # across versions, so a regeneration on a different machine can produce
    # byte-different CSVs with new hashes. S-GT-0 would still pass -- the
    # manifest is rewritten alongside -- while the ground truth every threshold
    # decision was calibrated against had quietly moved. Regenerating is
    # allowed; doing it by accident is not.
    manifest_path = OUT / "manifest.json"
    frozen = [OUT / "s_gt_1_positive.csv", OUT / "s_gt_2_negative.csv"]
    if all(p.exists() for p in frozen) and manifest_path.exists() and not args.force:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        print("controls already frozen; leaving them untouched (--force to regenerate)")
        wrote = []
        if args.sweep:
            manifest["sweep"] = _emit_sweep()
            wrote.append(f"{len(manifest['sweep'])} sweep")
        if args.drift:
            manifest["drift"] = _emit_drift()
            wrote.append(f"{len(manifest['drift'])} drift")
        if wrote:
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print("wrote " + " + ".join(wrote) + " fixtures")
        else:
            print("nothing to do")
        return

    seed_pos, df_pos = screen_positive()
    seed_neg, df_neg = screen_negative()

    manifest: dict = {
        "spec": {
            "n_months": N_MONTHS, "start": START, "train_end": TRAIN_END,
            "max_lag": MAX_LAG, "injected_lag": LAG, "injected_r": TARGET_R,
            "injected_beta": round(beta_for_r(TARGET_R), 6),
            "seed_positive": seed_pos, "seed_negative": seed_neg,
            "screen": {
                "applied_to": "data properties only, never pipeline output",
                "max_spurious_abs_r": MAX_SPURIOUS_R,
                "true_r_band": list(TRUE_R_BAND),
                "runner_up_max_abs_r": RUNNER_UP_MAX,
            },
        },
        "fixtures": {},
    }

    for name, df, target in (
        ("s_gt_1_positive", df_pos, "synthetic_target"),
        ("s_gt_2_negative", df_neg, "synthetic_target"),
    ):
        path = OUT / f"{name}.csv"
        df.to_csv(path, index=False)
        manifest["fixtures"][name] = {
            "file": path.name,
            "nature": "calibration control — synthetic, not a real-world causal case",
            "sha256": sha256(path),
            "rows": len(df),
            "request": request_payload(df, target),
            "diagnostics": diagnose(df, target),
        }

    if args.sweep:
        manifest["sweep"] = _emit_sweep()
    if args.drift:
        manifest["drift"] = _emit_drift()

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2)[:4000])


if __name__ == "__main__":
    main()
