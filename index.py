import asyncio
import re
from crawler import crawl_with_network_capture


async def main():
    # Example usage with the original patterns
    edge_url_prefix = "https://www.adobe.com/experienceedge/"

    network_patterns = [
        rf"{re.escape(edge_url_prefix)}",  # URLs starting with edge prefix
        r"marketingtech.*launch-",  # URLs containing marketingtech and launch-
    ]

    await crawl_with_network_capture(
        url="https://www.adobe.com",
        network_patterns=network_patterns,
        max_pages=4,
        max_depth=2,
        headless=False,
    )


if __name__ == "__main__":
    asyncio.run(main())
