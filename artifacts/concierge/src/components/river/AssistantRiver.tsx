import React from 'react';
import type { TaskTreeNode } from '@/api/taskService';
import WorkflowTimeline from '@/components/river/WorkflowTimeline';

interface Props {
  tree: TaskTreeNode;
  selectedNode: TaskTreeNode | null;
  onSelectNode: (node: TaskTreeNode | null) => void;
  displayTitle?: string;
}

/** Infographic project timeline — accordion step badges with position indicator. */
const AssistantRiver: React.FC<Props> = (props) => <WorkflowTimeline {...props} />;

export default AssistantRiver;