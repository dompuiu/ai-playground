import json
from typing import Dict, Any, List, Optional


def get_payload_size(payload: str) -> int:
    """
    Calculate the size of POST payload in bytes.

    Args:
        payload: The POST payload string

    Returns:
        Size in bytes
    """
    if not payload:
        return 0
    
    # Get size in bytes (UTF-8 encoded)
    return len(payload.encode('utf-8'))


def format_size(size_bytes: int) -> str:
    """
    Format size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 KB", "32.0 KB")
    """
    kb = size_bytes / 1024
    if kb < 1024:
        return f"{kb:.2f} KB"
    else:
        mb = kb / 1024
        return f"{mb:.2f} MB"


def extract_event_type_from_payload(payload: str) -> Optional[str]:
    """
    Extract eventType from Adobe Experience Platform payload JSON.

    Args:
        payload: The POST payload string (JSON format)

    Returns:
        The eventType value if found, None otherwise
    """
    if not payload:
        return None

    try:
        data = json.loads(payload)

        if isinstance(data, dict):
            # Check event.xdm.eventType
            if "event" in data and "xdm" in data["event"]:
                event_type = data["event"]["xdm"].get("eventType")
                if event_type:
                    return event_type

            # Also check top-level eventType
            if "eventType" in data:
                return data["eventType"]

    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    return None


# Backwards compatibility alias
def extract_event_type_from_post_data(post_data: str) -> Optional[str]:
    """Deprecated: Use extract_event_type_from_payload instead."""
    return extract_event_type_from_payload(post_data)


def validate_payload_size(
    network_data: Dict[str, Any], max_size_kb: float = 32.0
) -> Dict[str, Any]:
    """
    Validate that all POST payloads are under the specified size limit.

    Args:
        network_data: Dictionary with structure similar to network_requests_grouped.json
        max_size_kb: Maximum payload size in kilobytes (default: 32 KB)

    Returns:
        Dictionary containing validation results:
        {
            "valid": bool,  # True if all payloads are under size limit
            "total_post_requests": int,  # Total POST requests analyzed
            "payloads_under_limit": int,  # Payloads under size limit
            "payloads_over_limit": int,  # Payloads over size limit
            "max_size_kb": float,  # Size limit used
            "max_size_bytes": int,  # Size limit in bytes
            "largest_payload_size": int,  # Largest payload found (bytes)
            "smallest_payload_size": int,  # Smallest payload found (bytes)
            "average_payload_size": float,  # Average payload size (bytes)
            "details": list  # Detailed breakdown per page
        }
    """
    max_size_bytes = int(max_size_kb * 1024)
    total_post_requests = 0
    payloads_under_limit = 0
    payloads_over_limit = 0
    
    all_payload_sizes = []
    oversized_payloads = []
    details = []

    for page_url, page_data in network_data.items():
        network_requests = page_data.get("networkRequests", {})
        page_post_requests = 0
        page_payloads_under_limit = 0
        page_payloads_over_limit = 0
        page_oversized = []

        for request_url, request_data in network_requests.items():
            # Only check POST requests with payload
            request = request_data.get("request", {})
            if request.get("method") == "POST" and request.get("payload"):
                total_post_requests += 1
                page_post_requests += 1

                payload = request.get("payload")
                payload_size = get_payload_size(payload)
                all_payload_sizes.append(payload_size)

                if payload_size <= max_size_bytes:
                    payloads_under_limit += 1
                    page_payloads_under_limit += 1
                else:
                    payloads_over_limit += 1
                    page_payloads_over_limit += 1
                    
                    event_type = extract_event_type_from_payload(payload)
                    oversized_payload = {
                        "page_url": page_url,
                        "request_url": request_url[:100] + "..." if len(request_url) > 100 else request_url,
                        "timestamp": request.get("timestamp"),
                        "event_type": event_type or "unknown",
                        "payload_size_bytes": payload_size,
                        "payload_size_formatted": format_size(payload_size),
                        "exceeds_by_bytes": payload_size - max_size_bytes,
                        "exceeds_by_formatted": format_size(payload_size - max_size_bytes),
                        "percentage_of_limit": (payload_size / max_size_bytes) * 100,
                    }
                    page_oversized.append(oversized_payload)
                    oversized_payloads.append(oversized_payload)

        status = "✓ PASS" if page_payloads_over_limit == 0 else f"✗ FAIL - {page_payloads_over_limit} payload(s) over limit"

        details.append(
            {
                "page_url": page_url,
                "post_requests": page_post_requests,
                "payloads_under_limit": page_payloads_under_limit,
                "payloads_over_limit": page_payloads_over_limit,
                "status": status,
                "oversized_payloads": page_oversized,
            }
        )

    # Calculate statistics
    largest_payload = max(all_payload_sizes) if all_payload_sizes else 0
    smallest_payload = min(all_payload_sizes) if all_payload_sizes else 0
    average_payload = sum(all_payload_sizes) / len(all_payload_sizes) if all_payload_sizes else 0

    # Overall validation passes only if all payloads are under limit
    valid = payloads_over_limit == 0

    return {
        "valid": valid,
        "total_post_requests": total_post_requests,
        "payloads_under_limit": payloads_under_limit,
        "payloads_over_limit": payloads_over_limit,
        "max_size_kb": max_size_kb,
        "max_size_bytes": max_size_bytes,
        "largest_payload_size": largest_payload,
        "smallest_payload_size": smallest_payload,
        "average_payload_size": average_payload,
        "oversized_payloads": oversized_payloads,
        "details": details,
        "message": (
            f"✓ All {total_post_requests} payloads are under {max_size_kb} KB limit"
            if valid
            else f"✗ Payload size validation failed: "
            f"{payloads_over_limit}/{total_post_requests} payload(s) exceed {max_size_kb} KB limit"
        ),
    }


