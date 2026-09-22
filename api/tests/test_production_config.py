from __future__ import annotations

import asyncio
import os
import unittest
from unittest import mock

from api import seed_file
from api.config import (
    DEV_ADMIN_PASSWORD,
    DEV_SECRET_KEY,
    MIN_ADMIN_PASSWORD_LENGTH,
    MIN_SECRET_KEY_LENGTH,
    dev_credentials_in_use,
    production_config_errors,
)
from api.main import app, lifespan


class TestProductionConfigErrors(unittest.TestCase):
    def test_development_mode_unset_returns_no_errors(self) -> None:
        self.assertEqual(production_config_errors({}), [])

    def test_development_mode_explicit_returns_no_errors(self) -> None:
        env = {
            "ASOUNDJOB_ENV": "development",
            "ADMIN_PASSWORD": DEV_ADMIN_PASSWORD,
            "ADMIN_SECRET_KEY": DEV_SECRET_KEY,
        }
        self.assertEqual(production_config_errors(env), [])

    def test_production_with_nothing_set_returns_two_errors(self) -> None:
        errors = production_config_errors({"ASOUNDJOB_ENV": "production"})
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("ADMIN_PASSWORD" in error for error in errors))
        self.assertTrue(any("ADMIN_SECRET_KEY" in error for error in errors))

    def test_production_with_dev_defaults_returns_two_errors(self) -> None:
        env = {
            "ASOUNDJOB_ENV": "production",
            "ADMIN_PASSWORD": DEV_ADMIN_PASSWORD,
            "ADMIN_SECRET_KEY": DEV_SECRET_KEY,
        }
        errors = production_config_errors(env)
        self.assertEqual(len(errors), 2)
        self.assertTrue(
            any("ADMIN_PASSWORD" in error and "development default" in error for error in errors)
        )
        self.assertTrue(
            any(
                "ADMIN_SECRET_KEY" in error and "development default" in error
                for error in errors
            )
        )

    def test_production_with_too_short_password(self) -> None:
        env = {
            "ASOUNDJOB_ENV": "production",
            "ADMIN_PASSWORD": "short1",
            "ADMIN_SECRET_KEY": "x" * MIN_SECRET_KEY_LENGTH,
        }
        errors = production_config_errors(env)
        self.assertEqual(
            errors,
            [f"ADMIN_PASSWORD is shorter than {MIN_ADMIN_PASSWORD_LENGTH} characters"],
        )

    def test_production_with_too_short_secret_key(self) -> None:
        env = {
            "ASOUNDJOB_ENV": "production",
            "ADMIN_PASSWORD": "x" * MIN_ADMIN_PASSWORD_LENGTH,
            "ADMIN_SECRET_KEY": "shortkey",
        }
        errors = production_config_errors(env)
        self.assertEqual(
            errors,
            [f"ADMIN_SECRET_KEY is shorter than {MIN_SECRET_KEY_LENGTH} characters"],
        )

    def test_production_with_good_values_returns_no_errors(self) -> None:
        env = {
            "ASOUNDJOB_ENV": "production",
            "ADMIN_PASSWORD": "correct-horse-battery-staple",
            "ADMIN_SECRET_KEY": "x" * MIN_SECRET_KEY_LENGTH,
        }
        self.assertEqual(production_config_errors(env), [])

    def test_env_matched_case_insensitively_and_stripped(self) -> None:
        errors = production_config_errors({"ASOUNDJOB_ENV": " Production "})
        self.assertEqual(len(errors), 2)

    def test_no_message_contains_the_secret_value(self) -> None:
        env = {
            "ASOUNDJOB_ENV": "production",
            "ADMIN_PASSWORD": "tiny-pw-1",
            "ADMIN_SECRET_KEY": "tiny-key-1",
        }
        errors = production_config_errors(env)
        self.assertEqual(len(errors), 2)
        combined = " ".join(errors)
        self.assertNotIn("tiny-pw-1", combined)
        self.assertNotIn("tiny-key-1", combined)


class TestDevCredentialsInUse(unittest.TestCase):
    def test_true_when_nothing_set(self) -> None:
        self.assertTrue(dev_credentials_in_use({}))

    def test_true_when_password_is_dev_default(self) -> None:
        env = {"ADMIN_PASSWORD": DEV_ADMIN_PASSWORD, "ADMIN_SECRET_KEY": "x" * 40}
        self.assertTrue(dev_credentials_in_use(env))

    def test_true_when_secret_key_is_dev_default(self) -> None:
        env = {"ADMIN_PASSWORD": "a-strong-password-value", "ADMIN_SECRET_KEY": DEV_SECRET_KEY}
        self.assertTrue(dev_credentials_in_use(env))

    def test_false_when_both_overridden(self) -> None:
        env = {
            "ADMIN_PASSWORD": "a-strong-password-value",
            "ADMIN_SECRET_KEY": "x" * 40,
        }
        self.assertFalse(dev_credentials_in_use(env))

    def test_false_in_production_regardless_of_values(self) -> None:
        env = {"ASOUNDJOB_ENV": "production"}
        self.assertFalse(dev_credentials_in_use(env))


class TestLifespanRefusesProductionDefaults(unittest.TestCase):
    def test_lifespan_raises_before_seed_file_enable(self) -> None:
        env = {
            "ASOUNDJOB_ENV": "production",
            "ADMIN_PASSWORD": "",
            "ADMIN_SECRET_KEY": "",
        }

        async def drive() -> None:
            async with lifespan(app):
                pass

        with mock.patch.dict(os.environ, env), mock.patch.object(
            seed_file, "enable"
        ) as mock_enable:
            with self.assertRaises(RuntimeError) as ctx:
                asyncio.run(drive())

        self.assertTrue(
            str(ctx.exception).startswith("refusing to start with ASOUNDJOB_ENV=production:")
        )
        mock_enable.assert_not_called()


if __name__ == "__main__":
    unittest.main()
