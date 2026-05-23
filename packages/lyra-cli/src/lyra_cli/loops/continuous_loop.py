"""Continuous loop - Run until stopped"""

from typing import Callable, Optional
import time


class ContinuousLoop:
    """Continuous loop execution"""

    def __init__(self, task: Callable, interval: int = 60):
        self.task = task
        self.interval = interval
        self.running = False
        self.iteration = 0

    def start(self, max_iterations: Optional[int] = None):
        """Start continuous loop"""
        self.running = True
        print(f"🔄 Starting continuous loop (interval: {self.interval}s)")

        while self.running:
            self.iteration += 1
            print(f"\n📍 Iteration {self.iteration}")

            try:
                # Execute task
                result = self.task()
                print(f"✅ Iteration {self.iteration} completed")

                # Check max iterations
                if max_iterations and self.iteration >= max_iterations:
                    print(f"🏁 Reached max iterations ({max_iterations})")
                    break

                # Wait for next iteration
                if self.running:
                    print(f"⏳ Waiting {self.interval}s...")
                    time.sleep(self.interval)

            except KeyboardInterrupt:
                print("\n⏸️  Loop interrupted by user")
                break
            except Exception as e:
                print(f"❌ Iteration {self.iteration} error: {e}")
                break

        self.running = False
        print(f"\n🏁 Loop stopped after {self.iteration} iteration(s)")

    def stop(self):
        """Stop continuous loop"""
        self.running = False


def create_continuous_loop(task: Callable, interval: int = 60) -> ContinuousLoop:
    """Create a continuous loop"""
    return ContinuousLoop(task, interval)
