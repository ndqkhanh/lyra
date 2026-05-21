"""
Evolution Engine - Automatic reasoning strategy improvement.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..memory import ReasoningMemory
from ..types import ReasoningPattern, ReasoningStrategy, StrategyPerformance


@dataclass
class EvolutionReport:
    """Report from evolution cycle."""
    
    new_strategies: List[str]
    pruned_strategies: List[str]
    performance_delta: Dict[str, float]
    insights: List[str]


class EvolutionEngine:
    """
    Automatically improves reasoning capabilities.
    
    Features:
    - Strategy synthesis
    - Performance analysis
    - Automatic improvement
    - Pattern discovery
    """
    
    def __init__(self, memory: ReasoningMemory):
        self.memory = memory
        self.evolution_history: List[EvolutionReport] = []
    
    def evolve(self, min_samples: int = 10) -> EvolutionReport:
        """
        Run evolution cycle.
        
        Args:
            min_samples: Minimum samples needed for evolution
            
        Returns:
            Evolution report
        """
        # Analyze recent performance
        performance = self._analyze_performance()
        
        # Identify improvement opportunities
        opportunities = self._identify_opportunities(performance)
        
        # Synthesize new strategies (placeholder for now)
        new_strategies = self._synthesize_strategies(opportunities)
        
        # Prune ineffective strategies
        pruned = self._prune_strategies(performance)
        
        # Generate insights
        insights = self._generate_insights(performance, opportunities)
        
        # Calculate performance delta
        delta = self._calculate_delta(performance)
        
        report = EvolutionReport(
            new_strategies=new_strategies,
            pruned_strategies=pruned,
            performance_delta=delta,
            insights=insights,
        )
        
        self.evolution_history.append(report)
        
        return report
    
    def _analyze_performance(self) -> Dict[str, StrategyPerformance]:
        """Analyze strategy performance."""
        performances = self.memory.get_strategy_performance()
        
        return {
            perf.strategy.value: perf
            for perf in performances
        }
    
    def _identify_opportunities(
        self,
        performance: Dict[str, StrategyPerformance],
    ) -> List[str]:
        """Identify improvement opportunities."""
        opportunities = []
        
        for strategy_name, perf in performance.items():
            # Low success rate
            if perf.success_rate < 0.6 and perf.total_uses >= 5:
                opportunities.append(f"improve_{strategy_name}_success_rate")
            
            # High token usage
            if perf.avg_tokens > 15000:
                opportunities.append(f"reduce_{strategy_name}_token_usage")
            
            # Slow execution
            if perf.avg_duration > 300:
                opportunities.append(f"speed_up_{strategy_name}")
        
        return opportunities
    
    def _synthesize_strategies(self, opportunities: List[str]) -> List[str]:
        """
        Synthesize new strategies.
        
        For now, this is a placeholder. In production, this would:
        - Combine successful patterns
        - Generate new reasoning approaches
        - Test and validate new strategies
        """
        new_strategies = []
        
        # Get successful patterns
        patterns = self.memory.get_patterns()
        successful_patterns = [p for p in patterns if p.success_rate > 0.7]
        
        # Placeholder: suggest hybrid strategies
        if len(successful_patterns) >= 2:
            new_strategies.append("hybrid_cot_tree_search")
        
        return new_strategies
    
    def _prune_strategies(
        self,
        performance: Dict[str, StrategyPerformance],
    ) -> List[str]:
        """
        Prune ineffective strategies.
        
        For now, this is conservative - we don't actually remove strategies,
        just identify candidates for pruning.
        """
        pruned = []
        
        for strategy_name, perf in performance.items():
            # Very low success rate with enough samples
            if perf.success_rate < 0.3 and perf.total_uses >= 10:
                pruned.append(strategy_name)
        
        return pruned
    
    def _generate_insights(
        self,
        performance: Dict[str, StrategyPerformance],
        opportunities: List[str],
    ) -> List[str]:
        """Generate insights from performance analysis."""
        insights = []
        
        # Find best performing strategy
        if performance:
            best_strategy = max(
                performance.items(),
                key=lambda x: x[1].success_rate if x[1].total_uses >= 3 else 0,
            )
            insights.append(
                f"Best performing strategy: {best_strategy[0]} "
                f"(success rate: {best_strategy[1].success_rate:.2%})"
            )
        
        # Identify efficiency leaders
        if performance:
            most_efficient = min(
                performance.items(),
                key=lambda x: x[1].avg_tokens if x[1].total_uses >= 3 else float('inf'),
            )
            insights.append(
                f"Most token-efficient strategy: {most_efficient[0]} "
                f"(avg tokens: {most_efficient[1].avg_tokens:.0f})"
            )
        
        # Summarize opportunities
        if opportunities:
            insights.append(f"Identified {len(opportunities)} improvement opportunities")
        
        return insights
    
    def _calculate_delta(
        self,
        performance: Dict[str, StrategyPerformance],
    ) -> Dict[str, float]:
        """Calculate performance changes."""
        delta = {}
        
        # Compare with previous evolution cycle
        if len(self.evolution_history) >= 1:
            # For now, just return current success rates
            for strategy_name, perf in performance.items():
                delta[strategy_name] = perf.success_rate
        
        return delta
    
    def get_recommendations(self) -> List[str]:
        """Get strategy recommendations based on evolution history."""
        recommendations = []
        
        if not self.evolution_history:
            recommendations.append("Run evolution cycle to get recommendations")
            return recommendations
        
        latest = self.evolution_history[-1]
        
        # Recommend new strategies
        if latest.new_strategies:
            recommendations.append(
                f"Consider testing new strategies: {', '.join(latest.new_strategies)}"
            )
        
        # Warn about pruning candidates
        if latest.pruned_strategies:
            recommendations.append(
                f"Consider deprecating low-performing strategies: {', '.join(latest.pruned_strategies)}"
            )
        
        # Share insights
        recommendations.extend(latest.insights)
        
        return recommendations
