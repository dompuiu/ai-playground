from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from mitmproxy_utils import start_mitmproxy, stop_mitmproxy


async def crawl_with_mitmproxy(
    url: str,
    network_patterns: List[str],
    max_pages: int = 4,
    max_depth: int = 2,
    headless: bool = True,
    output_file: str = "ping_requests.json",
) -> None:
    """
    Crawl a URL and capture network requests via mitmproxy.
    All matching network requests are captured by mitmproxy and saved to output_file.

    Args:
        url: The initial URL to crawl
        network_patterns: List of regex patterns to match against network request URLs
        max_depth: Maximum depth for deep crawling (default: 2)
        max_pages: Maximum number of pages to crawl (default: 4)
        headless: Whether to run browser in headless mode (default: True)
        output_file: Path to save the mitmproxy captured data (default: "ping_requests.json")
    """
    # Start mitmproxy before browser initialization
    mitmproxy_process = start_mitmproxy(network_patterns, output_file=output_file)

    try:
        browser_conf = BrowserConfig(
            headless=headless,
            proxy_config={"server": "http://localhost:9000"},
        )
        run_conf = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            delay_before_return_html=5.0,
            page_timeout=60000,
            capture_network_requests=False,  # Disabled - using mitmproxy instead
            capture_console_messages=False,
            verbose=False,
            deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=max_depth,
                include_external=False,
                max_pages=max_pages,
            ),
            scraping_strategy=LXMLWebScrapingStrategy(),
        )

        async with AsyncWebCrawler(config=browser_conf) as crawler:
            print(f"Starting crawl of {url}...")
            results = await crawler.arun(url=url, config=run_conf)
            print(f"Crawled {len(results)} page(s)")

    finally:
        # Stop mitmproxy after crawling completes
        # This triggers the addon's done() method which saves captured data
        stop_mitmproxy(mitmproxy_process)
        print(f"\nNetwork requests saved to {output_file}")
