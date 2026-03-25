from __future__ import annotations

import unittest

from scripts.validate_contracts import main


class ContractValidationTests(unittest.TestCase):
    def test_contract_examples_match_schema(self) -> None:
        self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
