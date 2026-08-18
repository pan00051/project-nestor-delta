# Dual-Window Evaluation: What Nestor Delta Learned from Nine Spanish Datasets

## Experiment Design

The evaluation assembled 15 candidate signals from nine Eurostat datasets after an availability gate required an exact 168-month axis, no missing months, no interpolation, and no silent replacement of unavailable series. Each case used separate train, validation, and test windows, with lag length, maximum selected signals, and the relationship threshold chosen only from validation performance. A validation baseline guard froze the final mode as baseline-only whenever the best Delta validation MAE did not improve on persistence. All parameters and fallback decisions were frozen before test, and each test window was evaluated exactly once with no post-test adjustment.

## Finding 1: The System Knows When to Retreat

Case A evaluated a normal-period test window from 2016 through 2019. During validation, the best Delta configuration produced MAE `0.745759`, which was worse than persistence MAE `0.720833`, so the baseline guard activated and froze the case as baseline-only. The 48-month test reported persistence MAE `1.112500` and left every Delta metric empty rather than copying or inventing a model result. When the evidence does not support a reliable Delta forecast, the system declines to fit one instead of forcing a prediction.

## Finding 2: Validation Success Does Not Survive Structural Breaks

Case B used 2018-2019 for validation and reserved the 2020-2021 pandemic window for one test evaluation. The validation-selected five-signal model improved on persistence by `7.11%`, but that advantage reversed under the structural break: test MAE was `4.490262` for Delta versus `4.095833` for persistence, making Delta `9.63%` worse. Relationships learned from a stable historical regime can fail when the data-generating environment changes abruptly. This is a general boundary of models built from historical relationships, not a defect unique to Nestor Delta.

## Core Insight

> **Resource-aware signal filtering is not the same as online shock detection.**

The current mechanism evaluates historical co-movement, filters weak relationships, and can retreat when validation already shows that a model is unhelpful. It cannot identify a previously unseen regime change at the moment it begins. The next meaningful evolution is online regime-change detection: a past-only mechanism that can recognize when the current environment no longer resembles the regime used for fitting.

## Why This Matters

Many forecasting systems fail silently: they continue producing authoritative-looking numbers after their assumptions stop holding. Nestor Delta is designed to make that failure visible and auditable through explicit baselines, empty Delta fields when no model is justified, frozen decisions, one-shot tests, and reports that preserve negative outcomes instead of tuning them away.

Across nine Eurostat datasets, 15 gated signals, 43 passing tests, and byte-reproducible validation artifacts, this experiment does not prove forecasting superiority. It demonstrates evaluation discipline: the ability to distinguish a justified retreat from a model failure, preserve both outcomes, and state exactly what the current mechanism can and cannot know.
