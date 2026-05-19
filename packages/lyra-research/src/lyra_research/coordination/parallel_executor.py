"""Parallel executor for running multiple roles concurrently.

Supports parallel execution with timeout and error handling.
"""
from __future__ import annotations

import asyncio
from typing import Any, List

from lyra_research.roles.role_base import Role, RoleResult


class ParallelExecutor:
    """Executor for running multiple roles in parallel.

    Supports parallel execution with timeout and error handling.
    """

    def __init__(self) -> None:
        """Initialize parallel executor."""
        pass

    async def execute_parallel_roles(
        self, roles: List[Role], input_data: Any
    ) -> List[RoleResult]:
        """Execute multiple roles in parallel.

        Args:
            roles: List of roles to execute
            input_data: Input data for all roles

        Returns:
            List of RoleResults in same order as roles
        """
        # Create tasks for all roles
        tasks = [role.run(input_data) for role in roles]

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed RoleResults
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create failed result
                from lyra_research.roles.role_base import RoleStatus

                failed_result = RoleResult(
                    role_name=roles[i].name,
                    status=RoleStatus.FAILED,
                    data=None,
                    error=str(result),
                )
                failed_result.mark_complete()
                final_results.append(failed_result)
            else:
                final_results.append(result)

        return final_results

    async def execute_with_timeout(
        self, role: Role, input_data: Any, timeout_seconds: int
    ) -> RoleResult:
        """Execute role with timeout.

        Args:
            role: Role to execute
            input_data: Input data for the role
            timeout_seconds: Timeout in seconds

        Returns:
            RoleResult (may be failed if timeout)
        """
        try:
            result = await asyncio.wait_for(
                role.run(input_data), timeout=timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            # Create timeout result
            from lyra_research.roles.role_base import RoleStatus

            timeout_result = RoleResult(
                role_name=role.name,
                status=RoleStatus.FAILED,
                data=None,
                error=f"Execution timed out after {timeout_seconds} seconds",
            )
            timeout_result.mark_complete()
            return timeout_result
        except Exception as e:
            # Create failed result
            from lyra_research.roles.role_base import RoleStatus

            failed_result = RoleResult(
                role_name=role.name,
                status=RoleStatus.FAILED,
                data=None,
                error=str(e),
            )
            failed_result.mark_complete()
            return failed_result

    async def execute_with_retries(
        self,
        role: Role,
        input_data: Any,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> RoleResult:
        """Execute role with retries on failure.

        Args:
            role: Role to execute
            input_data: Input data for the role
            max_retries: Maximum number of retries
            retry_delay_seconds: Delay between retries in seconds

        Returns:
            RoleResult (last attempt if all fail)
        """
        from lyra_research.roles.role_base import RoleStatus

        last_result = None

        for attempt in range(max_retries + 1):
            result = await role.run(input_data)

            # Success - return immediately
            if result.status == RoleStatus.SUCCESS:
                return result

            # Failed - store result and retry if attempts remain
            last_result = result

            if attempt < max_retries:
                await asyncio.sleep(retry_delay_seconds)

        # All retries exhausted
        if last_result:
            last_result.error = f"{last_result.error} (after {max_retries} retries)"

        return last_result  # type: ignore

    async def execute_sequential(
        self, roles: List[Role], initial_input: Any
    ) -> List[RoleResult]:
        """Execute roles sequentially, passing output to next role.

        Args:
            roles: List of roles to execute in order
            initial_input: Input for first role

        Returns:
            List of RoleResults in execution order
        """
        results = []
        current_input = initial_input

        for role in roles:
            result = await role.run(current_input)
            results.append(result)

            # Stop on failure
            from lyra_research.roles.role_base import RoleStatus

            if result.status != RoleStatus.SUCCESS:
                break

            # Pass output to next role
            current_input = result.data

        return results

    async def execute_with_dependencies(
        self, role_graph: dict[str, tuple[Role, List[str]]], input_data: Any
    ) -> dict[str, RoleResult]:
        """Execute roles respecting dependencies.

        Args:
            role_graph: Dict mapping role name to (role, dependencies)
                       dependencies is list of role names that must complete first
            input_data: Initial input data

        Returns:
            Dict mapping role name to RoleResult
        """
        results: dict[str, RoleResult] = {}
        pending = set(role_graph.keys())
        running: dict[str, asyncio.Task] = {}

        while pending or running:
            # Find roles ready to execute (all dependencies met)
            ready = []
            for role_name in pending:
                role, deps = role_graph[role_name]
                if all(dep in results for dep in deps):
                    ready.append(role_name)

            # Start ready roles
            for role_name in ready:
                role, deps = role_graph[role_name]

                # Get input from dependencies or use initial input
                if deps:
                    # Use output from last dependency
                    role_input = results[deps[-1]].data
                else:
                    role_input = input_data

                # Start task
                task = asyncio.create_task(role.run(role_input))
                running[role_name] = task
                pending.remove(role_name)

            # Wait for at least one task to complete
            if running:
                done, _ = await asyncio.wait(
                    running.values(), return_when=asyncio.FIRST_COMPLETED
                )

                # Process completed tasks
                for task in done:
                    # Find role name for this task
                    role_name = next(
                        name for name, t in running.items() if t == task
                    )

                    # Get result
                    result = await task
                    results[role_name] = result

                    # Remove from running
                    del running[role_name]

        return results
