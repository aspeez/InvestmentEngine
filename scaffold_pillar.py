"""
Scaffold a new pillar directory with config and engine script.
"""

import argparse
import json
import shutil
from pathlib import Path


def scaffold_pillar(pillar_name: str, parent_dir: Path = Path(".")/"") -> None:
    pillar_dir = parent_dir / pillar_name
    pillar_dir.mkdir(exist_ok=True)

    config_path = pillar_dir / "pillar_tickers.json"
    if not config_path.exists():
        config = {"Default": []}
        config_path.write_text(json.dumps(config, indent=2))
        print(f"Created {config_path}")

    script_path = pillar_dir / f"run_{pillar_name.lower()}_engine.py"
    if not script_path.exists():
        template_script = Path(__file__).parent / "run_ai_engine.py"
        shutil.copy(template_script, script_path)
        print(f"Copied engine script to {script_path}")

    print(f"Pillar '{pillar_name}' scaffolded at {pillar_dir}")
    print(f"Edit {config_path} to configure tickers")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new investment pillar")
    parser.add_argument("pillar", help="Pillar name (e.g., Healthcare, ESG)")
    parser.add_argument("--dir", default=".", help="Parent directory")
    args = parser.parse_args()

    scaffold_pillar(args.pillar, Path(args.dir))


if __name__ == "__main__":
    main()
