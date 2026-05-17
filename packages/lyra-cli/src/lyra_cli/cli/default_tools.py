"""Example tools for LLM tool calling."""
import asyncio


async def read_file(path: str) -> str:
    """Read a file from the filesystem."""
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


async def search_code(query: str, path: str = ".") -> str:
    """Search for code patterns using grep."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "grep", "-r", query, path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode()[:1000]  # Limit output
    except Exception as e:
        return f"Error searching: {str(e)}"


async def list_files(directory: str = ".") -> str:
    """List files in a directory."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ls", "-la", directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode()[:1000]  # Limit output
    except Exception as e:
        return f"Error listing files: {str(e)}"


def register_default_tools(registry) -> None:
    """Register default tools with the registry."""
    registry.register(
        name="read_file",
        description="Read contents of a file",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
        executor=read_file,
        idempotent=True,  # Safe for eager dispatch
    )

    registry.register(
        name="search_code",
        description="Search for code patterns",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "path": {"type": "string", "description": "Directory to search"},
            },
            "required": ["query"],
        },
        executor=search_code,
        idempotent=True,  # Safe for eager dispatch
    )

    registry.register(
        name="list_files",
        description="List files in a directory",
        parameters={
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory path"},
            },
            "required": [],
        },
        executor=list_files,
        idempotent=True,  # Safe for eager dispatch
    )
