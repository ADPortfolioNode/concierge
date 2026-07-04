import type { TaskTreeNode } from '@/api/taskService';

export interface TreeLayoutNode {
  node: TaskTreeNode;
  depth: number;
  x: number;
  y: number;
}

export interface TreeLayoutEdge {
  parentId: string;
  childId: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface HorizontalTreeLayout {
  nodes: TreeLayoutNode[];
  edges: TreeLayoutEdge[];
  width: number;
  height: number;
}

const COL_WIDTH = 156;
const ROW_HEIGHT = 76;
const PAD_X = 28;
const PAD_Y = 24;
const NODE_W = 132;
const NODE_H = 56;

interface SubtreeLayout {
  nodes: TreeLayoutNode[];
  height: number;
}

function layoutSubtree(node: TaskTreeNode, depth: number): SubtreeLayout {
  const children = node.children ?? [];

  if (children.length === 0) {
    return {
      nodes: [{
        node,
        depth,
        x: PAD_X + depth * COL_WIDTH,
        y: PAD_Y,
      }],
      height: 1,
    };
  }

  const nodes: TreeLayoutNode[] = [];
  let rowOffset = 0;
  const childCenters: number[] = [];

  for (const child of children) {
    const sub = layoutSubtree(child, depth + 1);
    for (const n of sub.nodes) {
      nodes.push({ ...n, y: PAD_Y + (n.y - PAD_Y) + rowOffset * ROW_HEIGHT });
    }
    childCenters.push(rowOffset + sub.height / 2);
    rowOffset += sub.height;
  }

  const centerRow = (childCenters[0] + childCenters[childCenters.length - 1]) / 2;
  const parentNode: TreeLayoutNode = {
    node,
    depth,
    x: PAD_X + depth * COL_WIDTH,
    y: PAD_Y + centerRow * ROW_HEIGHT,
  };

  return {
    nodes: [parentNode, ...nodes],
    height: rowOffset,
  };
}

function buildEdges(nodes: TreeLayoutNode[]): TreeLayoutEdge[] {
  const byId = new Map(nodes.map((n) => [n.node.task_id, n]));
  const edges: TreeLayoutEdge[] = [];

  for (const item of nodes) {
    for (const child of item.node.children ?? []) {
      const target = byId.get(child.task_id);
      if (!target) continue;
      edges.push({
        parentId: item.node.task_id,
        childId: child.task_id,
        x1: item.x + NODE_W,
        y1: item.y + NODE_H / 2,
        x2: target.x,
        y2: target.y + NODE_H / 2,
      });
    }
  }

  return edges;
}

/** Lay out a task tree left-to-right: root on the left, branches grow rightward. */
export function layoutHorizontalTree(root: TaskTreeNode): HorizontalTreeLayout {
  const { nodes, height } = layoutSubtree(root, 0);
  const edges = buildEdges(nodes);
  const maxX = Math.max(...nodes.map((n) => n.x), PAD_X) + NODE_W + PAD_X;
  const maxY = Math.max(...nodes.map((n) => n.y), PAD_Y) + Math.max(height, 1) * ROW_HEIGHT;
  return {
    nodes,
    edges,
    width: maxX,
    height: maxY + PAD_Y,
  };
}

export const TREE_NODE_SIZE = { width: NODE_W, height: NODE_H };