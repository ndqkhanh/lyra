"""
Prompt optimization for different model families.

Optimizes prompts for Claude (XML tags, structured output) and
GPT (JSON mode, function calling) to maximize model performance.
"""


class PromptOptimizer:
    """Optimize prompts for different model families."""

    def optimize_for_claude(self, base_prompt: str) -> str:
        """
        Optimize prompt for Claude models (XML tags, structured output).

        Args:
            base_prompt: Base prompt to optimize

        Returns:
            Optimized prompt for Claude
        """
        # Add XML structure for Claude
        optimized = f"""<task>
{base_prompt}
</task>

<instructions>
Provide your response in a clear, structured format.
Use reasoning steps where appropriate.
</instructions>"""
        return optimized

    def optimize_for_gpt(self, base_prompt: str) -> str:
        """
        Optimize prompt for GPT models (JSON mode, function calling).

        Args:
            base_prompt: Base prompt to optimize

        Returns:
            Optimized prompt for GPT
        """
        # Add structured instructions for GPT
        optimized = f"""{base_prompt}

Please provide your response in a structured format.
Think step-by-step and explain your reasoning.
"""
        return optimized

    def optimize_for_model(self, base_prompt: str, model: str) -> str:
        """
        Auto-detect model family and optimize.

        Args:
            base_prompt: Base prompt to optimize
            model: Model identifier

        Returns:
            Optimized prompt for the model
        """
        if model.startswith("claude-"):
            return self.optimize_for_claude(base_prompt)
        elif model.startswith("gpt-"):
            return self.optimize_for_gpt(base_prompt)
        else:
            # Return base prompt for unknown models
            return base_prompt

    def add_output_format(
        self,
        prompt: str,
        format_type: str,
        model: str
    ) -> str:
        """
        Add output format instructions to prompt.

        Args:
            prompt: Base prompt
            format_type: Desired format (json, markdown, xml)
            model: Model identifier

        Returns:
            Prompt with format instructions
        """
        if model.startswith("claude-"):
            if format_type == "json":
                return f"{prompt}\n\n<output_format>JSON</output_format>"
            elif format_type == "xml":
                return f"{prompt}\n\n<output_format>XML</output_format>"
            else:
                return f"{prompt}\n\n<output_format>{format_type}</output_format>"
        else:
            return f"{prompt}\n\nProvide output in {format_type} format."

    def add_examples(
        self,
        prompt: str,
        examples: list[tuple[str, str]],
        model: str
    ) -> str:
        """
        Add few-shot examples to prompt.

        Args:
            prompt: Base prompt
            examples: List of (input, output) example tuples
            model: Model identifier

        Returns:
            Prompt with examples
        """
        if not examples:
            return prompt

        if model.startswith("claude-"):
            examples_text = "\n\n".join(
                f"<example>\n<input>{inp}</input>\n<output>{out}</output>\n</example>"
                for inp, out in examples
            )
            return f"{prompt}\n\n<examples>\n{examples_text}\n</examples>"
        else:
            examples_text = "\n\n".join(
                f"Example {i+1}:\nInput: {inp}\nOutput: {out}"
                for i, (inp, out) in enumerate(examples)
            )
            return f"{prompt}\n\nExamples:\n{examples_text}"
