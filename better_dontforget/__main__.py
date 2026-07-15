"""Allow ``python -m better_dontforget``."""

from .cli import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
