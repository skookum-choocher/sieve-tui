"""Entry point — `python -m sieve_tui` or installed as `sieve-tui`."""

from .app import SieveTUIApp


def main() -> None:
    SieveTUIApp().run()


if __name__ == "__main__":
    main()
