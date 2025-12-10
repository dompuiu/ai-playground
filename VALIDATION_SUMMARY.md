# Adobe Analytics Validation Suite - Summary

## Overview

A comprehensive validation suite for Adobe Experience Cloud tracking implementation. This suite validates the integrity and consistency of analytics events captured during web crawling sessions.

## Validators Implemented

### 1. Required Fields Validator ✓
**File:** `validators/required_fields.py`

**Purpose:** Validates that all events contain the required XDM fields.

**Validates:**
- Presence of `eventType` in `event.xdm.eventType`
- Presence of `timestamp` in `event.xdm.timestamp`
- Presence of `identityMap` in `event.xdm.identityMap`
- Provides statistics for each field
- Lists all events with missing fields

**Status:** ✓ Fully implemented and tested

---

### 2. ECID Consistency Validator ✓
**File:** `validators/ecid_consistency.py`

**Purpose:** Ensures all tracking events use the same Experience Cloud ID (ECID) throughout a session.

**Validates:**
- ECID extracted from `event.xdm.identityMap.ECID[0].id` in POST data
- Consistency across all pages and requests
- Excludes URL-based ECIDs (focuses on POST data only)

**Status:** ✓ Fully implemented and tested

---

### 3. Page View Integrity Validator ✓
**File:** `validators/page_view_integrity.py`

**Purpose:** Validates that each page load fires exactly one `web.webpagedetails.pageViews` event.

**Validates:**
- Count of page view events per page
- Identifies pages with 0 page views (missing tracking)
- Identifies pages with multiple page views (double-firing)
- Provides timestamps and event details

**Status:** ✓ Fully implemented and tested

---

### 4. No Duplicate Events Validator ✓
**File:** `validators/no_duplicate_events.py`

**Purpose:** Detects duplicate events with identical payloads within a configurable time window.

**Validates:**
- Creates SHA256 hash of POST payloads for comparison
- Checks for duplicates within specified time window (default: 1 second)
- Groups duplicate events and shows time spans
- Configurable time window for different use cases

**Status:** ✓ Fully implemented and tested

---

### 5. Payload Size Validator ✓
**File:** `validators/payload_size.py`

**Purpose:** Validates that all POST payloads are under the specified size limit.

**Validates:**
- Calculates size of each POST payload in bytes
- Validates payloads are under size limit (default: 32 KB)
- Provides size statistics (largest, smallest, average)
- Lists all oversized payloads with details
- Shows how much each payload exceeds the limit
- Configurable size limit

**Status:** ✓ Fully implemented and tested

---

## Master Validator Script

**File:** `run_validators.py`

A unified script that runs all validators and provides a consolidated summary.

**Features:**
- Runs all validators in sequence
- Provides summary of pass/fail status
- Supports verbose mode for detailed output
- Exit code 0 on success, 1 on failure (CI/CD friendly)
- Configurable time window for duplicate detection

**Usage:**
```bash
# Quick run with defaults
python3 run_validators.py

# Custom file and time window
python3 run_validators.py network_requests_grouped.json 5.0

# Verbose output
python3 run_validators.py network_requests_grouped.json 1.0 --verbose
```

---

## Test Results

Based on the current test data (`network_requests_grouped.json`):

| Validator | Status | Details |
|-----------|--------|---------|
| Required Fields | ✗ FAIL | 2/4 events missing required fields (eventType, timestamp, identityMap) |
| ECID Consistency | ✓ PASS | All events share ECID: 89050626930748798822279015352808145908 |
| Page View Integrity | ✗ FAIL | 2/3 pages have correct count (1 page missing page view event) |
| No Duplicate Events | ✓ PASS | No duplicates found within 1.0s window |
| Payload Size | ✓ PASS | All payloads under 32 KB (largest: 4.89 KB) |

**Overall:** 3/5 validators passed

---

## Architecture

### Data Flow