def validate_payload_size_from_file(
    file_path: str, max_size_kb: float = 32.0
) -> Dict[str, Any]:
    """
    Load JSON data from file and validate payload sizes.

    Args:
        file_path: Path to JSON file with network request data
        max_size_kb: Maximum payload size in kilobytes (default: 32 KB)

    Returns:
        Validation results dictionary
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return validate_payload_size(data, max_size_kb)


if __name__ == "__main__":
    import sys

    # Get file path and optional size limit from command line
    file_path = sys.argv[1] if len(sys.argv) > 1 else "requests.json"
    max_size_kb = float(sys.argv[2]) if len(sys.argv) > 2 else 32.0

    result = validate_payload_size_from_file(file_path, max_size_kb)

    print("=" * 70)
    print("PAYLOAD SIZE VALIDATION")
    print("=" * 70)
    print(f"\n{result['message']}\n")
    print(f"Size limit: {result['max_size_kb']} KB ({result['max_size_bytes']:,} bytes)")
    print(f"Total POST requests checked: {result['total_post_requests']}")
    print(f"Payloads under limit: {result['payloads_under_limit']}")
    print(f"Payloads over limit: {result['payloads_over_limit']}")

    print("\n" + "-" * 70)
    print("Payload Size Statistics:")
    print("-" * 70)
    print(f"Largest payload:  {format_size(result['largest_payload_size'])} ({result['largest_payload_size']:,} bytes)")
    print(f"Smallest payload: {format_size(result['smallest_payload_size'])} ({result['smallest_payload_size']:,} bytes)")
    print(f"Average payload:  {format_size(result['average_payload_size'])} ({result['average_payload_size']:,.0f} bytes)")

    if result["oversized_payloads"]:
        print("\n" + "-" * 70)
        print("Oversized Payloads:")
        print("-" * 70)
        
        for i, payload in enumerate(result["oversized_payloads"], 1):
            print(f"\n[{i}] Page: {payload['page_url']}")
            print(f"    Request: {payload['request_url']}")
            print(f"    Event Type: {payload['event_type']}")
            print(f"    Payload Size: {payload['payload_size_formatted']} ({payload['payload_size_bytes']:,} bytes)")
            print(f"    Exceeds Limit By: {payload['exceeds_by_formatted']} ({payload['exceeds_by_bytes']:,} bytes)")
            print(f"    Percentage of Limit: {payload['percentage_of_limit']:.1f}%")
            if payload.get('timestamp'):
                print(f"    Timestamp: {payload['timestamp']}")

    print("\n" + "-" * 70)
    print("Per-page breakdown:")
    print("-" * 70)

    for detail in result["details"]:
        print(f"\nPage: {detail['page_url']}")
        print(f"  Status: {detail['status']}")
        print(f"  POST requests: {detail['post_requests']}")
        print(f"  Payloads under limit: {detail['payloads_under_limit']}")
        print(f"  Payloads over limit: {detail['payloads_over_limit']}")

    print("\n" + "=" * 70)
    if result["valid"]:
        print("VALIDATION: PASSED ✓")
        print(f"All payloads are under {result['max_size_kb']} KB limit")
    else:
        print("VALIDATION: FAILED ✗")
        print(
            f"{result['payloads_over_limit']} payload(s) exceed the {result['max_size_kb']} KB limit"
        )
    print("=" * 70)
