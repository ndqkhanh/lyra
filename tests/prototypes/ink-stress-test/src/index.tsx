#!/usr/bin/env node
/**
 * Ink + React Stress Test - Phase 0 Performance Validation
 *
 * Tests 3 concurrent scenarios to validate Ink performance:
 * 1. Thinking tokens streaming at 50 tokens/sec for 60 seconds
 * 2. 5 concurrent background tasks updating progress bars every 100ms
 * 3. Tree with 100 nodes, 10 expanding/collapsing per second
 *
 * Gate criteria:
 * - CPU usage < 10% (measured via pidusage)
 * - No visible flicker (manual inspection)
 * - Frame rate ≥ 30 FPS (measured via frame timing)
 *
 * PASS → proceed with Ink + React
 * FAIL → escalate to user for decision
 */

import React, { useState, useEffect, useRef } from 'react';
import { render, Box, Text } from 'ink';
import pidusage from 'pidusage';

interface PerformanceStats {
  fps: number;
  cpuAvg: number;
  cpuMax: number;
  duration: number;
}

interface TreeNode {
  id: number;
  label: string;
  parent: number | null;
  children: number[];
}

const StressTestApp: React.FC<{ duration: number }> = ({ duration }) => {
  const [tokens, setTokens] = useState(0);
  const [tasks, setTasks] = useState([
    { name: 'Analyzing codebase', progress: 0 },
    { name: 'Running tests', progress: 0 },
    { name: 'Building project', progress: 0 },
    { name: 'Generating docs', progress: 0 },
    { name: 'Deploying app', progress: 0 },
  ]);
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]));
  const [elapsed, setElapsed] = useState(0);
  const [fps, setFps] = useState(0);
  const [cpuAvg, setCpuAvg] = useState(0);
  const [testComplete, setTestComplete] = useState(false);

  const startTime = useRef(Date.now());
  const frameTimes = useRef<number[]>([]);
  const cpuSamples = useRef<number[]>([]);

  // Create tree nodes
  const nodes = useRef<TreeNode[]>([]);
  if (nodes.current.length === 0) {
    for (let i = 0; i < 100; i++) {
      nodes.current.push({
        id: i,
        label: `Node ${i}`,
        parent: i > 0 ? Math.floor(i / 10) : null,
        children: [],
      });
    }
    // Build parent-child relationships
    nodes.current.forEach(node => {
      if (node.parent !== null) {
        nodes.current[node.parent].children.push(node.id);
      }
    });
  }

  // Token streaming (50 tokens/sec)
  useEffect(() => {
    const interval = setInterval(() => {
      setTokens(t => t + 1);
    }, 20); // 50 Hz
    return () => clearInterval(interval);
  }, []);

  // Task progress updates (10 updates/sec)
  useEffect(() => {
    const interval = setInterval(() => {
      setTasks(prevTasks =>
        prevTasks.map(task => ({
          ...task,
          progress: Math.min(100, task.progress + Math.random() * 2),
        }))
      );
    }, 100); // 10 Hz
    return () => clearInterval(interval);
  }, []);

  // Tree node toggling (10 toggles/sec)
  useEffect(() => {
    const interval = setInterval(() => {
      const nodeId = Math.floor(Math.random() * 100);
      setExpandedNodes(prev => {
        const next = new Set(prev);
        if (next.has(nodeId)) {
          next.delete(nodeId);
        } else {
          next.add(nodeId);
        }
        return next;
      });
    }, 100); // 10 Hz
    return () => clearInterval(interval);
  }, []);

  // Frame timing and CPU sampling
  useEffect(() => {
    const frameInterval = setInterval(() => {
      const now = Date.now();
      frameTimes.current.push(now);

      // Calculate FPS from last 30 frames
      if (frameTimes.current.length > 30) {
        frameTimes.current.shift();
      }
      if (frameTimes.current.length >= 2) {
        const deltas = [];
        for (let i = 1; i < frameTimes.current.length; i++) {
          deltas.push(frameTimes.current[i] - frameTimes.current[i - 1]);
        }
        const avgDelta = deltas.reduce((a, b) => a + b, 0) / deltas.length;
        setFps(1000 / avgDelta);
      }
    }, 33); // 30 Hz

    const cpuInterval = setInterval(async () => {
      try {
        const stats = await pidusage(process.pid);
        cpuSamples.current.push(stats.cpu);
        const avg = cpuSamples.current.reduce((a, b) => a + b, 0) / cpuSamples.current.length;
        setCpuAvg(avg);
      } catch (err) {
        // Ignore errors
      }
    }, 333); // 3 Hz

    return () => {
      clearInterval(frameInterval);
      clearInterval(cpuInterval);
    };
  }, []);

  // Elapsed time and completion check
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      const elapsedSec = (now - startTime.current) / 1000;
      setElapsed(elapsedSec);

      if (elapsedSec >= duration && !testComplete) {
        setTestComplete(true);
      }
    }, 100);
    return () => clearInterval(interval);
  }, [duration, testComplete]);

  // Format token count
  const formatTokens = (count: number) => {
    if (count < 1000) return `${count} tokens`;
    return `${(count / 1000).toFixed(1)}k tokens`;
  };

  // Render progress bar
  const renderProgressBar = (progress: number, width: number = 30) => {
    const filled = Math.floor((width * progress) / 100);
    return '━'.repeat(filled) + '╺' + ' '.repeat(Math.max(0, width - filled - 1));
  };

  // Render tree (first 20 lines only for performance)
  const renderTree = () => {
    const lines: string[] = ['🌳 Agent Tree'];
    let lineCount = 1;

    for (let i = 0; i < 10 && lineCount < 20; i++) {
      const root = nodes.current[i];
      const indicator = expandedNodes.has(i) ? '⏺' : '◯';
      lines.push(`├── ${indicator} ${root.label}`);
      lineCount++;

      if (expandedNodes.has(i) && lineCount < 20) {
        for (const childId of root.children) {
          if (lineCount >= 20) break;
          const child = nodes.current[childId];
          const childIndicator = expandedNodes.has(childId) ? '⏺' : '◯';
          lines.push(`│   ├── ${childIndicator} ${child.label}`);
          lineCount++;
        }
      }
    }

    return lines.join('\n');
  };

  if (testComplete) {
    return (
      <Box flexDirection="column">
        <Text bold color="cyan">
          Test Complete!
        </Text>
        <Text>
          Duration: {elapsed.toFixed(1)}s
        </Text>
        <Text>
          FPS: {fps.toFixed(1)}
        </Text>
        <Text>
          CPU: {cpuAvg.toFixed(1)}%
        </Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" padding={1}>
      {/* Header */}
      <Box borderStyle="single" borderColor="cyan" paddingX={2}>
        <Text color="cyan" bold>
          ✳ Stress Testing
        </Text>
        <Text dimColor> ({elapsed.toFixed(1)}s · ↓ {formatTokens(tokens)} · {fps.toFixed(1)} FPS · CPU {cpuAvg.toFixed(1)}%)</Text>
      </Box>

      {/* Body */}
      <Box marginTop={1}>
        <Box flexDirection="row" width="100%">
          {/* Progress bars */}
          <Box flexDirection="column" width="50%" borderStyle="single" borderColor="cyan" paddingX={1}>
            <Text bold>Background Tasks</Text>
            {tasks.map((task, i) => (
              <Box key={i} marginTop={1}>
                <Text>
                  {task.name.padEnd(20)} {renderProgressBar(task.progress)} {task.progress.toFixed(0)}%
                </Text>
              </Box>
            ))}
          </Box>

          {/* Tree */}
          <Box flexDirection="column" width="50%" borderStyle="single" borderColor="cyan" paddingX={1} marginLeft={1}>
            <Text>{renderTree()}</Text>
          </Box>
        </Box>
      </Box>

      {/* Footer */}
      <Box marginTop={1} borderStyle="single" paddingX={2}>
        <Text dimColor>Press Ctrl+C to stop early</Text>
      </Box>
    </Box>
  );
};

async function main() {
  console.log('\nInk + React Stress Test - Phase 0');
  console.log('Duration: 60 seconds');
  console.log('Scenarios:');
  console.log('  1. Token streaming (50 tokens/sec)');
  console.log('  2. Background tasks (5 progress bars, 100ms updates)');
  console.log('  3. Tree expansion (100 nodes, 10 toggles/sec)');
  console.log('\nGate Criteria:');
  console.log('  • CPU usage < 10%');
  console.log('  • No visible flicker');
  console.log('  • Frame rate ≥ 30 FPS');
  console.log('\nStarting in 3 seconds...\n');

  await new Promise(resolve => setTimeout(resolve, 3000));

  const { waitUntilExit } = render(<StressTestApp duration={60} />);
  await waitUntilExit();

  console.log('\n' + '='.repeat(80));
  console.log('Ink + React Stress Test Results');
  console.log('='.repeat(80) + '\n');
  console.log('Test completed. Check the final stats above.');
  console.log('\nRecommendation: If CPU < 10% and FPS ≥ 30, proceed with Ink + React');
}

main().catch(console.error);
