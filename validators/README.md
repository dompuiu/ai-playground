# Adobe Analytics Validators

This directory contains validators for Adobe Experience Cloud tracking implementation.

## Quick Start

```bash
# Run all validators at once
python3 run_validators.py

# Run with verbose output
python3 run_validators.py network_requests_grouped.json 1.0 --verbose
```

## Available Validators

### 1. Required Fields Validator (`required_fields.py`)

Validates that all events contain the required XDM fields: eventType, timestamp, and identityMap.

**Usage:**
```bash
python3 validators/required_fields.py network_requests_grouped.json
```

**What it checks:**
- Presence of `eventType` in `event.xdm.eventType`
- Presence of `timestamp` in `event.xdm.timestamp`
- Presence of `identityMap` in `event.xdm.identityMap`
- Provides statistics for each field
- Lists all events missing required fields

**Example output:**
```
REQUIRED FIELDS VALIDATION
✓ All 4 events have required fields (eventType, timestamp, identityMap)

Total POST requests checked: 4
Events with all required fields: 4
Events missing fields: 0

Field Statistics:
✓ eventType:
    Present: 4/4
    Missing: 0/4
✓ timestamp:
    Present: 4/4
    Missing: 0/4
✓ identityMap:
    Present: 4/4
    Missing: 0/4
```

### 2. ECID Consistency Validator (`ecid_consistency.py`)

Validates that all requests contain the same ECID (Experience Cloud ID) across a crawl session.

**Usage:**
```bash
# Validate POST data ECIDs only (recommended - excludes URLs)
python3 validators/ecid_consistency.py post_data network_requests_grouped.json

# Validate all ECIDs (includes URLs, headers, responses)
python3 validators/ecid_consistency.py all network_requests_grouped.json
```

**What it checks:**
- Extracts ECID from `event.xdm.identityMap.ECID[0].id` in POST data
- Validates that all POST requests share the same ECID
- Provides per-page breakdown of ECID usage

**Example output:**
```
POST Data ECID Validation Results
✓ All POST data requests share the same ECID: 17703841390766917980955670073436534760

Total POST requests checked: 4
POST requests with ECID: 2
Unique ECIDs found: 1
```

### 3. Page View Integrity Validator (`page_view_integrity.py`)

Validates that each page load fires exactly one `web.webpagedetails.pageViews` event.

**Usage:**
```bash
python3 validators/page_view_integrity.py network_requests_grouped.json
```

**What it checks:**
- Counts `web.webpagedetails.pageViews` events per page
- Validates that each page has exactly 1 page view event
- Identifies pages with 0 or multiple page view events
- Provides detailed event information including timestamps

**Example output:**
```
PAGE VIEW FIRING INTEGRITY VALIDATION
✓ All 3 pages have exactly 1 page view event

Total pages crawled: 3
Pages with exactly 1 page view event: 3
Pages with 0 page view events: 0
Pages with multiple page view events: 0
```

### 4. No Duplicate Events Validator (`no_duplicate_events.py`)

Validates that no identical event payloads are sent within a specified time window (default: 1 second).

**Usage:**
```bash
# Check for duplicates within 1 second (default)
python3 validators/no_duplicate_events.py network_requests_grouped.json

# Check for duplicates within custom time window (e.g., 5 seconds)
python3 validators/no_duplicate_events.py network_requests_grouped.json 5.0
```

**What it checks:**
- Creates SHA256 hash of each POST request payload
- Compares payloads within the specified time window
- Detects identical events that may indicate double-firing
- Groups duplicates and shows time span between them
- Provides event type and timestamp information

**Example output:**
```
NO DUPLICATE EVENTS VALIDATION
✓ No duplicate events found (checked 4 POST requests)

Time window: 1.0s
Total POST requests checked: 4
Duplicate groups found: 0
Total duplicate events: 0
```

**Example failure output:**
```
NO DUPLICATE EVENTS VALIDATION
✗ Found 1 duplicate group(s) with 1 duplicate event(s) within 1.0s window

[Group 1]
  Event Type: web.webpagedetails.pageViews
  Duplicate Count: 2 identical events
  Time Span: 0.342s
  Payload Hash: a3f5d8e9c2b4f1a7...
```

### 5. Payload Size Validator (`payload_size.py`)

