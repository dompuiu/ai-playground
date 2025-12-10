import json
from typing import Dict, Any


def extract_required_fields_from_payload(payload: str) -> Dict[str, Any]:
    """
    Extract required fields from Adobe Experience Platform payload JSON.
    Checks for: eventType, timestamp, identityMap

    Args:
        payload: The POST payload string (JSON format)

    Returns:
        Dictionary with field presence information
    """
    if not payload:
        return {
            "eventType": None,
            "timestamp": None,
            "identityMap": None,
            "has_all_required": False,
            "missing_fields": ["eventType", "timestamp", "identityMap"],
        }

    try:
        # Parse the JSON string
        data = json.loads(payload)

        event_type = None
        timestamp = None
        identity_map = None
        missing_fields = []

        if isinstance(data, dict):
            # Check event.xdm structure (most common)
            if "event" in data and "xdm" in data["event"]:
                xdm = data["event"]["xdm"]

                # Check eventType
                event_type = xdm.get("eventType")
                if not event_type:
                    # Also check top-level
                    event_type = data.get("eventType")

                # Check timestamp
                timestamp = xdm.get("timestamp")
                if not timestamp:
                    # Also check top-level
                    timestamp = data.get("timestamp")

                # Check identityMap
                identity_map = xdm.get("identityMap")
                if not identity_map:
                    # Also check top-level
                    identity_map = data.get("identityMap")
            else:
                # Check top-level directly
                event_type = data.get("eventType")
                timestamp = data.get("timestamp")
                identity_map = data.get("identityMap")

        # Determine missing fields
        if not event_type:
            missing_fields.append("eventType")
        if not timestamp:
            missing_fields.append("timestamp")
        if not identity_map:
            missing_fields.append("identityMap")

        return {
            "eventType": event_type,
            "timestamp": timestamp,
            "identityMap": identity_map,
            "has_all_required": len(missing_fields) == 0,
            "missing_fields": missing_fields,
        }

    except (json.JSONDecodeError, KeyError, TypeError):
        # If parsing fails, all fields are missing
        return {
            "eventType": None,
            "timestamp": None,
            "identityMap": None,
            "has_all_required": False,
            "missing_fields": ["eventType", "timestamp", "identityMap"],
            "parse_error": True,
        }


