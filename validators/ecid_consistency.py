import json
import re
from typing import Dict, Any, Set, Optional


def extract_ecid_from_text(text: str) -> Optional[str]:
    """
    Extract ECID from text content using regex patterns.
    ECID typically appears in various formats in Adobe Experience Cloud requests.

    Args:
        text: The text content to search for ECID

    Returns:
        The ECID value if found, None otherwise
    """
    if not text:
        return None

    # Common ECID patterns in Adobe Experience Cloud
    # ECID can appear as: ecid, ECID, experienceCloud.ecid, etc.
    patterns = [
        r'"ecid"\s*:\s*"([^"]+)"',  # "ecid": "value"
        r'"ECID"\s*:\s*"([^"]+)"',  # "ECID": "value"
        r'ecid=([^&\s"]+)',  # ecid=value (URL parameter)
        r'ECID=([^&\s"]+)',  # ECID=value (URL parameter)
        r'experienceCloud\.ecid["\s:]+([^",\s]+)',  # experienceCloud.ecid
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def extract_ecid_from_post_data(post_data: str) -> Optional[str]:
    """
    Extract ECID specifically from Adobe Experience Platform post_data JSON.
    Looks for the ECID in the identityMap.ECID structure.

    Args:
        post_data: The POST data string (JSON format)

    Returns:
        The ECID value if found in identityMap, None otherwise
    """
    if not post_data:
        return None

    try:
        # Parse the JSON string
        data = json.loads(post_data)

        # Look for identityMap.ECID in the event.xdm structure
        if isinstance(data, dict):
            # Check event.xdm.identityMap.ECID
            if "event" in data and "xdm" in data["event"]:
                identity_map = data["event"]["xdm"].get("identityMap", {})
                ecid_array = identity_map.get("ECID", [])
                if ecid_array and len(ecid_array) > 0:
                    return ecid_array[0].get("id")

            # Also check top-level identityMap (in case structure differs)
            identity_map = data.get("identityMap", {})
            ecid_array = identity_map.get("ECID", [])
            if ecid_array and len(ecid_array) > 0:
                return ecid_array[0].get("id")

    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
        # If parsing fails or structure is different, return None
        pass

    return None


def extract_ecids_from_post_data_only(data: Dict[str, Any]) -> Set[str]:
    """
    Extract ECIDs from POST data only (not from URLs).

    Args:
        data: Dictionary containing network request/response data

    Returns:
        Set of unique ECID values found in POST data
    """
    ecids = set()

    # Check in request data
    if data.get("request"):
        request = data["request"]

        # Check post data only
        post_data = request.get("post_data")
        if post_data:
            ecid = extract_ecid_from_post_data(post_data)
            if ecid:
                ecids.add(ecid)

    return ecids


def extract_ecids_from_network_data(data: Dict[str, Any]) -> Set[str]:
    """
    Extract all ECIDs from network request data.

    Args:
        data: Dictionary containing network request/response data

    Returns:
        Set of unique ECID values found in the data
    """
    ecids = set()

    # Check in request data
    if data.get("request"):
        request = data["request"]

        # Check URL
        url = request.get("url", "")
        ecid = extract_ecid_from_text(url)
        if ecid:
            ecids.add(ecid)

        # Check headers
        headers = request.get("headers", {})
        for header_value in headers.values():
            if isinstance(header_value, str):
                ecid = extract_ecid_from_text(header_value)
                if ecid:
                    ecids.add(ecid)

        # Check post data
        post_data = request.get("post_data")
        if post_data:
            ecid = extract_ecid_from_text(str(post_data))
            if ecid:
                ecids.add(ecid)

    # Check in response data
    if data.get("response"):
        response = data["response"]

        # Check response headers
        headers = response.get("headers", {})
        for header_value in headers.values():
            if isinstance(header_value, str):
                ecid = extract_ecid_from_text(header_value)
                if ecid:
                    ecids.add(ecid)

        # Check response body
        body = response.get("body", {})
        if isinstance(body, dict):
            text = body.get("text", "")
            if text:
                ecid = extract_ecid_from_text(text)
                if ecid:
                    ecids.add(ecid)
        elif isinstance(body, str):
            ecid = extract_ecid_from_text(body)
            if ecid:
                ecids.add(ecid)

    return ecids


def validate_same_ecid(network_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that all events in the network data share the same ECID.

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
            "valid": bool,  # True if all events share the same ECID
            "ecids_found": list,  # List of unique ECIDs found
            "total_ecids": int,  # Count of unique ECIDs
            "events_with_ecid": int,  # Number of events that contained ECID
            "total_events": int,  # Total number of events checked
            "details": list  # Detailed breakdown per page
        }
    """
    all_ecids = set()
    events_with_ecid = 0
    total_events = 0
    details = []

    for page_url, page_data in network_data.items():
        network_requests = page_data.get("networkRequests", {})
        page_ecids = set()
        page_events = 0

        for request_url, request_data in network_requests.items():
            total_events += 1
            page_events += 1

            ecids = extract_ecids_from_network_data(request_data)
            if ecids:
                events_with_ecid += 1
                all_ecids.update(ecids)
                page_ecids.update(ecids)

        details.append(
            {
                "page_url": page_url,
                "ecids": list(page_ecids),
                "events_checked": page_events,
                "events_with_ecid": len(
                    [
                        req
                        for req in network_requests.values()
                        if extract_ecids_from_network_data(req)
                    ]
                ),
            }
        )

    ecids_list = sorted(list(all_ecids))

    return {
        "valid": len(all_ecids) <= 1,  # Valid if 0 or 1 unique ECID
        "ecids_found": ecids_list,
        "total_ecids": len(all_ecids),
        "events_with_ecid": events_with_ecid,
        "total_events": total_events,
        "details": details,
        "message": (
            f"✓ All events share the same ECID: {ecids_list[0]}"
            if len(all_ecids) == 1
            else f"✗ Multiple ECIDs found: {ecids_list}"
            if len(all_ecids) > 1
            else "⚠ No ECID found in any events"
        ),
    }


def validate_post_data_ecid(network_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that all POST data requests share the same ECID.
    This function specifically looks at the identityMap.ECID field in POST data,
    ignoring ECIDs found in URLs or other places.

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
            "valid": bool,  # True if all POST data events share the same ECID
            "ecids_found": list,  # List of unique ECIDs found in POST data
            "total_ecids": int,  # Count of unique ECIDs
            "requests_with_ecid": int,  # Number of requests with POST data ECID
            "total_post_requests": int,  # Total number of POST requests checked
            "details": list  # Detailed breakdown per page
        }
    """
    all_ecids = set()
    requests_with_ecid = 0
    total_post_requests = 0
    details = []

    for page_url, page_data in network_data.items():
        network_requests = page_data.get("networkRequests", {})
        page_ecids = set()
        page_post_requests = 0
        page_requests_with_ecid = 0
        page_details = []

        for request_url, request_data in network_requests.items():
            # Only check POST requests
            request = request_data.get("request", {})
            if request.get("method") == "POST" and request.get("post_data"):
                total_post_requests += 1
                page_post_requests += 1

                ecids = extract_ecids_from_post_data_only(request_data)
                if ecids:
                    requests_with_ecid += 1
                    page_requests_with_ecid += 1
                    all_ecids.update(ecids)
                    page_ecids.update(ecids)
                    page_details.append(
                        {
                            "request_url": request_url,
                            "ecid": list(ecids)[0] if ecids else None,
                        }
                    )

        details.append(
            {
                "page_url": page_url,
                "ecids": list(page_ecids),
                "post_requests_checked": page_post_requests,
                "requests_with_ecid": page_requests_with_ecid,
                "request_details": page_details,
            }
        )

    ecids_list = sorted(list(all_ecids))

    return {
        "valid": len(all_ecids) <= 1,  # Valid if 0 or 1 unique ECID
        "ecids_found": ecids_list,
        "total_ecids": len(all_ecids),
        "requests_with_ecid": requests_with_ecid,
        "total_post_requests": total_post_requests,
        "details": details,
        "message": (
            f"✓ All POST data requests share the same ECID: {ecids_list[0]}"
            if len(all_ecids) == 1
            else f"✗ Multiple ECIDs found in POST data: {ecids_list}"
            if len(all_ecids) > 1
            else "⚠ No ECID found in POST data"
        ),
    }


def validate_ecid_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from file and validate ECID consistency.

    Args:
        file_path: Path to JSON file with network request data

    Returns:
        Validation results dictionary
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return validate_same_ecid(data)


def validate_post_data_ecid_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from file and validate POST data ECID consistency.

    Args:
        file_path: Path to JSON file with network request data

    Returns:
        Validation results dictionary
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return validate_post_data_ecid(data)


if __name__ == "__main__":
    import sys

    # Check if a specific validation type is requested
    validation_type = sys.argv[1] if len(sys.argv) > 1 else "post_data"
    file_path = sys.argv[2] if len(sys.argv) > 2 else "network_requests_grouped.json"

    if validation_type == "post_data":
        # Validate POST data ECIDs only (excluding URLs)
        result = validate_post_data_ecid_from_file(file_path)

        print("=" * 60)
        print("POST Data ECID Validation Results")
        print("=" * 60)
        print(f"\n{result['message']}\n")
        print(f"Total POST requests checked: {result['total_post_requests']}")
        print(f"POST requests with ECID: {result['requests_with_ecid']}")
        print(f"Unique ECIDs found: {result['total_ecids']}")

        if result["ecids_found"]:
            print("\nECID(s) from POST data:")
            for ecid in result["ecids_found"]:
                print(f"  - {ecid}")

        print("\nPer-page breakdown:")
        for detail in result["details"]:
            print(f"\n  Page: {detail['page_url']}")
            print(f"    POST requests checked: {detail['post_requests_checked']}")
            print(f"    Requests with ECID: {detail['requests_with_ecid']}")
            if detail["ecids"]:
                print(f"    ECIDs: {', '.join(detail['ecids'])}")
            if detail["request_details"]:
                print(f"    Request details:")
                for req_detail in detail["request_details"]:
                    print(f"      - URL: {req_detail['request_url'][:80]}...")
                    print(f"        ECID: {req_detail['ecid']}")

        print("\n" + "=" * 60)
        print(f"Validation: {'PASSED ✓' if result['valid'] else 'FAILED ✗'}")
        print("=" * 60)

    else:
        # Original validation (all sources including URLs)
        result = validate_ecid_from_file(file_path)

        print("=" * 60)
        print("ECID Validation Results (All Sources)")
        print("=" * 60)
        print(f"\n{result['message']}\n")
        print(f"Total events checked: {result['total_events']}")
        print(f"Events with ECID: {result['events_with_ecid']}")
        print(f"Unique ECIDs found: {result['total_ecids']}")

        if result["ecids_found"]:
            print("\nECID(s):")
            for ecid in result["ecids_found"]:
                print(f"  - {ecid}")

        print("\nPer-page breakdown:")
        for detail in result["details"]:
            print(f"\n  Page: {detail['page_url']}")
            print(f"    Events checked: {detail['events_checked']}")
            print(f"    Events with ECID: {detail['events_with_ecid']}")
            if detail["ecids"]:
                print(f"    ECIDs: {', '.join(detail['ecids'])}")

        print("\n" + "=" * 60)
        print(f"Validation: {'PASSED ✓' if result['valid'] else 'FAILED ✗'}")
        print("=" * 60)
