#!/usr/bin/env python3
"""
Master validation script that runs all Adobe Analytics validators.
Provides a consolidated summary of all validation results.
"""

import sys
import subprocess
import os


def run_validator(script_name, args, description):
    """
    Run a validator script and capture its output.

    Args:
        script_name: Name of the validator script
        args: List of arguments to pass
        description: Description of the validator

    Returns:
        Tuple of (success, output)
    """
    try:
        script_path = os.path.join("validators", script_name)
        cmd = ["python3", script_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # Check if validation passed by looking for "PASSED" in output
        success = "PASSED ✓" in result.stdout or "Validation: PASSED" in result.stdout
        return success, result.stdout
    except Exception as e:
        return False, f"Error running {script_name}: {str(e)}"


def main():
    """Run all validators and provide summary."""
    file_path = sys.argv[1] if len(sys.argv) > 1 else "requests.json"
    time_window = sys.argv[2] if len(sys.argv) > 2 else "1.0"

    print("=" * 70)
    print("         ADOBE VALIDATION SUITE")
    print("=" * 70)
    print(f"\nAnalyzing: {file_path}")
    print(f"Duplicate time window: {time_window}s\n")

    validators = [
        {
            "name": "Required Fields",
            "script": "required_fields.py",
            "args": [file_path],
        },
        {
            "name": "ECID Consistency",
            "script": "ecid_consistency.py",
            "args": ["payload", file_path],
        },
        {
            "name": "Page View Integrity",
            "script": "page_view_integrity.py",
            "args": [file_path],
        },
        {
            "name": "No Duplicate Events",
            "script": "no_duplicate_events.py",
            "args": [file_path, time_window],
        },
        {
            "name": "Payload Size",
            "script": "payload_size.py",
            "args": [file_path, "32.0"],
        },
    ]

    results = []

    # Run each validator
    for i, validator in enumerate(validators, 1):
        print(f"[{i}/{len(validators)}] Running {validator['name']} Validator...")
        success, output = run_validator(
            validator["script"], validator["args"], validator["name"]
        )
        results.append(
            {"name": validator["name"], "success": success, "output": output}
        )
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"      {status}")

    # Print summary
    print("\n" + "=" * 70)
    print("         VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r["success"])
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}\n")

    for result in results:
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        print(f"{status} {result['name']}")

    print("\n" + "=" * 70)
    if passed == total:
        print("         ALL VALIDATIONS PASSED ✓")
    else:
        print(f"         {total - passed} VALIDATION(S) FAILED ✗")
    print("=" * 70)

    # Print detailed output if requested
    if "--verbose" in sys.argv or "-v" in sys.argv:
        print("\n\n" + "=" * 70)
        print("         DETAILED OUTPUT")
        print("=" * 70)
        for result in results:
            print(f"\n\n{'=' * 70}")
            print(f"{result['name']}")
            print("=" * 70)
            print(result["output"])

    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python3 run_validators.py [file_path] [time_window] [options]")
        print()
        print("Arguments:")
        print(
            "  file_path      Path to network requests JSON file (default: requests.json)"
        )
        print(
            "  time_window    Time window for duplicate detection in seconds (default: 1.0)"
        )
        print()
        print("Options:")
        print("  -v, --verbose  Show detailed output from each validator")
        print("  -h, --help     Show this help message")
        print()
        print("Examples:")
        print("  python3 run_validators.py")
        print("  python3 run_validators.py requests.json")
        print("  python3 run_validators.py requests.json 5.0")
        print("  python3 run_validators.py requests.json 1.0 --verbose")
        sys.exit(0)

    main()
