import re
import json
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
    mitmproxy_process = start_mitmproxy(network_patterns)

    compiled_patterns = [re.compile(pattern) for pattern in network_patterns]

    try:
        browser_conf = BrowserConfig(
            headless=headless,
            proxy_config={"server": "http://localhost:9000"},
        )
        run_conf = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            delay_before_return_html=5.0,
            page_timeout=60000,
            capture_network_requests=True,
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

            stop_mitmproxy(mitmproxy_process)

            # Read the c.json file into a dictionary
            with open("proxy_requests.json", "r", encoding="utf-8") as f:
                proxy_requests = json.load(f)

            # Initialize export data outside the loop
            export_data = {}

            for result in results:
                if result.network_requests:
                    # Group requests and responses by URL
                    url_map = {}

                    for event in result.network_requests:
                        request_url = event.get("url", "")

                        # Check if URL matches any of the provided patterns
                        matches_pattern = any(
                            pattern.search(request_url) for pattern in compiled_patterns
                        )

                        if not matches_pattern:
                            continue

                        # Initialize the URL entry if it doesn't exist
                        if request_url not in url_map:
                            url_map[request_url] = {
                                "request": None,
                                "response": None,
                            }

                        # Categorize the event
                        event_type = event.get("event_type")

                        if event_type == "request":
                            if event.get("resource_type") == "ping":
                                post_data = (
                                    proxy_requests.get(event.get("url"))
                                    .get("request", {})
                                    .get("payload")
                                )
                                event["post_data"] = post_data
                            url_map[request_url]["request"] = event
                        elif event_type == "response":
                            url_map[request_url]["response"] = event
                        elif event_type == "response_failure":
                            url_map[request_url]["response"] = event

                    # Add this page's data to the export structure
                    # Handle duplicate URLs by appending (#N)
                    key = result.url
                    if key in export_data:
                        counter = 2
                        while f"{result.url} (#{counter})" in export_data:
                            counter += 1
                        key = f"{result.url} (#{counter})"

                    export_data[key] = {
                        "html": result.html,
                        "networkRequests": url_map,
                    }

            with open("c.json", "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"Crawled {len(results)} page(s)")

    except Exception as e:
        print(f"An error occurred during crawling: {e}")
