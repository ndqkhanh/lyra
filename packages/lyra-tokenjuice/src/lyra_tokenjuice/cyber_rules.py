"""
Cyber-Specific Compression Rules.

Specialized compression for:
- Nmap XML output
- Log files
- Exploit output
- Packet captures
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List


class CyberCompressor:
    """
    Cyber-specific compression rules.

    Optimized for security tool output.
    """

    def compress_nmap_xml(self, xml_content: str) -> str:
        """
        Compress nmap XML to structured summary.

        Args:
            xml_content: Nmap XML output

        Returns:
            Compressed summary
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return xml_content

        summary = []
        summary.append("# Nmap Scan Results\n")

        # Scan info
        scaninfo = root.find("scaninfo")
        if scaninfo is not None:
            summary.append(f"Scan: {scaninfo.get('type')} on {scaninfo.get('protocol')}\n")

        # Hosts
        for host in root.findall("host"):
            # Host address
            address = host.find("address")
            if address is not None:
                ip = address.get("addr")
                summary.append(f"\n## Host: {ip}\n")

            # Hostname
            hostnames = host.find("hostnames")
            if hostnames is not None:
                for hostname in hostnames.findall("hostname"):
                    summary.append(f"Hostname: {hostname.get('name')}\n")

            # Ports
            ports = host.find("ports")
            if ports is not None:
                open_ports = []
                for port in ports.findall("port"):
                    state = port.find("state")
                    if state is not None and state.get("state") == "open":
                        portid = port.get("portid")
                        protocol = port.get("protocol")
                        service = port.find("service")
                        service_name = service.get("name") if service is not None else "unknown"
                        open_ports.append(f"{portid}/{protocol} ({service_name})")

                if open_ports:
                    summary.append(f"Open ports: {', '.join(open_ports)}\n")

        return "".join(summary)

    def compress_log_file(self, log_content: str, preserve_errors: bool = True) -> str:
        """
        Compress log file, preserving anomalies.

        Args:
            log_content: Log file content
            preserve_errors: Keep error/warning lines

        Returns:
            Compressed log
        """
        lines = log_content.split("\n")
        compressed = []

        # Patterns to preserve
        important_patterns = [
            r"error",
            r"warning",
            r"critical",
            r"fail",
            r"exception",
            r"denied",
            r"unauthorized",
            r"forbidden",
        ]

        # Deduplicate similar lines
        seen_patterns = set()

        for line in lines:
            line_lower = line.lower()

            # Always keep important lines
            if preserve_errors and any(re.search(p, line_lower) for p in important_patterns):
                compressed.append(line)
                continue

            # Deduplicate repetitive lines
            # Extract pattern (remove timestamps, IPs, etc.)
            pattern = re.sub(r"\d{4}-\d{2}-\d{2}", "DATE", line)
            pattern = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "IP", pattern)
            pattern = re.sub(r"\d+", "NUM", pattern)

            if pattern not in seen_patterns:
                compressed.append(line)
                seen_patterns.add(pattern)

        return "\n".join(compressed)

    def compress_exploit_output(self, exploit_output: str) -> str:
        """
        Compress exploit output, keeping key indicators.

        Args:
            exploit_output: Exploit tool output

        Returns:
            Compressed output
        """
        lines = exploit_output.split("\n")
        compressed = []

        # Key indicators to preserve
        key_patterns = [
            r"exploit",
            r"payload",
            r"shell",
            r"success",
            r"fail",
            r"session",
            r"meterpreter",
            r"root",
            r"admin",
            r"password",
            r"credential",
        ]

        for line in lines:
            line_lower = line.lower()

            # Keep lines with key indicators
            if any(re.search(p, line_lower) for p in key_patterns):
                compressed.append(line)
            # Keep short lines (likely important)
            elif len(line) < 80:
                compressed.append(line)

        return "\n".join(compressed)

    def compress_vulnerability_report(self, report: str) -> str:
        """
        Compress vulnerability report.

        Args:
            report: Vulnerability report

        Returns:
            Compressed report
        """
        # Extract key sections
        sections = {
            "summary": [],
            "cvss": [],
            "affected": [],
            "remediation": [],
        }

        lines = report.split("\n")
        current_section = None

        for line in lines:
            line_lower = line.lower()

            # Detect sections
            if "summary" in line_lower or "description" in line_lower:
                current_section = "summary"
            elif "cvss" in line_lower or "severity" in line_lower:
                current_section = "cvss"
            elif "affected" in line_lower or "vulnerable" in line_lower:
                current_section = "affected"
            elif "remediation" in line_lower or "fix" in line_lower or "patch" in line_lower:
                current_section = "remediation"

            if current_section and line.strip():
                sections[current_section].append(line)

        # Build compressed report
        compressed = []

        if sections["summary"]:
            compressed.append("Summary: " + " ".join(sections["summary"][:2]))

        if sections["cvss"]:
            compressed.append("CVSS: " + " ".join(sections["cvss"][:1]))

        if sections["affected"]:
            compressed.append("Affected: " + " ".join(sections["affected"][:2]))

        if sections["remediation"]:
            compressed.append("Fix: " + " ".join(sections["remediation"][:2]))

        return "\n".join(compressed)

    def deduplicate_vulnerabilities(self, vulns: List[Dict]) -> List[Dict]:
        """
        Deduplicate similar vulnerabilities.

        Args:
            vulns: List of vulnerability dictionaries

        Returns:
            Deduplicated list
        """
        seen = set()
        deduplicated = []

        for vuln in vulns:
            # Create signature
            signature = (
                vuln.get("cve", ""),
                vuln.get("severity", ""),
                vuln.get("affected_service", ""),
            )

            if signature not in seen:
                deduplicated.append(vuln)
                seen.add(signature)

        return deduplicated
