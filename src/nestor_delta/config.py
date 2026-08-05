"""Frozen Sprint 1 evaluation constants."""

SEEDS = (11, 23, 37, 41, 53)
SERIES_LENGTH = 600
LAG_WINDOW = 5
FEATURE_COLUMNS = ("target", "driver_a", "driver_b", "noise")
CSV_COLUMNS = ("step", "target", "driver_a", "driver_b", "noise")

TRAIN_ROWS = range(0, 420)
VALIDATION_ROWS = range(420, 510)
TEST_ROWS = range(510, 600)

TRAIN_LABEL_ROWS = range(5, 420)
VALIDATION_LABEL_ROWS = range(420, 510)
TEST_LABEL_ROWS = range(510, 600)
