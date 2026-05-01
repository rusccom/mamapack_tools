import sys
from pathlib import Path


def add_project_root() -> None:
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root))


add_project_root()

from shopify_store.product_import.product_content import run


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    configure_stdout()
    result = run(Path.cwd())
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
