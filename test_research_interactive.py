#!/usr/bin/env python3
"""Interactive test of Lyra research command."""

import subprocess
import time
import sys

def test_research_command():
    """Test /research command interactively."""
    print("=" * 80)
    print("INTERACTIVE RESEARCH TEST")
    print("=" * 80)

    # Start ly process
    print("\nStarting Lyra with DeepSeek...")
    proc = subprocess.Popen(
        ["ly", "--model", "deepseek"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Wait for prompt
    time.sleep(2)

    # Send research command
    print("Sending: /research Python async patterns --depth quick")
    proc.stdin.write("/research Python async patterns --depth quick\n")
    proc.stdin.flush()

    # Wait for research to complete (max 60 seconds)
    print("Waiting for research to complete...")
    start_time = time.time()
    output_lines = []

    while time.time() - start_time < 60:
        try:
            line = proc.stdout.readline()
            if line:
                output_lines.append(line)
                print(line.rstrip())

                # Check for completion indicators
                if "Research complete" in line or "Report" in line or "Sources analyzed" in line:
                    print("\n✓ Research completed!")
                    break
        except:
            break

    # Send exit command
    print("\nSending: /exit")
    proc.stdin.write("/exit\n")
    proc.stdin.flush()

    # Wait for process to finish
    proc.wait(timeout=5)

    # Analyze output
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    full_output = "".join(output_lines)

    if "Research complete" in full_output or "Sources analyzed" in full_output:
        print("✓ Research command executed successfully")
        return True
    else:
        print("✗ Research command did not complete")
        print(f"Captured {len(output_lines)} lines of output")
        return False

if __name__ == "__main__":
    try:
        success = test_research_command()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
