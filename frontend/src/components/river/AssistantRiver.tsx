import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { TaskTreeNode } from '@/api/taskService';

interface Props {
  tree: TaskTreeNode;
  selectedNode: TaskTreeNode | null;
  onSelectNode: (node: TaskTreeNode) => void;
}

const STATUS_COLORS: Record<string, string> = {
  running: '#22c55e',
  waiting: '#38bdf8',
  done: '#7c3aed',
  error: '#ef4444',
  completed: '#0ea5e9',
};

const getStatusColor = (status: string) => STATUS_COLORS[status] || '#7c6af7';

const flattenTaskTree = (root: TaskTreeNode): TaskTreeNode[] => {
  const nodes: TaskTreeNode[] = [];
  const walk = (node: TaskTreeNode) => {
    if (node.task_id !== root.task_id) {
      nodes.push(node);
    }
    node.children?.forEach(walk);
  };
  walk(root);
  return nodes;
};

const AssistantRiver: React.FC<Props> = ({ tree, selectedNode, onSelectNode }) => {
  const branches = useMemo(() => flattenTaskTree(tree), [tree]);
  const width = Math.max(520, 120 + branches.length * 140);
  const height = 180;

  return (
    <div style={{ margin: '0 0 16px', padding: '18px', borderRadius: 18, background: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#a5b4fc' }}>
            Forking River Visualization
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
            Assistant thread progress
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)' }}>Root:</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#c4b5fd' }}>{tree.task_name || tree.task_id}</span>
        </div>
      </div>

      <div style={{ position: 'relative', width: '100%', overflowX: 'auto' }}>
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
          <defs>
            <linearGradient id="riverFlow" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="45%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#7c3aed" />
            </linearGradient>
          </defs>
          <motion.path
            d={`M20,${height / 2} C${width / 4},${height / 2 - 24} ${width / 2},${height / 2 + 24} ${width - 20},${height / 2}`}
            fill="none"
            stroke="url(#riverFlow)"
            strokeWidth="24"
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.4, ease: 'easeOut' }}
          />
          <motion.circle
            cx={20}
            cy={height / 2}
            r={10}
            fill="#38bdf8"
            animate={{ x: [0, 4, -2, 0], y: [0, -2, 2, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />
          {branches.map((branch, index) => {
            const x = 120 + index * 120;
            const y = height / 2 + ((index % 2 === 0) ? -38 : 38);
            const color = getStatusColor(branch.status);
            return (
              <g key={branch.task_id} style={{ cursor: 'pointer' }} onClick={() => onSelectNode(branch)}>
                <motion.path
                  d={`M20,${height / 2} C${x / 2},${height / 2} ${x / 2},${y} ${x},${y}`}
                  fill="none"
                  stroke={color}
                  strokeWidth="2"
                  strokeDasharray="8 8"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.9, ease: 'easeOut' }}
                />
                <motion.circle
                  cx={x}
                  cy={y}
                  r={12}
                  fill={color}
                  stroke="#ffffff33"
                  strokeWidth={2}
                  whileHover={{ scale: 1.1 }}
                  animate={{ opacity: [0.7, 1, 0.8] }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                />
                <text x={x + 18} y={y + 4} fontSize="11" fill="#e2e8f0">
                  {branch.task_name || branch.task_id}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {selectedNode ? (
        <div style={{ marginTop: 16, padding: 16, borderRadius: 14, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0' }}>{selectedNode.task_name || selectedNode.task_id}</div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)' }}>{selectedNode.status.toUpperCase()}</div>
            </div>
            <div style={{ minWidth: 80, textAlign: 'right', fontSize: 12, color: 'rgba(255,255,255,0.75)' }}>
              {selectedNode.progress}%
            </div>
          </div>
          <div style={{ height: 8, width: '100%', background: 'rgba(255,255,255,0.08)', borderRadius: 999 }}> 
            <div style={{ width: `${Math.min(100, selectedNode.progress)}%`, height: 8, borderRadius: 999, background: getStatusColor(selectedNode.status) }} />
          </div>
          <div style={{ marginTop: 12, fontSize: 13, color: 'rgba(255,255,255,0.8)', lineHeight: 1.6 }}>
            {selectedNode.metadata?.result_summary ? (
              <>{String(selectedNode.metadata.result_summary)}</>
            ) : (
              <>{selectedNode.metadata?.instructions || 'No additional metadata available.'}</>
            )}
          </div>
        </div>
      ) : (
        <div style={{ marginTop: 16, fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
          Tap a branch to inspect task details, progress, and summary.
        </div>
      )}
    </div>
  );
};

export default AssistantRiver;
