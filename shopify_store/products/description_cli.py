import json
import sys

from .description_style import build_product_description


def main():
    spec = json.load(sys.stdin)
    sys.stdout.write(build_product_description(spec))


if __name__ == "__main__":
    main()
