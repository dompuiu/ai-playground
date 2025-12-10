"""
Mitmproxy management utilities for network request capture.
"""

import json
import subprocess
import time
import os
import signal
import re
from typing import List, Dict, Any


class CaptureAddon:
    """
    Mitmproxy addon to capture ping requests matching specific patterns.
    Groups captured requests by referrer (page URL).
    """

    def __init__(self, patterns: List[str], output_file: str = "ping_requests.json"):
        """
        Initialize the addon with regex patterns to match ping requests.

        Args:
            patterns: List of regex patterns to match against request URLs
            output_file: Path to save captured requests/responses
        """
        self.patterns = [re.compile(pattern) for pattern in patterns]
        self.output_file = output_file
        # Structure: {referrer_url: {request_url: {request: {...}, response: {...}}}}
        self.captured_data: Dict[str, Dict[str, Any]] = {}

    def request(self, flow) -> None:
        """
        Capture request data when a request matches our patterns.
        """
        url = flow.request.pretty_url

        # Check if URL matches any of the provided patterns
        if not any(pattern.search(url) for pattern in self.patterns):
            return

        # Get referrer from request headers
        referrer = flow.request.headers.get("Referer", "No Referrer")

        # Initialize referrer group if not exists
        if referrer not in self.captured_data:
            self.captured_data[referrer] = {}

        # Initialize entry for this URL if not exists
        if url not in self.captured_data[referrer]:
            self.captured_data[referrer][url] = {
                "request": None,
                "response": None,
            }

        # Capture request data in format compatible with validators
        self.captured_data[referrer][url]["request"] = {
            "url": url,
            "method": flow.request.method,
            "headers": dict(flow.request.headers),
            "payload": flow.request.content.decode("utf-8", errors="ignore")
            if flow.request.content
            else None,
            "timestamp": flow.request.timestamp_start,
        }

    def response(self, flow) -> None:
        """
        Capture response data when a response matches our patterns.
        """
        url = flow.request.pretty_url

        # Check if URL matches any of the provided patterns
        if not any(pattern.search(url) for pattern in self.patterns):
            return

        # Get referrer from request headers
        referrer = flow.request.headers.get("Referer", "No Referrer")

        # Initialize referrer group if not exists
        if referrer not in self.captured_data:
            self.captured_data[referrer] = {}

        # Initialize entry for this URL if not exists
        if url not in self.captured_data[referrer]:
            self.captured_data[referrer][url] = {
                "request": None,
                "response": None,
            }

        # Capture response data
        if flow.response:
            self.captured_data[referrer][url]["response"] = {
                "status_code": flow.response.status_code,
                "headers": dict(flow.response.headers),
                "content": flow.response.content.decode("utf-8", errors="ignore")
                if flow.response.content
                else None,
                "timestamp": flow.response.timestamp_start,
            }

    def done(self) -> None:
        """
        Called when mitmproxy is shutting down. Save captured data to file.
        """
        if self.captured_data:
            # Convert to validator-compatible format
            # Format: {page_url: {networkRequests: {...}}}
            output_data = {}
            total_requests = 0

            for referrer, requests in self.captured_data.items():
                output_data[referrer] = {
                    "html": "",  # Not captured by mitmproxy
                    "networkRequests": requests,
                }
                total_requests += len(requests)

            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(
                f"\nSaved {total_requests} requests grouped by {len(output_data)} referrer(s) to {self.output_file}"
            )


def start_mitmproxy(
    patterns: List[str], port: int = 9000, output_file: str = "requests.json"
) -> subprocess.Popen:
    """
    Start mitmproxy with the CaptureAddon.

    Args:
        patterns: List of regex patterns to match ping requests
        port: Port to run mitmproxy on (default: 9000)
        ping_output_file: Output file for ping requests

    Returns:
        Subprocess handle for the mitmproxy process
    """
    # Create a temporary Python script to configure the addon
    addon_script = f"""
import sys
sys.path.insert(0, '{os.getcwd()}')
from mitmproxy_utils import CaptureAddon

patterns = {patterns!r}
output_file = {output_file!r}
addons = [CaptureAddon(patterns, output_file)]
"""

    # Write the configuration script
    script_path = "mitmproxy_config.py"
    with open(script_path, "w") as f:
        f.write(addon_script)

    # Start mitmproxy
    print(f"Starting mitmproxy on port {port}...")
    process = subprocess.Popen(
        ["mitmdump", "-p", str(port), "-s", script_path, "--set", "flow_detail=0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait a bit for mitmproxy to start
    time.sleep(3)
    print(f"Mitmproxy started with PID {process.pid}")

    return process


def stop_mitmproxy(process: subprocess.Popen) -> None:
    """
    Stop the mitmproxy process gracefully.

    Args:
        process: The mitmproxy subprocess handle
    """
    if process and process.poll() is None:
        print(f"\nStopping mitmproxy (PID {process.pid})...")
        process.send_signal(signal.SIGTERM)

        # Wait for graceful shutdown
        try:
            process.wait(timeout=5)
            print("Mitmproxy stopped successfully")
        except subprocess.TimeoutExpired:
            print("Mitmproxy didn't stop gracefully, forcing...")
            process.kill()
            process.wait()

        # Clean up the config script
        if os.path.exists("mitmproxy_config.py"):
            os.remove("mitmproxy_config.py")
