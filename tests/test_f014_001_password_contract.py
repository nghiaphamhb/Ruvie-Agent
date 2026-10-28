"""Password change requests preserve secrets and reject malformed values."""
import unittest

from pydantic import ValidationError

from ruvie.contracts.auth import ChangePasswordRequest


class ChangePasswordContractTests(unittest.TestCase):
    def valid(self, **changes):
        values = {
            "current_password": "x",
            "new_password": "new-password-123",
            "password_confirmation": "new-password-123",
        }
        values.update(changes)
        return ChangePasswordRequest(**values)

    def test_accepts_limits_and_preserves_unicode_and_whitespace(self):
        current = " x " + "😀" * 1021
        new = "é" * 12
        request = self.valid(current_password=current, new_password=new, password_confirmation=new)
        self.assertEqual(request.current_password, current)
        self.assertEqual(request.new_password, new)

    def test_rejects_out_of_range_password_lengths(self):
        for field, value in (
            ("current_password", ""),
            ("current_password", "x" * 1025),
            ("new_password", "x" * 11),
            ("new_password", "x" * 129),
            ("password_confirmation", "x" * 11),
            ("password_confirmation", "x" * 129),
        ):
            with self.subTest(field=field, length=len(value)):
                with self.assertRaises(ValidationError):
                    self.valid(**{field: value})

    def test_requires_strict_string_fields_and_rejects_extra_fields(self):
        for field, value in (
            ("current_password", None),
            ("current_password", 7),
            ("new_password", True),
            ("password_confirmation", ["new-password-123"]),
        ):
            with self.subTest(field=field, value_type=type(value).__name__):
                with self.assertRaises(ValidationError):
                    self.valid(**{field: value})
        with self.assertRaises(ValidationError):
            self.valid(user_id="attacker-selected-id")

    def test_mismatched_confirmation_has_fixed_error_type(self):
        with self.assertRaises(ValidationError) as raised:
            self.valid(password_confirmation="different-password")
        self.assertIn(
            "password_confirmation_mismatch",
            {error["type"] for error in raised.exception.errors()},
        )
        self.assertNotIn("new-password-123", str(raised.exception))

    def test_passwords_are_hidden_from_repr(self):
        request = self.valid(
            current_password="current-secret-marker",
            new_password="new-secret-marker",
            password_confirmation="new-secret-marker",
        )
        rendered = repr(request)
        self.assertNotIn("current-secret-marker", rendered)
        self.assertNotIn("new-secret-marker", rendered)


if __name__ == "__main__":
    unittest.main()