Validates that all POST payloads are under the specified size limit (default: 32 KB).

**Usage:**
```bash
# Check with default 32 KB limit
python3 validators/payload_size.py network_requests_grouped.json

# Check with custom size limit (e.g., 64 KB)
python3 validators/payload_size.py network_requests_grouped.json 64.0
```

**What it checks:**
- Calculates size of each POST payload in bytes
- Validates payloads are under the size limit
- Provides payload size statistics (largest, smallest, average)
- Lists all oversized payloads with details
- Shows how much each payload exceeds the limit

**Example output:**
```
PAYLOAD SIZE VALIDATION
✓ All 4 payloads are under 32.0 KB limit

Size limit: 32.0 KB (32,768 bytes)
Total POST requests checked: 4
Payloads under limit: 4
Payloads over limit: 0

Payload Size Statistics:
Largest payload:  4.89 KB (5,010 bytes)
Smallest payload: 3.42 KB (3,507 bytes)
Average payload:  3.91 KB (4,008 bytes)
```

**Example failure output:**
```
PAYLOAD SIZE VALIDATION
✗ Payload size validation failed: 1/4 payload(s) exceed 4.0 KB limit

Oversized Payloads:
[1] Page: https://example.com/page
    Event Type: web.webpagedetails.pageViews
    Payload Size: 4.89 KB (5,010 bytes)
    Exceeds Limit By: 0.89 KB (914 bytes)
    Percentage of Limit: 122.3%
```

## Input Data Format

All validators expect a JSON file with the following structure:

```json
{
  "https://example.com/page1": {
    "html": "...",
    "networkRequests": {
      "https://edge.server.com/interact?...": {
        "request": {
          "method": "POST",
          "post_data": "{...}",
          ...
        },
        "response": {...},
        "response_failure": null
      }
    }
  }
}
```

This format is generated by the crawler in `crawler.py`.

## Running Validators

### Option 1: Run All Validators at Once (Recommended)

Use the master validator script in the project root:

```bash
# Run all validators with default settings
python3 run_validators.py

# Specify custom file and time window
python3 run_validators.py network_requests_grouped.json 5.0

# Show detailed output from each validator
python3 run_validators.py network_requests_grouped.json 1.0 --verbose

# Show help
python3 run_validators.py --help
```

**Example output:**
```
ADOBE ANALYTICS VALIDATION SUITE
Analyzing: network_requests_grouped.json
Duplicate time window: 1.0s

[1/3] Running ECID Consistency Validator...
      ✓ PASS
[2/3] Running Page View Integrity Validator...
      ✗ FAIL
[3/3] Running No Duplicate Events Validator...
      ✓ PASS

VALIDATION SUMMARY
Tests Passed: 2/3

✓ PASS ECID Consistency
✗ FAIL Page View Integrity
✓ PASS No Duplicate Events
```

### Option 2: Run Individual Validators

1. First, run the crawler to generate the network requests JSON:
   ```bash
   python3 index.py
   ```

2. Then run the validators:
   ```bash
   # Check required fields
   python3 validators/required_fields.py network_requests_grouped.json
   
   # Check ECID consistency
   python3 validators/ecid_consistency.py post_data network_requests_grouped.json
   
   # Check page view integrity
   python3 validators/page_view_integrity.py network_requests_grouped.json
   
   # Check for duplicate events
   python3 validators/no_duplicate_events.py network_requests_grouped.json
   
   # Check payload sizes
   python3 validators/payload_size.py network_requests_grouped.json
   ```

3. Run all validators sequentially:
   ```bash
   # Run all validators one after another
   python3 validators/required_fields.py network_requests_grouped.json && \
   python3 validators/ecid_consistency.py post_data network_requests_grouped.json && \
   python3 validators/page_view_integrity.py network_requests_grouped.json && \
   python3 validators/no_duplicate_events.py network_requests_grouped.json && \
   python3 validators/payload_size.py network_requests_grouped.json
   ```

## Adding New Validators

To add a new validator:

1. Create a new Python file in the `validators/` directory
2. Follow the pattern of extracting data from POST requests
3. Return a dictionary with validation results including:
   - `valid`: boolean indicating pass/fail
   - `message`: human-readable summary
   - `details`: per-page breakdown
4. Add a `__main__` block for command-line usage
5. Update this README with usage instructions
