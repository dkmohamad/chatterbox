import argparse
import logging
import signal

from chatterbox.config import load_config
from chatterbox.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Chatterbox voice agent")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to TOML config file",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit",
    )
    args = parser.parse_args()

    if args.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        print()
        print(f"Default input:  {sd.query_devices(kind='input')['name']}")
        print(f"Default output: {sd.query_devices(kind='output')['name']}")
        return

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Suppress noisy third-party loggers unless in debug mode
    if not args.debug:
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

    config = load_config(args.config)
    pipeline = Pipeline(config)

    def handle_signal(sig: int, frame: object) -> None:
        logging.info("Shutdown signal received")
        pipeline.shutdown()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    pipeline.run()


if __name__ == "__main__":
    main()
