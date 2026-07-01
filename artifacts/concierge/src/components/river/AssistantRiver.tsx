import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { TaskTreeNode } from '@/api/taskService';
import { stepDisplayName } from '@/utils/workflowStatus';
import { truncateText } from '@/components/tasks/taskDisplayUtils';

interface Props {
  tree: TaskTreeNode;
  selectedNode: TaskTreeNode | null;
  onSelectNode: (node: TaskTreeNode) => void;
  displayTitle?: string;
}

const STATUS_COLORS: Record<string, string> = {
  running: '#22c55e',
  waiting: '#38bdf8',
  done: '#7c3aed',
  error: '#ef4444',
  completed: '#0ea5e9',
};

const getStatusColor = (status: string) => STATUS_COLORS[status] || '#2563EB';

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

const AssistantRiver: React.FC<Props> = ({ tree, selectedNode, onSelectNode, displayTitle }) => {
  const branches = useMemo(() => flattenTaskTree(tree), [tree]);
  const width = Math.max(520, 120 + branches.length * 140);
  const height = 400;
  const completedCount = branches.filter((b) => ['done', 'completed', 'success'].includes((b.status || '').toLowerCase())).length;

  return (
    <div style={{ margin: '0 0 16px', padding: '18px', borderRadius: 18, background: '#FFFFFF', border: '1px solid #DBEAFE', boxShadow: '0 4px 16px rgba(37,99,235,0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#94A3B8' }}>
            Workflow steps
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#0F172A', marginTop: 4 }}>
            {branches.length} step{branches.length !== 1 ? 's' : ''}
            {branches.length > 0 ? ` · ${completedCount} complete` : ''}
          </div>
        </div>
        {displayTitle ? (
          <div style={{ fontSize: 12, color: '#64748B', maxWidth: 280, textAlign: 'right', lineHeight: 1.4 }}>
            {truncateText(displayTitle, 72)}
          </div>
        ) : null}
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
                  stroke="rgba(37,99,235,0.2)"
                  strokeWidth={2}
                  whileHover={{ scale: 1.1 }}
                  animate={{ opacity: [0.7, 1, 0.8] }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                />
                <text x={x + 18} y={y + 4} fontSize="11" fill="#334155">
                  {stepDisplayName(branch)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {selectedNode ? (
        <div style={{ marginTop: 16, padding: 16, borderRadius: 14, background: '#EFF6FF', border: '1px solid #BFDBFE' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>{stepDisplayName(selectedNode)}</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>{(selectedNode.status || selectedNode.state || 'unknown').toUpperCase()}</div>
            </div>
            <div style={{ minWidth: 80, textAlign: 'right', fontSize: 12, color: '#475569' }}>
              {typeof selectedNode.progress === 'number' ? `${selectedNode.progress}%` : '—'}
            </div>
          </div>
          <div style={{ height: 8, width: '100%', background: '#DBEAFE', borderRadius: 999 }}>
            <div
              style={{
                width: `${Math.min(100, Math.max(0, selectedNode.progress ?? 0))}%`,
                height: 8,
                borderRadius: 999,
                background: getStatusColor(selectedNode.status || selectedNode.state || ''),
              }}
            />
          </div>
          <div style={{ marginTop: 12, fontSize: 13, color: '#334155', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {selectedNode.metadata?.result_summary ? (
              <>{truncateText(String(selectedNode.metadata.result_summary), 320)}</>
            ) : selectedNode.metadata?.instructions ? (
              <>{truncateText(String(selectedNode.metadata.instructions), 320)}</>
            ) : (
              <>No step summary yet.</>
            )}
          </div>
        </div>
      ) : (
        <div style={{ marginTop: 16, fontSize: 12, color: '#94A3B8' }}>
          Select a step to view its status and summary.
        </div>
      )}
    </div>
  );
};

export default AssistantRiver;
