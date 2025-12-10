import json
import hashlib
from typing import Dict, Any, List, Tuple, Optional


def hash_payload(payload: str) -> Optional[str]:
    """
    Create a hash of the POST payload for comparison.

    Args:
        payload: The POST payload string (JSON format)

    Returns:
        SHA256 hash of the payload, or None if invalid
    """
    if not payload:
        return None

    try:
        # Parse and re-serialize to normalize the JSON
        # This ensures identical data structures produce the same hash
        # even if whitespace or key ordering differs
        data = json.loads(payload)
        normalized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    except (json.JSONDecodeError, TypeError):
        # If parsing fails, hash the raw string
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def find_duplicate_events(
    network_data: Dict[str, Any], time_window_seconds: float = 1.0
) -> Dict[str, Any]:
    """
    Find duplicate events (identical payloads) within a specified time window.

    Args:
        network_data: Dictionary with structure similar to network_requests_grouped.json
        time_window_seconds: Time window in seconds to check for duplicates (default: 1.0)

    Returns:
        Dictionary containing validation results:
        {
            "valid": bool,  # True if no duplicates found
            "total_post_requests": int,  # Total POST requests analyzed
            "duplicate_groups": int,  # Number of duplicate groups found
            "total_duplicates": int,  # Total number of duplicate events
            "time_window_seconds": float,  # Time window used for detection
            "details": list  # Detailed breakdown per page
        }
    """
    all_events: List[Tuple[str, str, float, str, str]] = []
    total_post_requests = 0
    page_details = []

    # Collect all POST events with timestamps
    for page_url, page_data in network_data.items():
        network_requests = page_data.get("networkRequests", {})
        page_post_requests = 0

        for request_url, request_data in network_requests.items():
            request = request_data.get("request", {})
            if request.get("method") == "POST" and request.get("post_data"):
                total_post_requests += 1
                page_post_requests += 1

                post_data = request.get("post_data")
                timestamp = request.get("timestamp", 0)
                payload_hash = hash_payload(post_data)
                event_type = extract_event_type_from_payload(post_data)

                if payload_hash:
                    all_events.append(
                        (
                            page_url,
                            request_url,
                            timestamp,
                            payload_hash,
                            event_type or "unknown",
                        )
                    )

        page_details.append(
            {
                "page_url": page_url,
                "post_requests": page_post_requests,
            }
        )

    # Sort events by timestamp
    all_events.sort(key=lambda x: x[2])

    # Find duplicates within time window
    duplicate_groups = []
    checked_indices = set()

    for i in range(len(all_events)):
        if i in checked_indices:
            continue

        page_url_i, request_url_i, timestamp_i, hash_i, event_type_i = all_events[i]
        duplicates = [(i, page_url_i, request_url_i, timestamp_i, event_type_i)]

        # Check subsequent events within time window
        for j in range(i + 1, len(all_events)):
            if j in checked_indices:
                continue

            page_url_j, request_url_j, timestamp_j, hash_j, event_type_j = all_events[j]

            # If timestamp difference exceeds window, stop checking
            if timestamp_j - timestamp_i > time_window_seconds:
                break

            # If hashes match, it's a duplicate
            if hash_i == hash_j:
                duplicates.append(
                    (j, page_url_j, request_url_j, timestamp_j, event_type_j)
                )
                checked_indices.add(j)

        # If we found duplicates, add to groups
        if len(duplicates) > 1:
            duplicate_groups.append(
                {
                    "event_type": event_type_i,
                    "payload_hash": hash_i,
                    "count": len(duplicates),
                    "time_span_seconds": duplicates[-1][3] - duplicates[0][3],
                    "events": [
                        {
                            "page_url": dup[1],
                            "request_url": dup[2][:100] + "..."
                            if len(dup[2]) > 100
                            else dup[2],
                            "timestamp": dup[3],
                            "event_type": dup[4],
                        }
                        for dup in duplicates
                    ],
                }
            )
            checked_indices.add(i)

    total_duplicates = sum(group["count"] - 1 for group in duplicate_groups)

    return {
        "valid": len(duplicate_groups) == 0,
        "total_post_requests": total_post_requests,
        "duplicate_groups": len(duplicate_groups),
        "total_duplicates": total_duplicates,
        "time_window_seconds": time_window_seconds,
        "details": page_details,
        "duplicate_details": duplicate_groups,
        "message": (
            f"✓ No duplicate events found (checked {total_post_requests} POST requests)"
            if len(duplicate_groups) == 0
            else f"✗ Found {len(duplicate_groups)} duplicate group(s) "
            f"with {total_duplicates} duplicate event(s) within {time_window_seconds}s window"
        ),
    }


def validate_no_duplicate_events_from_file(
    file_path: str, time_window_seconds: float = 1.0
) -> Dict[str, Any]:
    """
    Load JSON data from file and validate no duplicate events exist.

    Args:
        file_path: Path to JSON file with network request data
        time_window_seconds: Time window in seconds to check for duplicates

    Returns:
        Validation results dictionary
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return find_duplicate_events(data, time_window_seconds)


if __name__ == "__main__":
    import sys

    # Get file path and optional time window from command line
    file_path = sys.argv[1] if len(sys.argv) > 1 else "requests.json"
    time_window = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0

    result = validate_no_duplicate_events_from_file(file_path, time_window)

    print("=" * 70)
    print("NO DUPLICATE EVENTS VALIDATION")
    print("=" * 70)
    print(f"\n{result['message']}\n")
    print(f"Time window: {result['time_window_seconds']}s")
    print(f"Total POST requests checked: {result['total_post_requests']}")
    print(f"Duplicate groups found: {result['duplicate_groups']}")
    print(f"Total duplicate events: {result['total_duplicates']}")

    if result["duplicate_details"]:
        print("\n" + "-" * 70)
        print("DUPLICATE EVENT GROUPS:")
        print("-" * 70)

        for i, group in enumerate(result["duplicate_details"], 1):
            print(f"\n[Group {i}]")
            print(f"  Event Type: {group['event_type']}")
            print(f"  Duplicate Count: {group['count']} identical events")
            print(f"  Time Span: {group['time_span_seconds']:.3f}s")
            print(f"  Payload Hash: {group['payload_hash'][:16]}...")
            print("  Events:")

            for j, event in enumerate(group["events"], 1):
                print(f"\n    [{j}] Timestamp: {event['timestamp']}")
                print(f"        Page: {event['page_url']}")
                print(f"        Request: {event['request_url']}")
                print(f"        Type: {event['event_type']}")

    print("\n" + "-" * 70)
    print("Per-page summary:")
    print("-" * 70)
    for detail in result["details"]:
        print(f"\n  Page: {detail['page_url']}")
        print(f"    POST requests: {detail['post_requests']}")

    print("\n" + "=" * 70)
    if result["valid"]:
        print("VALIDATION: PASSED ✓")
        print("No duplicate events detected")
    else:
        print("VALIDATION: FAILED ✗")
        print(
            f"Found {result['duplicate_groups']} group(s) with duplicate events "
            f"within {result['time_window_seconds']}s"
        )
    print("=" * 70)
