import React, { useMemo } from 'react';
import type { TaskTreeNode } from '@/api/taskService';
import RichTextWithImages from '@/components/media/RichTextWithImages';
import { truncateText } from '@/components/tasks/taskDisplayUtils';
import {
  layoutHorizontalTree,
  TREE_NODE_SIZE,
} from '@/components/tasks/horizontalTreeLayout';
import {
  currentStepIndex,
  flattenWorkflowSteps,
  PHASE_COLORS,
  stepPhase,
  type TimelineStep,
} from '@/components/tasks/workflowTimelineUtils';
import { extractImageUrls } from '@/utils/imageContent';
import { stepDisplayName } from '@/utils/workflowStatus';

interface Props {
  tree: TaskTreeNode;
  selectedNode: TaskTreeNode | null;
  onSelectNode: (node: TaskTreeNode | null) => void;
  displayTitle?: string;
}

const StepDetailPanel: React.FC<{ step: TimelineStep }> = ({ step }) => {
  const meta = step.node.metadata as { result_summary?: string; instructions?: string } | undefined;
  const body = meta?.result_summary || meta?.instructions;
  return (
    <div className="workflow-timeline__detail">
      <div className="workflow-timeline__detail-head">
        <div>
          <div className="workflow-timeline__detail-title">{step.name}</div>
          <div className="workflow-timeline__detail-status">{step.status.toUpperCase()}</div>
        </div>
        <div className="workflow-timeline__detail-pct">{step.progress}%</div>
      </div>
      <div className="workflow-timeline__detail-bar">
        <div
          style={{
            width: `${Math.min(100, Math.max(0, step.progress))}%`,
            background: PHASE_COLORS[step.phase],
          }}
        />
      </div>
      <div className="workflow-timeline__detail-copy">
        {body ? (
          (() => {
            const text = String(body);
            const imageUrls = extractImageUrls(text);
            const textOnly = imageUrls.reduce((acc, url) => acc.split(url).join(''), text).replace(/\n{2,}/g, '\n').trim();
            const preview = truncateText(textOnly || text, 420);
            const imageBlock = imageUrls.length > 0 ? `\n\n${imageUrls.join('\n')}` : '';
            return <RichTextWithImages content={`${preview}${imageBlock}`} />;
          })()
        ) : (
          'No summary for this step yet.'
        )}
      </div>
    </div>
  );
};

function edgePath(x1: number, y1: number, x2: number, y2: number) {
  const midX = x1 + (x2 - x1) * 0.45;
  return `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`;
}

const WorkflowTimeline: React.FC<Props> = ({ tree, selectedNode, onSelectNode, displayTitle }) => {
  const steps = useMemo(() => flattenWorkflowSteps(tree), [tree]);
  const layout = useMemo(() => layoutHorizontalTree(tree), [tree]);
  const currentIdx = useMemo(() => currentStepIndex(steps), [steps]);
  const doneCount = steps.filter((s) => s.phase === 'done').length;
  const selectedId = selectedNode?.task_id ?? null;

  const stepById = useMemo(() => {
    const map = new Map<string, TimelineStep>();
    for (const step of steps) map.set(step.node.task_id, step);
    return map;
  }, [steps]);

  const toggleNode = (node: TaskTreeNode) => {
    if (selectedId === node.task_id) onSelectNode(null);
    else onSelectNode(node);
  };

  if (steps.length === 0 && (tree.children?.length ?? 0) === 0) {
    return (
      <div className="workflow-timeline workflow-timeline--empty">
        <p>No workflow steps yet.</p>
      </div>
    );
  }

  const selectedStep =
    selectedNode && stepById.get(selectedNode.task_id)
      ? stepById.get(selectedNode.task_id)!
      : selectedNode
      ? {
          node: selectedNode,
          index: 0,
          name: stepDisplayName(selectedNode),
          status: selectedNode.status || selectedNode.state || 'pending',
          phase: stepPhase(selectedNode.status || selectedNode.state, selectedNode.progress),
          progress: selectedNode.progress ?? 0,
        }
      : null;

  return (
    <section className="workflow-timeline" aria-label="Project workflow timeline">
      <div className="workflow-timeline__header">
        <div className="workflow-timeline__header-main">
          <span className="workflow-timeline__eyebrow">Workflow tree</span>
          <span className="workflow-timeline__stat">
            {doneCount}/{Math.max(steps.length, layout.nodes.length - 1)} complete
          </span>
        </div>
        {displayTitle ? (
          <span className="workflow-timeline__goal" title={displayTitle}>
            {truncateText(displayTitle, 64)}
          </span>
        ) : null}
      </div>

      <div className="workflow-timeline__tree-scroll" data-testid="workflow-tree">
        <div
          className="workflow-timeline__tree-canvas"
          style={{ width: layout.width, height: layout.height, minWidth: '100%' }}
        >
          <svg
            className="workflow-timeline__tree-svg"
            width={layout.width}
            height={layout.height}
            aria-hidden
          >
            {layout.edges.map((edge) => (
              <path
                key={`${edge.parentId}-${edge.childId}`}
                d={edgePath(edge.x1, edge.y1, edge.x2, edge.y2)}
                className="workflow-timeline__tree-edge"
              />
            ))}
          </svg>

          {layout.nodes.map((item, idx) => {
            const step = stepById.get(item.node.task_id);
            const status = item.node.status || item.node.state || 'pending';
            const progress = item.node.progress ?? 0;
            const phase = step?.phase ?? stepPhase(status, progress);
            const isRoot = item.depth === 0 && idx === 0;
            const isOpen = selectedId === item.node.task_id;
            const isCurrent = step ? step.index === currentIdx && phase !== 'done' : false;
            const label = isRoot ? 'Start' : step?.name ?? stepDisplayName(item.node);

            return (
              <button
                key={item.node.task_id}
                type="button"
                className={[
                  'workflow-timeline__tree-node',
                  `workflow-timeline__tree-node--${phase}`,
                  isOpen ? 'workflow-timeline__tree-node--open' : '',
                  isCurrent ? 'workflow-timeline__tree-node--current' : '',
                  isRoot ? 'workflow-timeline__tree-node--root' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                style={{
                  left: item.x,
                  top: item.y,
                  width: TREE_NODE_SIZE.width,
                  height: TREE_NODE_SIZE.height,
                  '--step-color': PHASE_COLORS[phase],
                } as React.CSSProperties}
                onClick={() => toggleNode(item.node)}
                title={label}
              >
                <span className="workflow-timeline__tree-node-label">{truncateText(label, 28)}</span>
                <span className="workflow-timeline__tree-node-meta">
                  {isRoot ? 'Root' : `${progress}%`}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {selectedStep ? (
        <StepDetailPanel step={selectedStep} />
      ) : (
        <p className="workflow-timeline__hint">Select a node in the tree to view step details.</p>
      )}
    </section>
  );
};

export default WorkflowTimeline;