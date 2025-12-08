import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

edge_url_prefix = "https://www.adobe.com/experienceedge/"
initial_url = "https://www.adobe.com"


async def main():
    browser_conf = BrowserConfig(headless=False)  # or False to see the browser
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=5.0,
        page_timeout=60000,
        capture_network_requests=True,
        capture_console_messages=True,
        verbose=True,
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,
            include_external=False,
            max_pages=4,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        results = await crawler.arun(url=initial_url, config=run_conf)

        # Initialize export data outside the loop
        export_data = {}

        for result in results:
            if result.network_requests:
                # Group requests and responses by URL
                url_map = {}

                for event in result.network_requests:
                    url = event.get("url", "")

                    # Check if URL matches our patterns
                    is_edge_request = url.startswith(edge_url_prefix)
                    is_launch_file = "marketingtech" in url and "launch-" in url

                    if not (is_edge_request or is_launch_file):
                        continue

                    # Initialize the URL entry if it doesn't exist
                    if url not in url_map:
                        url_map[url] = {
                            "request": None,
                            "response": None,
                            "response_failure": None,
                        }

                    # Categorize the event
                    event_type = event.get("event_type")

                    if event_type == "request":
                        url_map[url]["request"] = event
                    elif event_type == "response":
                        url_map[url]["response"] = event
                    elif event_type == "response_failure":
                        url_map[url]["response_failure"] = event

                # Print the grouped data
                print(f"\nPage: {result.url}")
                print(f"Grouped {len(url_map)} unique URLs\n")
                for url, data in url_map.items():
                    print(f"URL: {url}")
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
        output_file = "network_requests_grouped.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved grouped data for {len(export_data)} pages to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
