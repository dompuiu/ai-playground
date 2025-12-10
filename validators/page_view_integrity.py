import json
from typing import Dict, Any, List, Optional


def extract_event_type_from_post_data(post_data: str) -> Optional[str]:
    """
    Extract eventType from Adobe Experience Platform post_data JSON.

    Args:
        post_data: The POST data string (JSON format)

    Returns:
        The eventType value if found, None otherwise
    """
    if not post_data:
        return None

    try:
        # Parse the JSON string
        data = json.loads(post_data)

        # Look for eventType in the event.xdm structure
        if isinstance(data, dict):
            # Check event.xdm.eventType
            if "event" in data and "xdm" in data["event"]:
                event_type = data["event"]["xdm"].get("eventType")
                if event_type:
                    return event_type

            # Also check top-level eventType (in case structure differs)
            if "eventType" in data:
                return data["eventType"]

    except (json.JSONDecodeError, KeyError, TypeError):
        # If parsing fails or structure is different, return None
        pass

    return None


def extract_page_url_from_post_data(post_data: str) -> Optional[str]:
    """
    Extract page URL from Adobe Experience Platform post_data JSON.

    Args:
        post_data: The POST data string (JSON format)

    Returns:
        The page URL if found, None otherwise
    """
    if not post_data:
        return None

    try:
        # Parse the JSON string
        data = json.loads(post_data)

        # Look for web.webPageDetails.URL in the event.xdm structure
        if isinstance(data, dict):
            # Check event.xdm.web.webPageDetails.URL
            if "event" in data and "xdm" in data["event"]:
                web = data["event"]["xdm"].get("web", {})
                web_page_details = web.get("webPageDetails", {})
                url = web_page_details.get("URL")
                if url:
                    return url

    except (json.JSONDecodeError, KeyError, TypeError):
        # If parsing fails or structure is different, return None
        pass

    return None


def count_page_view_events(network_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Count page view events (web.webpagedetails.pageViews) for each page load.
    Validates that each page has exactly 1 page view event.

    Args:
        network_data: Dictionary with structure similar to network_requests_grouped.json
                     Format: {
                         "page_url": {
                             "html": "...",
                             "networkRequests": {
                                 "request_url": {
                                     "request": {...},
                                     "response": {...},
                                     "response_failure": {...}
                                 }
                             }
                         }
                     }

    Returns:
        Dictionary containing validation results:
        {
            "valid": bool,  # True if all pages have exactly 1 page view event
            "total_pages": int,  # Total number of pages crawled
            "pages_with_one_event": int,  # Number of pages with exactly 1 page view
            "pages_with_zero_events": int,  # Number of pages with 0 page views
            "pages_with_multiple_events": int,  # Number of pages with >1 page views
            "details": list  # Detailed breakdown per page
        }
    """
    total_pages = len(network_data)
    pages_with_one_event = 0
    pages_with_zero_events = 0
    pages_with_multiple_events = 0
    details = []

    for page_url, page_data in network_data.items():
        network_requests = page_data.get("networkRequests", {})
        page_view_events = []
        total_post_requests = 0

        for request_url, request_data in network_requests.items():
            # Only check POST requests with post_data
            request = request_data.get("request", {})
            if request.get("method") == "POST" and request.get("post_data"):
                total_post_requests += 1
                event_type = extract_event_type_from_post_data(request.get("post_data"))

                if event_type == "web.webpagedetails.pageViews":
                    page_url_from_event = extract_page_url_from_post_data(
                        request.get("post_data")
                    )
                    page_view_events.append(
                        {
                            "request_url": request_url,
                            "event_page_url": page_url_from_event,
                            "timestamp": request.get("timestamp"),
                        }
                    )

        # Count the results
        page_view_count = len(page_view_events)
        if page_view_count == 1:
            pages_with_one_event += 1
            status = "✓ PASS"
        elif page_view_count == 0:
            pages_with_zero_events += 1
            status = "✗ FAIL - No page view event"
        else:
            pages_with_multiple_events += 1
            status = f"✗ FAIL - {page_view_count} page view events (expected 1)"

        details.append(
            {
                "page_url": page_url,
                "page_view_count": page_view_count,
                "total_post_requests": total_post_requests,
                "status": status,
                "page_view_events": page_view_events,
            }
        )

    # Overall validation passes only if all pages have exactly 1 page view event
    valid = pages_with_zero_events == 0 and pages_with_multiple_events == 0

    return {
        "valid": valid,
        "total_pages": total_pages,
        "pages_with_one_event": pages_with_one_event,
        "pages_with_zero_events": pages_with_zero_events,
        "pages_with_multiple_events": pages_with_multiple_events,
        "details": details,
        "message": (
            f"✓ All {total_pages} pages have exactly 1 page view event"
            if valid
            else f"✗ Page view integrity check failed: "
            f"{pages_with_one_event}/{total_pages} pages have correct count"
        ),
    }


def validate_page_view_integrity_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from file and validate page view firing integrity.

    Args:
        file_path: Path to JSON file with network request data

    Returns:
        Validation results dictionary
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return count_page_view_events(data)


if __name__ == "__main__":
    import sys

    # Get file path from command line or use default
    file_path = sys.argv[1] if len(sys.argv) > 1 else "network_requests_grouped.json"

    result = validate_page_view_integrity_from_file(file_path)

    print("=" * 70)
    print("PAGE VIEW FIRING INTEGRITY VALIDATION")
    print("=" * 70)
    print(f"\n{result['message']}\n")
    print(f"Total pages crawled: {result['total_pages']}")
    print(f"Pages with exactly 1 page view event: {result['pages_with_one_event']}")
    print(f"Pages with 0 page view events: {result['pages_with_zero_events']}")
    print(f"Pages with multiple page view events: {result['pages_with_multiple_events']}")

    print("\n" + "-" * 70)
    print("Per-page breakdown:")
    print("-" * 70)

    for detail in result["details"]:
        print(f"\nPage: {detail['page_url']}")
        print(f"  Status: {detail['status']}")
        print(f"  Page view events found: {detail['page_view_count']}")
        print(f"  Total POST requests: {detail['total_post_requests']}")

        if detail["page_view_events"]:
            print(f"  Event details:")
            for i, event in enumerate(detail["page_view_events"], 1):
                print(f"    [{i}] Timestamp: {event['timestamp']}")
                print(f"        Event URL: {event['event_page_url']}")
                print(f"        Request: {event['request_url'][:80]}...")

    print("\n" + "=" * 70)
    if result["valid"]:
        print("VALIDATION: PASSED ✓")
        print("All pages fired exactly one page view event")
    else:
        print("VALIDATION: FAILED ✗")
        print(
            f"{result['pages_with_zero_events']} page(s) missing page view events"
            if result["pages_with_zero_events"] > 0
            else ""
        )
        print(
            f"{result['pages_with_multiple_events']} page(s) with multiple page view events"
            if result["pages_with_multiple_events"] > 0
            else ""
        )
    print("=" * 70)