```
1. Crawler (index.py)
   ↓
   Generates: network_requests_grouped.json
   ↓
2. Validators
   ↓
   - required_fields.py
   - ecid_consistency.py
   - page_view_integrity.py  
   - no_duplicate_events.py
   - payload_size.py
   ↓
3. Master Validator (run_validators.py)
   ↓
   Consolidated Summary Report
```

### Input Data Format

All validators expect JSON with this structure:

```json
{
  "https://example.com/page": {
    "html": "...",
    "networkRequests": {
      "https://edge.server.com/interact?...": {
        "request": {
          "method": "POST",
          "post_data": "{...}",
          "timestamp": 1234567890.123
        },
        "response": {...},
        "response_failure": null
      }
    }
  }
}
```

### Validation Results Format

Each validator returns a dictionary with:

```python
{
    "valid": bool,              # Overall pass/fail
    "message": str,             # Human-readable summary
    "details": list,            # Per-page breakdown
    "total_*": int,             # Aggregate metrics
    # ... validator-specific fields
}
```

---

## Key Features

1. **Modular Design**: Each validator is independent and can be run standalone
2. **Consistent Interface**: All validators follow the same pattern
3. **Detailed Reporting**: Per-page breakdowns with specific failure details
4. **Configurable**: Support for custom time windows and file paths
5. **CI/CD Ready**: Exit codes and machine-readable output
6. **Extensible**: Easy to add new validators following the established pattern

---

## Adding New Validators

To add a new validator:

1. Create `validators/new_validator.py`
2. Implement extraction functions for your data
3. Implement validation logic function
4. Implement file-based validation function
5. Add `__main__` block for CLI usage
6. Update `validators/README.md`
7. Add to `run_validators.py` if desired

**Template:**

```python
def extract_data_from_post_data(post_data: str) -> Optional[Any]:
    """Extract specific data from POST payload"""
    # Implementation
    pass

def validate_something(network_data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform validation"""
    return {
        "valid": bool,
        "message": str,
        "details": list,
        # ...
    }

def validate_from_file(file_path: str) -> Dict[str, Any]:
    """Load and validate from file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return validate_something(data)

if __name__ == "__main__":
    # CLI implementation
    pass
```

---

## Future Enhancements

Potential additions to the validation suite:

1. **Event Timing Validator**: Verify events fire in correct order
2. **Required Fields Validator**: Check for mandatory XDM fields
3. **Data Type Validator**: Validate field types match schema
4. **Campaign Parameter Validator**: Verify UTM parameters are captured
5. **Cross-Domain Tracking Validator**: Check ECID persistence
6. **Consent Management Validator**: Verify consent signals
7. **Performance Validator**: Check for excessive request counts

---

## Documentation

- **Main README**: `validators/README.md` - Complete usage documentation
- **This Summary**: `VALIDATION_SUMMARY.md` - Architecture and overview
- **Inline Docs**: Comprehensive docstrings in all validator files

---

## Files Created/Modified

```
/validators/
  ├── required_fields.py           (New - validates required XDM fields)
  ├── ecid_consistency.py          (Updated with POST-only extraction)
  ├── page_view_integrity.py       (New - validates page view events)
  ├── no_duplicate_events.py       (New - detects duplicate payloads)
  ├── payload_size.py              (New - validates payload sizes < 32 KB)
  └── README.md                    (Updated with all validators)

/run_validators.py                 (Updated - master validation script)
/VALIDATION_SUMMARY.md            (Updated - this file)
```

---

## Conclusion

The Adobe Analytics Validation Suite provides a robust framework for ensuring tracking implementation quality. With five core validators and a master orchestration script, it delivers comprehensive validation coverage for the most critical tracking requirements:

1. **Required Fields** - Ensures data completeness
2. **ECID Consistency** - Maintains user identity integrity
3. **Page View Integrity** - Validates event firing accuracy
4. **No Duplicate Events** - Prevents double-tracking issues
5. **Payload Size** - Ensures payloads are within limits

**Status:** Production Ready ✓

