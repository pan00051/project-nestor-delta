"""Source-revision resolution, asserted identically for both implementations.

`nestor_delta_web` may not import anything named `nestor_delta*`
(test_website_frontend.test_frontend_never_imports_nestor_delta), so the helper
is duplicated per package. Tests are not under that restriction, so this module
imports both copies and drives them through one table. Any behavioural drift
between the two fails here.
"""

from __future__ import annotations

import unittest
from unittest import mock

from nestor_delta_service import build_info as service_build_info
from nestor_delta_web import build_info as web_build_info

IMPLEMENTATIONS = (
    ("service", service_build_info),
    ("web", web_build_info),
)

PLATFORM = "RAILWAY_GIT_COMMIT_SHA"
MANUAL = "NESTOR_BUILD_SHA"

VALID_A = "a1b2c3d4e5f6"
VALID_B = "0123456789ab"

# (label, env, expected). Every case has both env vars fully controlled and the
# git fallback disabled, so the expected value is exact rather than incidental.
CASES = (
    ("platform wins over manual", {PLATFORM: VALID_A, MANUAL: VALID_B}, VALID_A),
    ("manual used when platform absent", {MANUAL: VALID_B}, VALID_B),
    ("blank platform never shadows manual", {PLATFORM: "   ", MANUAL: VALID_B}, VALID_B),
    ("empty platform never shadows manual", {PLATFORM: "", MANUAL: VALID_B}, VALID_B),
    ("malformed platform is skipped", {PLATFORM: "not-a-sha", MANUAL: VALID_B}, VALID_B),
    ("surrounding whitespace is stripped", {MANUAL: f"  {VALID_A}\n"}, VALID_A),
    ("uppercase is normalised", {MANUAL: VALID_A.upper()}, VALID_A),
    ("six characters is too short", {MANUAL: "a1b2c3", PLATFORM: VALID_A}, VALID_A),
    ("forty-one characters is too long", {MANUAL: "a" * 41, PLATFORM: VALID_A}, VALID_A),
    ("forty characters is accepted", {MANUAL: "b" * 40}, "b" * 40),
    ("seven characters is accepted", {MANUAL: "abcdef1"}, "abcdef1"),
    ("no usable source falls back to unknown", {}, "unknown"),
    ("all sources malformed falls back to unknown", {PLATFORM: " ", MANUAL: "zzzzzzz"}, "unknown"),
)


class SourceRevisionResolution(unittest.TestCase):
    def _detect_with(self, module, env):
        """Run _detect with a fully controlled env and no git fallback."""
        with mock.patch.dict(module.os.environ, env, clear=True):
            with mock.patch.object(
                module.subprocess, "run", side_effect=FileNotFoundError("no git")
            ):
                return module._detect()

    def test_resolution_table(self) -> None:
        for label, env, expected in CASES:
            results = {}
            for name, module in IMPLEMENTATIONS:
                with self.subTest(case=label, implementation=name):
                    actual = self._detect_with(module, env)
                    self.assertEqual(actual, expected)
                results[name] = self._detect_with(module, env)
            self.assertEqual(
                results["service"],
                results["web"],
                f"implementations drifted on: {label}",
            )

    def test_git_fallback_is_used_when_no_env_var_is_set(self) -> None:
        completed = mock.Mock(returncode=0, stdout=f"{VALID_A}\n")
        for name, module in IMPLEMENTATIONS:
            with self.subTest(implementation=name):
                with mock.patch.dict(module.os.environ, {}, clear=True):
                    with mock.patch.object(module.subprocess, "run", return_value=completed):
                        self.assertEqual(module._detect(), VALID_A)

    def test_git_failure_falls_through_to_unknown(self) -> None:
        failed = mock.Mock(returncode=128, stdout="")
        for name, module in IMPLEMENTATIONS:
            with self.subTest(implementation=name):
                with mock.patch.dict(module.os.environ, {}, clear=True):
                    with mock.patch.object(module.subprocess, "run", return_value=failed):
                        self.assertEqual(module._detect(), module.UNKNOWN)

    def test_git_output_is_validated_like_any_other_source(self) -> None:
        garbage = mock.Mock(returncode=0, stdout="fatal: not a repository\n")
        for name, module in IMPLEMENTATIONS:
            with self.subTest(implementation=name):
                with mock.patch.dict(module.os.environ, {}, clear=True):
                    with mock.patch.object(module.subprocess, "run", return_value=garbage):
                        self.assertEqual(module._detect(), module.UNKNOWN)

    def test_unknown_constant_agrees(self) -> None:
        self.assertEqual(service_build_info.UNKNOWN, web_build_info.UNKNOWN)
        self.assertEqual(service_build_info.UNKNOWN, "unknown")


if __name__ == "__main__":
    unittest.main()