def validate_required_fields(network_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that all POST events contain required fields: eventType, timestamp, identityMap.

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
            "valid": bool,  # True if all events have all required fields
            "total_post_requests": int,  # Total POST requests analyzed
            "events_with_all_fields": int,  # Events with all required fields
            "events_missing_fields": int,  # Events missing one or more fields
            "field_statistics": dict,  # Stats per field
            "details": list  # Detailed breakdown per page
        }
    """
    total_post_requests = 0
    events_with_all_fields = 0
    events_missing_fields = 0

    # Track which fields are missing across all events
    field_missing_count = {
        "eventType": 0,
        "timestamp": 0,
        "identityMap": 0,
    }

    details = []
    all_missing_events = []

    for page_url, page_data in network_data.items():
        network_requests = page_data.get("networkRequests", {})
        page_post_requests = 0
        page_events_with_all_fields = 0
        page_events_missing_fields = 0
        page_missing_events = []

        for request_url, request_data in network_requests.items():
            # Only check POST requests with post_data
            request = request_data.get("request", {})
            if request.get("method") == "POST" and request.get("post_data"):
                total_post_requests += 1
                page_post_requests += 1

                post_data = request.get("post_data")
                fields = extract_required_fields_from_payload(post_data)

                if fields["has_all_required"]:
                    events_with_all_fields += 1
                    page_events_with_all_fields += 1
                else:
                    events_missing_fields += 1
                    page_events_missing_fields += 1

                    # Track which fields are missing
                    for field in fields["missing_fields"]:
                        field_missing_count[field] += 1

                    # Store details about missing fields
                    missing_event = {
                        "request_url": request_url[:100] + "..."
                        if len(request_url) > 100
                        else request_url,
                        "timestamp": request.get("timestamp"),
                        "missing_fields": fields["missing_fields"],
                        "eventType": fields.get("eventType", "N/A"),
                        "has_parse_error": fields.get("parse_error", False),
                    }
                    page_missing_events.append(missing_event)
                    all_missing_events.append(
                        {
                            **missing_event,
                            "page_url": page_url,
                        }
                    )

        status = (
            "✓ PASS"
            if page_events_missing_fields == 0
            else f"✗ FAIL - {page_events_missing_fields} event(s) missing fields"
        )

        details.append(
            {
                "page_url": page_url,
                "post_requests": page_post_requests,
                "events_with_all_fields": page_events_with_all_fields,
                "events_missing_fields": page_events_missing_fields,
                "status": status,
                "missing_events": page_missing_events,
            }
        )

    # Overall validation passes only if all events have all required fields
    valid = events_missing_fields == 0

    return {
        "valid": valid,
        "total_post_requests": total_post_requests,
        "events_with_all_fields": events_with_all_fields,
        "events_missing_fields": events_missing_fields,
        "field_statistics": {
            "eventType": {
                "missing_count": field_missing_count["eventType"],
                "present_count": total_post_requests - field_missing_count["eventType"],
            },
            "timestamp": {
                "missing_count": field_missing_count["timestamp"],
                "present_count": total_post_requests - field_missing_count["timestamp"],
            },
            "identityMap": {
                "missing_count": field_missing_count["identityMap"],
                "present_count": total_post_requests
                - field_missing_count["identityMap"],
            },
        },
        "details": details,
        "all_missing_events": all_missing_events,
        "message": (
            f"✓ All {total_post_requests} events have required fields (eventType, timestamp, identityMap)"
            if valid
            else f"✗ Required fields validation failed: "
            f"{events_missing_fields}/{total_post_requests} event(s) missing required fields"
        ),
    }


def validate_required_fields_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from file and validate required fields.

    Args:
        file_path: Path to JSON file with network request data

    Returns:
        Validation results dictionary
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return validate_required_fields(data)


if __name__ == "__main__":
    import sys

    # Get file path from command line or use default
    file_path = sys.argv[1] if len(sys.argv) > 1 else "requests.json"

    result = validate_required_fields_from_file(file_path)

    print("=" * 70)
    print("REQUIRED FIELDS VALIDATION")
    print("=" * 70)
    print(f"\n{result['message']}\n")
    print(f"Total POST requests checked: {result['total_post_requests']}")
    print(f"Events with all required fields: {result['events_with_all_fields']}")
    print(f"Events missing fields: {result['events_missing_fields']}")

    print("\n" + "-" * 70)
    print("Field Statistics:")
    print("-" * 70)
    for field_name, stats in result["field_statistics"].items():
        status = "✓" if stats["missing_count"] == 0 else "✗"
        print(f"{status} {field_name}:")
        print(f"    Present: {stats['present_count']}/{result['total_post_requests']}")
        print(f"    Missing: {stats['missing_count']}/{result['total_post_requests']}")

    if result["all_missing_events"]:
        print("\n" + "-" * 70)
        print("Events with Missing Fields:")
        print("-" * 70)

        for i, event in enumerate(result["all_missing_events"], 1):
            print(f"\n[{i}] Page: {event['page_url']}")
            print(f"    Request: {event['request_url']}")
            print(f"    Event Type: {event['eventType']}")
            print(f"    Missing Fields: {', '.join(event['missing_fields'])}")
            if event.get("has_parse_error"):
                print("    ⚠ Parse Error: Unable to parse payload")

    print("\n" + "-" * 70)
    print("Per-page breakdown:")
    print("-" * 70)

    for detail in result["details"]:
        print(f"\nPage: {detail['page_url']}")
        print(f"  Status: {detail['status']}")
        print(f"  POST requests: {detail['post_requests']}")
        print(f"  Events with all fields: {detail['events_with_all_fields']}")
        print(f"  Events missing fields: {detail['events_missing_fields']}")

    print("\n" + "=" * 70)
    if result["valid"]:
        print("VALIDATION: PASSED ✓")
        print("All events contain required fields")
    else:
        print("VALIDATION: FAILED ✗")
        print(
            f"{result['events_missing_fields']} event(s) missing one or more required fields"
        )
    print("=" * 70)
