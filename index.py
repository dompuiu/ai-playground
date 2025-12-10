import asyncio
import re
from crawler import crawl_with_mitmproxy


async def main():
    # Example usage with the original patterns
    edge_url_prefix = "https://www.adobe.com/experienceedge/"

    network_patterns = [
        rf"{re.escape(edge_url_prefix)}",  # URLs starting with edge prefix
        r"marketingtech.*launch-",  # URLs containing marketingtech and launch-
    ]

    await crawl_with_mitmproxy(
        url="https://www.adobe.com",
        network_patterns=network_patterns,
        max_pages=5,
        max_depth=2,
        headless=False,
        output_file="requests.json",
    )


if __name__ == "__main__":
    asyncio.run(main())
