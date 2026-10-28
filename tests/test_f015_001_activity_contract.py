"""Contract for administrator-controlled account activity."""
import unittest

from pydantic import ValidationError
from ruvie.contracts import admin


class AccountActivityContractTests(unittest.TestCase):
    def test_accepts_only_boolean_activity(self):
        contract = getattr(admin, "SetAccountActivityRequest", None)
        self.assertIsNotNone(contract, "activity contract is missing")
        for value in (True, False):
            self.assertIs(contract.model_validate({"is_active": value}).is_active, value)
        for value in (None, "true", 1, 0, [], {}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                contract.model_validate({"is_active": value})
        for body in ({}, [], {"is_active": True, "actor": "other"},
                     {"is_active": True, "system_role": "admin"},
                     {"is_active": True, "password": "secret"}):
            with self.subTest(body=body), self.assertRaises(ValidationError):
                contract.model_validate(body)

    def test_identity_update_rejects_activity(self):
        with self.assertRaises(ValidationError):
            admin.UpdateAccountRequest.model_validate({"is_active": False})
