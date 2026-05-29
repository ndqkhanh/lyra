"""
Demo script showing Lyra multi-agent orchestration in action.
"""

import asyncio

from src.agents import CodeAgent, PrimaryAgent, ResearchAgent, ReviewAgent, TestAgent
from src.core.task import Task, TaskType


async def demo_basic_orchestration():
    """Demonstrate basic agent orchestration."""
    print("=" * 70)
    print("LYRA MULTI-AGENT ORCHESTRATION DEMO")
    print("=" * 70)
    print()

    # 1. Create primary agent
    print("📋 Step 1: Creating Primary Agent (Orchestrator)")
    primary = PrimaryAgent()
    print(f"   ✓ Created: {primary}")
    print()

    # 2. Create specialist agents
    print("📋 Step 2: Creating Specialist Agents")
    code_agent = CodeAgent()
    research_agent = ResearchAgent()
    test_agent = TestAgent()
    review_agent = ReviewAgent()

    print(f"   ✓ Code Agent: {code_agent}")
    print(f"   ✓ Research Agent: {research_agent}")
    print(f"   ✓ Test Agent: {test_agent}")
    print(f"   ✓ Review Agent: {review_agent}")
    print()

    # 3. Register specialists with primary
    print("📋 Step 3: Registering Specialists")
    primary.register_specialist(code_agent)
    primary.register_specialist(research_agent)
    primary.register_specialist(test_agent)
    primary.register_specialist(review_agent)
    print()

    # 4. Show statistics
    print("📋 Step 4: System Statistics")
    stats = primary.get_statistics()
    print(f"   Primary Agent: {stats['agent_id']}")
    print(f"   Status: {stats['status']}")
    print(f"   Specialists: {stats['specialists_count']}")
    print(f"   Registered: {', '.join(stats['specialists'])}")
    print()

    # 5. Execute various tasks
    print("=" * 70)
    print("EXECUTING TASKS")
    print("=" * 70)
    print()

    # Task 1: Code generation
    print("🔹 Task 1: Code Generation")
    response = await primary.handle_request("Implement a function to calculate fibonacci numbers")
    print(f"   {response}")
    print()

    # Task 2: Research
    print("🔹 Task 2: Research")
    response = await primary.handle_request("Research best practices for async Python")
    print(f"   {response}")
    print()

    # Task 3: Testing
    print("🔹 Task 3: Test Generation")
    response = await primary.handle_request("Generate tests for the authentication module")
    print(f"   {response}")
    print()

    # Task 4: Code review
    print("🔹 Task 4: Code Review")
    response = await primary.handle_request("Review the database connection code")
    print(f"   {response}")
    print()

    # 6. Show final statistics
    print("=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)
    print()

    stats = primary.get_statistics()
    print(f"Total Executions: {stats['total_executions']}")
    print(f"Success Rate: {stats['success_rate']:.1%}")
    print()

    for agent in [code_agent, research_agent, test_agent, review_agent]:
        print(f"{agent.agent_id}:")
        print(f"  Executions: {len(agent.execution_history)}")
        print(f"  Success Rate: {agent.get_success_rate():.1%}")
    print()


async def demo_parallel_execution():
    """Demonstrate parallel task execution."""
    print("=" * 70)
    print("PARALLEL EXECUTION DEMO")
    print("=" * 70)
    print()

    # Create and setup agents
    primary = PrimaryAgent()
    primary.register_specialist(CodeAgent())
    primary.register_specialist(ResearchAgent())
    primary.register_specialist(TestAgent())
    primary.register_specialist(ReviewAgent())

    # Create multiple tasks
    tasks = [
        Task(type=TaskType.CODE_GENERATION, description="Implement user authentication"),
        Task(type=TaskType.RESEARCH, description="Research OAuth 2.0 best practices"),
        Task(type=TaskType.TEST_GENERATION, description="Generate auth tests"),
        Task(type=TaskType.CODE_REVIEW, description="Review auth implementation"),
    ]

    print(f"📋 Executing {len(tasks)} tasks in parallel...")
    print()

    # Execute in parallel
    import time
    start = time.time()
    results = await primary.execute_parallel(tasks)
    duration = time.time() - start

    # Show results
    print("Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.success else "❌"
        print(f"  {status} Task {i}: {result.agent_id} - {result.success}")

    print()
    print(f"⏱️  Total time: {duration:.2f}s")
    print(f"📊 Success rate: {sum(1 for r in results if r.success) / len(results):.1%}")
    print()


async def demo_agent_capabilities():
    """Demonstrate agent capability matching."""
    print("=" * 70)
    print("AGENT CAPABILITY MATCHING DEMO")
    print("=" * 70)
    print()

    # Create agents
    agents = [
        CodeAgent(),
        ResearchAgent(),
        TestAgent(),
        ReviewAgent(),
    ]

    # Test different task types
    test_tasks = [
        Task(type=TaskType.CODE_GENERATION, description="Generate code"),
        Task(type=TaskType.RESEARCH, description="Research topic"),
        Task(type=TaskType.TEST_GENERATION, description="Generate tests"),
        Task(type=TaskType.CODE_REVIEW, description="Review code"),
        Task(type=TaskType.SECURITY_SCAN, description="Security scan"),
    ]

    print("Task Type Matching:")
    print()

    for task in test_tasks:
        print(f"📋 {task.type.value}:")
        for agent in agents:
            confidence = agent.can_handle(task)
            if confidence > 0:
                print(f"   ✓ {agent.agent_id}: {confidence:.0%} confidence")
        print()


async def main():
    """Run all demos."""
    await demo_basic_orchestration()
    await asyncio.sleep(1)

    await demo_parallel_execution()
    await asyncio.sleep(1)

    await demo_agent_capabilities()

    print("=" * 70)
    print("✅ ALL DEMOS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
