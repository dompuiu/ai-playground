import json
import re
from typing import List, Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy


async def crawl_with_network_capture(
    url: str,
    network_patterns: List[str],
    max_pages: int = 4,
    max_depth: int = 2,
    headless: bool = True,
    output_file: str = "network_requests_grouped.json",
) -> Dict[str, Any]:
    """
    Crawl a URL and capture network requests matching the provided regex patterns.

    Args:
        url: The initial URL to crawl
        network_patterns: List of regex patterns to match against network request URLs
        max_depth: Maximum depth for deep crawling (default: 2)
        max_pages: Maximum number of pages to crawl (default: 4)
        headless: Whether to run browser in headless mode (default: False)
        output_file: Path to save the JSON output (default: "network_requests_grouped.json")

    Returns:
        Dictionary containing crawled data with network requests grouped by page URL
    """
    # Compile regex patterns for better performance
    compiled_patterns = [re.compile(pattern) for pattern in network_patterns]

    browser_conf = BrowserConfig(headless=headless)
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=5.0,
        page_timeout=60000,
        capture_network_requests=True,
        capture_console_messages=True,
        verbose=False,
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=False,
            max_pages=max_pages,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        results = await crawler.arun(url=url, config=run_conf)

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
                            "response_failure": None,
                        }

                    # Categorize the event
                    event_type = event.get("event_type")

                    if event_type == "request":
                        url_map[request_url]["request"] = event
                    elif event_type == "response":
                        url_map[request_url]["response"] = event
                    elif event_type == "response_failure":
                        url_map[request_url]["response_failure"] = event

                # Print the grouped data
                print(f"\nPage crawled: {result.url}")
                print(f"Grouped {len(url_map)} unique URLs\n")
                for request_url, data in url_map.items():
                    print(f"URL: {request_url}")
                    print(f"  Has request: {data['request'] is not None}")
                    print(f"  Has response: {data['response'] is not None}")
                    print(f"  Has failure: {data['response_failure'] is not None}")
                    if data["request"]:
                        print(f"  Request method: {data['request'].get('method')}")
                    if data["response"]:
                        print(f"  Response status: {data['response'].get('status')}")
                    if data["response_failure"]:
                        print(
                            f"  Failure reason: {data['response_failure'].get('error_text')}"
                        )
                    print("---")

                # Add this page's data to the export structure
                export_data[result.url] = {
                    "html": result.html,
                    "networkRequests": url_map,
                }

        # Save to JSON file after processing all pages
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved grouped data for {len(export_data)} pages to {output_file}")

        return export_data
