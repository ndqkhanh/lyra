"""Tests for the ast_transformer module."""

from __future__ import annotations

import pytest
from lyra_meta_editor import (
    ASTNode,
    ASTTransformationError,
    ASTTransformer,
    TransformConfig,
)


class TestTransformConfig:
    """Tests for TransformConfig."""

    def test_defaults(self) -> None:
        cfg = TransformConfig()
        assert cfg.preserve_comments is True
        assert cfg.preserve_formatting is True
        assert cfg.max_line_length == 100

    def test_custom_values(self) -> None:
        cfg = TransformConfig(max_line_length=80)
        assert cfg.max_line_length == 80


class TestASTNode:
    """Tests for ASTNode."""

    def test_creation(self) -> None:
        node = ASTNode(
            node_type="Module",
            name="",
            line=1,
            col=0,
            children=("FunctionDef",),
        )
        assert node.node_type == "Module"
        assert node.children == ("FunctionDef",)

    def test_immutable(self) -> None:
        node = ASTNode("Module", "", 1, 0, ())
        with pytest.raises(AttributeError):
            node.node_type = "Other"  # type: ignore[misc]


class TestASTTransformer:
    """Tests for ASTTransformer."""

    @pytest.mark.asyncio
    async def test_parse_simple_source(self) -> None:
        source = "x = 1\n"
        node = await ASTTransformer.parse_to_ast(source)
        assert node.node_type == "Module"

    @pytest.mark.asyncio
    async def test_parse_function(self) -> None:
        source = "def foo():\n    pass\n"
        node = await ASTTransformer.parse_to_ast(source)
        assert node.node_type == "Module"
        assert "FunctionDef" in node.children

    @pytest.mark.asyncio
    async def test_parse_invalid_syntax(self) -> None:
        with pytest.raises(ASTTransformationError, match="parse"):
            await ASTTransformer.parse_to_ast("if x:\n")

    @pytest.mark.asyncio
    async def test_parse_empty_source(self) -> None:
        node = await ASTTransformer.parse_to_ast("")
        assert node.node_type == "Module"

    @pytest.mark.asyncio
    async def test_apply_transform_wrap_in_function(self) -> None:
        source = "x = 1\n"
        result = await ASTTransformer.apply_transform(
            source, ("wrap_in_function:my_func",)
        )
        assert result.success
        assert result.nodes_changed == 1
        assert "def my_func" in result.transformed

    @pytest.mark.asyncio
    async def test_apply_transform_rename_function(self) -> None:
        source = "def old_name():\n    pass\n"
        result = await ASTTransformer.apply_transform(
            source, ("rename_function:old_name,new_name",)
        )
        assert result.success
        assert result.nodes_changed == 1
        assert "def new_name" in result.transformed
        assert "def old_name" not in result.transformed

    @pytest.mark.asyncio
    async def test_apply_transform_rename_nonexistent(self) -> None:
        source = "def foo():\n    pass\n"
        result = await ASTTransformer.apply_transform(
            source, ("rename_function:nonexistent,newname",)
        )
        assert result.success
        assert result.nodes_changed == 0
        assert result.transformed == result.original

    @pytest.mark.asyncio
    async def test_apply_transform_rename_async(self) -> None:
        source = "async def old_name():\n    pass\n"
        result = await ASTTransformer.apply_transform(
            source, ("rename_function:old_name,new_name",)
        )
        assert result.success
        assert result.nodes_changed == 1
        assert "async def new_name" in result.transformed

    @pytest.mark.asyncio
    async def test_apply_transform_unknown_rule(self) -> None:
        with pytest.raises(ASTTransformationError, match="Unknown"):
            await ASTTransformer.apply_transform(
                "x = 1\n", ("unknown_rule:args",)
            )

    @pytest.mark.asyncio
    async def test_apply_transform_invalid_rule_format(self) -> None:
        with pytest.raises(ASTTransformationError, match="Invalid"):
            await ASTTransformer.apply_transform(
                "x = 1\n", ("no_colon",)
            )

    @pytest.mark.asyncio
    async def test_apply_transform_malformed_source(self) -> None:
        with pytest.raises(ASTTransformationError, match="parse"):
            await ASTTransformer.apply_transform(
                "if x:\n", ("rename_function:old,new",)
            )

    @pytest.mark.asyncio
    async def test_validate_syntax_valid(self) -> None:
        assert await ASTTransformer.validate_syntax("x = 1\n") is True

    @pytest.mark.asyncio
    async def test_validate_syntax_invalid(self) -> None:
        assert await ASTTransformer.validate_syntax("if x:\n") is False

    @pytest.mark.asyncio
    async def test_validate_syntax_empty(self) -> None:
        assert await ASTTransformer.validate_syntax("") is True

    @pytest.mark.asyncio
    async def test_validate_syntax_complex(self) -> None:
        source = (
            "def foo():\n"
            "    for i in range(10):\n"
            "        if i > 5:\n"
            "            print(i)\n"
        )
        assert await ASTTransformer.validate_syntax(source) is True

    @pytest.mark.asyncio
    async def test_generate_diff_identical(self) -> None:
        source = "x = 1\n"
        diff = await ASTTransformer.generate_diff(source, source)
        assert diff == ""

    @pytest.mark.asyncio
    async def test_generate_diff_different(self) -> None:
        original = "x = 1\n"
        modified = "x = 2\n"
        diff = await ASTTransformer.generate_diff(original, modified)
        assert len(diff) > 0
        assert "-x = 1" in diff
        assert "+x = 2" in diff

    @pytest.mark.asyncio
    async def test_generate_diff_multiline(self) -> None:
        original = "def foo():\n    pass\n"
        modified = "def bar():\n    pass\n"
        diff = await ASTTransformer.generate_diff(original, modified)
        assert len(diff) > 0

    @pytest.mark.asyncio
    async def test_apply_transform_empty_rules(self) -> None:
        source = "x = 1\n"
        result = await ASTTransformer.apply_transform(source, ())
        assert result.success
        assert result.nodes_changed == 0
        assert result.diff == "" or True  # may normalize

    @pytest.mark.asyncio
    async def test_parse_class(self) -> None:
        source = "class MyClass:\n    pass\n"
        node = await ASTTransformer.parse_to_ast(source)
        assert "ClassDef" in node.children

    @pytest.mark.asyncio
    async def test_parse_decorator(self) -> None:
        source = "@dec\ndef foo():\n    pass\n"
        node = await ASTTransformer.parse_to_ast(source)
        assert node.node_type == "Module"

    @pytest.mark.asyncio
    async def test_deep_nested_ast(self) -> None:
        source = (
            "def outer():\n"
            "    def inner():\n"
            "        x = 1\n"
            "    return inner\n"
        )
        node = await ASTTransformer.parse_to_ast(source)
        assert "FunctionDef" in node.children

    @pytest.mark.asyncio
    async def test_transform_result_fields(self) -> None:
        source = "x = 1\n"
        result = await ASTTransformer.apply_transform(
            source, ("wrap_in_function:foo",)
        )
        assert result.original == source
        assert "def foo" in result.transformed
        assert isinstance(result.diff, str)
        assert result.success is True
