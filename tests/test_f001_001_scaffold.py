import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FoundationScaffoldTests(unittest.TestCase):
    def test_fastapi_application_is_declared(self) -> None:
        module = ast.parse((ROOT / "backend" / "ruvie" / "main.py").read_text())
        self.assertTrue(
            any(
                isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "app" for target in node.targets)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "FastAPI"
                for node in module.body
            )
        )

    def test_svelte_entry_points_are_present(self) -> None:
        package = json.loads((ROOT / "frontend" / "package.json").read_text())
        self.assertEqual(package["scripts"]["dev"], "vite")
        self.assertEqual(package["scripts"]["build"], "vite build")
        self.assertTrue((ROOT / "frontend" / "src" / "App.svelte").is_file())


if __name__ == "__main__":
    unittest.main()
