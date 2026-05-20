# Phase 4 — Context Window Visualization

Module: `context_viz.py`

Context window tracking and visualization.

```python
from lyra_ui import (
    ContextTracker,
    ContextComponent,
    ContextRingVisualizer,
    ContextManager,
)

tracker = ContextTracker(total_tokens=200000)

# Add tokens by component
tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 5000)
tracker.add_tokens(ContextComponent.CONVERSATION, 50000)
tracker.add_tokens(ContextComponent.TOOL_RESULTS, 20000)
tracker.add_tokens(ContextComponent.CODE_CONTEXT, 15000)

# Stats
total_used = tracker.get_total_used()           # 90000
total_percentage = tracker.get_total_percentage()  # 45.0

# Visualize
viz = ContextRingVisualizer()
viz.display(tracker)  # Ring chart + breakdown table

# Recommendations
manager = ContextManager(tracker)
recommendations = manager.get_recommendations()
```

**Features**

- Component-level token tracking
- Context ring visualization with color coding
- Breakdown table with percentages
- Context export / import
- Component pruning
- Optimization recommendations
