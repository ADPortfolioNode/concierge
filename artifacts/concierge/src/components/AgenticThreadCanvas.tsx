import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchTaskTree, TaskTreeNode } from '@/api/taskService';
import { makeApiUrl } from '@/config/activeServer';
import { useAppStore } from '@/state/appStore';

type VisualNodeType = 'reasoning' | 'tool_call' | 'observation' | 'rag_retrieval' | 'thread_root';
type VisualEdgeType = 'dependency' | 'sequence' | 'tool_flow';

interface VisualNode {
  id: string;
  type: VisualNodeType;
  label: string;
  status: string;
  x: number;
  y: number;
  metadata: Record<string, unknown>;
}

interface VisualEdge {
  fromId: string;
  toId: string;
  type: VisualEdgeType;
}

interface RetrievalDocument {
  id?: string;
  title?: string;
  source?: string;
  excerpt?: string;
  score?: number;
  url?: string;
}

interface TimelineEventPayload {
  type?: string;
  thread_id?: string;
  threadId?: string;
  task_id?: string;
  task_name?: string;
  status?: string;
  progress?: number;
  summary?: string;
  payload?: unknown;
}

interface StreamDeltaNodePayload {
  id: string;
  type?: VisualNodeType;
  label?: string;
  status?: string;
  x?: number;
  y?: number;
  metadata?: Record<string, unknown>;
}

interface NodeMemory {
  id: string;
  summary: string;
  score?: number;
  metadata?: Record<string, unknown>;
}

const STATUS_COLOR_MAP: Record<string, string> = {
  error: '#ef4444',
  failed: '#ef4444',
  cancelled: '#ef4444',
  done: '#22c55e',
  completed: '#22c55e',
  success: '#22c55e',
  running: '#fbbf24',
  started: '#fbbf24',
  thinking: '#fbbf24',
  queued: '#818cf8',
  waiting: '#818cf8',
  pending: '#818cf8',
  tool_call: '#38bdf8',
};

const ANIMATED_STATUSES = new Set(['running', 'thinking', 'started']);

const getStatusColor = (status: string): string => {
  const normalized = (status || '').toLowerCase();
  return STATUS_COLOR_MAP[normalized] || '#8b5cf6';
};

const toVisualType = (node: TaskTreeNode): VisualNodeType => {
  const name = (node.task_name || '').toLowerCase();
  if (name.includes('search') || name.includes('retrieve') || name.includes('rag')) {
    return 'rag_retrieval';
  }
  if (node.metadata?.agent_type || name.includes('tool') || node.metadata?.tool_name) {
    return 'tool_call';
  }
  if (name.includes('observe') || name.includes('read') || name.includes('scan')) {
    return 'observation';
  }
  return node.task_id === node.parent_id ? 'thread_root' : 'reasoning';
};

// ─── Hierarchical layout (Reingold-Tilford style, two-pass) ──────────────────
//
// x = X_ORIGIN + depth * X_STEP  (horizontal axis → depth/column)
// y = centred over children      (vertical axis → sibling distribution)
//
// MIN_SIBLING_GAP is the minimum center-to-centre vertical distance between
// siblings.  Nodes are 56 px tall (NODE_HALF_H * 2), so 140 px gives an 84 px
// edge-to-edge clearance — no overlap is possible.

const MIN_SIBLING_GAP = 140;
const X_STEP = 320;
const X_ORIGIN = 200;
const Y_ORIGIN = 120;

interface LayoutNode {
  taskNode: TaskTreeNode;
  subtreeHeight: number;
  x: number;
  y: number;
}

// Heights are memoised in a Map keyed by task_id so each subtree is walked
// exactly once — O(n) total rather than O(n²) with repeated recursion.
function buildSubtreeHeightMap(node: TaskTreeNode, memo: Map<string, number>): number {
  const cached = memo.get(node.task_id);
  if (cached !== undefined) return cached;
  const children = node.children || [];
  const height =
    children.length === 0
      ? MIN_SIBLING_GAP
      : Math.max(
          MIN_SIBLING_GAP,
          children.reduce((sum, child) => sum + buildSubtreeHeightMap(child, memo), 0),
        );
  memo.set(node.task_id, height);
  return height;
}

function assignPositions(
  node: TaskTreeNode,
  depth: number,
  centerY: number,
  result: LayoutNode[],
  heightMap: Map<string, number>,
): void {
  const x = X_ORIGIN + depth * X_STEP;
  result.push({
    taskNode: node,
    subtreeHeight: heightMap.get(node.task_id) ?? MIN_SIBLING_GAP,
    x,
    y: centerY,
  });

  const children = node.children || [];
  if (children.length === 0) return;

  const childHeights = children.map((c) => heightMap.get(c.task_id) ?? MIN_SIBLING_GAP);
  const totalHeight = childHeights.reduce((a, b) => a + b, 0);
  let cursor = centerY - totalHeight / 2;
  children.forEach((child, i) => {
    const halfH = childHeights[i] / 2;
    assignPositions(child, depth + 1, cursor + halfH, result, heightMap);
    cursor += childHeights[i];
  });
}

const buildGraphFromTree = (tree: TaskTreeNode): { nodes: VisualNode[]; edges: VisualEdge[] } => {
  const heightMap = new Map<string, number>();
  buildSubtreeHeightMap(tree, heightMap);
  const layoutNodes: LayoutNode[] = [];
  assignPositions(tree, 0, Y_ORIGIN, layoutNodes, heightMap);

  const nodes: VisualNode[] = layoutNodes.map(({ taskNode, x, y }) => ({
    id: taskNode.task_id,
    type: toVisualType(taskNode),
    label: taskNode.task_name || taskNode.task_id,
    status: taskNode.status || 'running',
    x,
    y,
    metadata: {
      progress: taskNode.progress,
      state: taskNode.state,
      ...taskNode.metadata,
    },
  }));

  const edges: VisualEdge[] = [];
  const walkEdges = (node: TaskTreeNode) => {
    (node.children || []).forEach((child) => {
      edges.push({ fromId: node.task_id, toId: child.task_id, type: 'dependency' });
      walkEdges(child);
    });
  };
  walkEdges(tree);

  return { nodes, edges };
};

// ─── Bezier path length cache ─────────────────────────────────────────────────

function computeBezierPoint(t: number, p0: number, p1: number, p2: number, p3: number) {
  return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3;
}

function approximateBezierLength(
  x0: number, y0: number,
  cp1x: number, cp1y: number,
  cp2x: number, cp2y: number,
  x1: number, y1: number,
  steps = 100,
): number {
  let length = 0;
  let prevX = x0;
  let prevY = y0;
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    const cx = computeBezierPoint(t, x0, cp1x, cp2x, x1);
    const cy = computeBezierPoint(t, y0, cp1y, cp2y, y1);
    length += Math.hypot(cx - prevX, cy - prevY);
    prevX = cx;
    prevY = cy;
  }
  return length;
}

// ─── Streaming helpers ────────────────────────────────────────────────────────

const getWebSocketUrl = () => {
  const timelineUrl = makeApiUrl('/api/v1/concierge/timeline/ws');
  if (timelineUrl.startsWith('http')) {
    return timelineUrl.replace(/^http/, 'ws');
  }
  if (typeof window !== 'undefined' && window.location) {
    const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${scheme}//${window.location.host}${timelineUrl}`;
  }
  return timelineUrl;
};

const buildTimelineStreamUrl = (threadId?: string) => {
  const url = new URL(makeApiUrl('/api/v1/concierge/timeline/stream'), window.location.origin);
  if (threadId) url.searchParams.set('thread_id', threadId);
  return url.toString();
};

const buildTimelineWebSocketUrl = (threadId?: string) => {
  const base = getWebSocketUrl();
  const url = new URL(base, window.location.origin);
  if (threadId) url.searchParams.set('thread_id', threadId);
  return url.toString();
};

// ─── NodeDetailPanel (memoised side panel) ────────────────────────────────────

interface NodeDetailPanelProps {
  selectedNode: VisualNode | null;
  nodeMemories: NodeMemory[];
  memoryStatus: 'idle' | 'loading' | 'ready' | 'error';
  taskThreadId: string | null;
  onKillTask: (node: VisualNode) => void;
  onOpenThreadStatus: () => void;
  onDeselect: () => void;
}

const NodeDetailPanel = React.memo(function NodeDetailPanel({
  selectedNode,
  nodeMemories,
  memoryStatus,
  taskThreadId,
  onKillTask,
  onOpenThreadStatus,
  onDeselect,
}: NodeDetailPanelProps) {
  if (!selectedNode) {
    return (
      <div className="agentic-thread-panel-empty">
        Select any node to inspect execution metadata, retrieved documents, and tool context.
      </div>
    );
  }

  const documents: RetrievalDocument[] =
    (selectedNode.metadata?.retrieved_documents as RetrievalDocument[] | undefined) ||
    (selectedNode.metadata?.documents as RetrievalDocument[] | undefined) ||
    (selectedNode.metadata?.matches as RetrievalDocument[] | undefined) ||
    [];

  return (
    <div className="agentic-thread-sidepanel__content">
      <h3>{selectedNode.label}</h3>
      <div className="agentic-thread-node-meta">
        <span>Status: {selectedNode.status}</span>
        <span>Type: {selectedNode.type}</span>
        <span>Progress: {String(selectedNode.metadata?.progress ?? 'N/A')}</span>
        {typeof selectedNode.metadata?.confidence === 'number' ? (
          <span>Confidence: {(selectedNode.metadata.confidence * 100).toFixed(0)}%</span>
        ) : null}
      </div>
      {selectedNode.metadata?.summary ? (
        <section>
          <h4>Summary</h4>
          <p>{String(selectedNode.metadata.summary)}</p>
        </section>
      ) : null}
      <section>
        <h4>Chroma memories</h4>
        {memoryStatus === 'loading' ? <p>Retrieving related memory context...</p> : null}
        {memoryStatus === 'error' ? <p>Could not load related memories right now.</p> : null}
        {memoryStatus === 'ready' && nodeMemories.length === 0 ? <p>No related memories found yet.</p> : null}
        {memoryStatus === 'ready' && nodeMemories.length > 0 ? (
          <div className="agentic-thread-doc-list">
            {nodeMemories.map((memory) => (
              <article key={memory.id} className="agentic-thread-doc-card">
                <strong>{memory.metadata?.task_name ? String(memory.metadata.task_name) : memory.id}</strong>
                <p>{memory.summary}</p>
                {typeof memory.score === 'number' ? <small>Relevance {(memory.score * 100).toFixed(0)}%</small> : null}
              </article>
            ))}
          </div>
        ) : null}
      </section>
      {documents.length > 0 ? (
        <section>
          <h4>Retrievals</h4>
          <div className="agentic-thread-doc-list">
            {documents.slice(0, 6).map((doc, idx) => (
              <article key={`${doc.id || idx}`} className="agentic-thread-doc-card">
                {doc.title ? <strong>{doc.title}</strong> : null}
                {doc.source ? <div className="agentic-thread-doc-source">{doc.source}</div> : null}
                {doc.excerpt ? <p>{doc.excerpt}</p> : null}
                {typeof doc.score === 'number' ? <small>Score {(doc.score * 100).toFixed(0)}%</small> : null}
                {doc.url ? <a href={doc.url} target="_blank" rel="noreferrer">Open source</a> : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
      {selectedNode.metadata?.agent_type || selectedNode.metadata?.tool_name ? (
        <section>
          <h4>Tool / agent context</h4>
          <p>{String(selectedNode.metadata?.agent_type || selectedNode.metadata?.tool_name || '')}</p>
          <pre>{JSON.stringify(selectedNode.metadata, null, 2)}</pre>
        </section>
      ) : null}
      <div className="agentic-thread-sidepanel__actions">
        <button className="agentic-thread-action" onClick={() => onKillTask(selectedNode)}>
          Kill Task
        </button>
        <button className="agentic-thread-action" onClick={onOpenThreadStatus}>
          Open thread status
        </button>
        <button className="agentic-thread-action agentic-thread-action--secondary" onClick={onDeselect}>
          Deselect node
        </button>
      </div>
    </div>
  );
});

// ─── Main component ───────────────────────────────────────────────────────────

const SPATIAL_CELL_SIZE = 200;
const NODE_HALF_W = 96;
const NODE_HALF_H = 28;

const AgenticThreadCanvas: React.FC = () => {
  const taskThreadId = useAppStore((s) => s.taskThreadId);
  const [nodes, setNodes] = useState<VisualNode[]>([]);
  const [edges, setEdges] = useState<VisualEdge[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('Loading thread graph…');
  const [isMobileFallback, setIsMobileFallback] = useState(false);
  const [nodeMemories, setNodeMemories] = useState<NodeMemory[]>([]);
  const [memoryStatus, setMemoryStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const rafId = useRef<number | null>(null);
  const particleFrame = useRef(0);
  const clickStartPointer = useRef<{ x: number; y: number } | null>(null);

  const [viewState, setViewState] = useState({ x: 0, y: 0, scale: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const lastPointer = useRef<{ x: number; y: number } | null>(null);

  // ── Dirty flag for idle-aware render loop ──
  const needsRedraw = useRef(true);

  // ── Bezier path length cache ──
  const edgeLengthCache = useRef<Map<string, number>>(new Map());

  // ── RAF-based update batching for streaming events ──
  const pendingUpdates = useRef<TimelineEventPayload[]>([]);
  const flushRafId = useRef<number | null>(null);

  // ── Pointer-move throttle ──
  const hoverRafPending = useRef<number | null>(null);

  const selectedNode = useMemo(
    () => nodes.find((node) => node.id === selectedNodeId) || null,
    [nodes, selectedNodeId]
  );

  const nodeMap = useMemo(
    () => new Map(nodes.map((node) => [node.id, node])),
    [nodes]
  );

  const selectedAdjacency = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const connected = new Set<string>([selectedNodeId]);
    for (const edge of edges) {
      if (edge.fromId === selectedNodeId) connected.add(edge.toId);
      if (edge.toId === selectedNodeId) connected.add(edge.fromId);
    }
    return connected;
  }, [edges, selectedNodeId]);

  // ── Spatial grid for O(1) hit testing ──
  const spatialGrid = useMemo(() => {
    const grid = new Map<string, string[]>();
    for (const node of nodes) {
      const x0 = Math.floor((node.x - NODE_HALF_W) / SPATIAL_CELL_SIZE);
      const x1 = Math.floor((node.x + NODE_HALF_W) / SPATIAL_CELL_SIZE);
      const y0 = Math.floor((node.y - NODE_HALF_H) / SPATIAL_CELL_SIZE);
      const y1 = Math.floor((node.y + NODE_HALF_H) / SPATIAL_CELL_SIZE);
      for (let cx = x0; cx <= x1; cx++) {
        for (let cy = y0; cy <= y1; cy++) {
          const key = `${cx},${cy}`;
          if (!grid.has(key)) grid.set(key, []);
          grid.get(key)!.push(node.id);
        }
      }
    }
    return grid;
  }, [nodes]);

  // Mark dirty whenever visual state changes
  useEffect(() => { needsRedraw.current = true; }, [nodes, edges, viewState, hoveredNodeId, selectedNodeId, selectedAdjacency]);

  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;
    const dpr = window.devicePixelRatio || 1;
    const width = parent.clientWidth;
    const height = parent.clientHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext('2d');
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    needsRedraw.current = true;
  }, []);

  const drawScene = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = '#070b16';
    ctx.fillRect(0, 0, width, height);

    ctx.save();
    ctx.translate(viewState.x, viewState.y);
    ctx.scale(viewState.scale, viewState.scale);

    const visibleX0 = -viewState.x / viewState.scale - 240;
    const visibleY0 = -viewState.y / viewState.scale - 240;
    const visibleX1 = visibleX0 + width / viewState.scale + 480;
    const visibleY1 = visibleY0 + height / viewState.scale + 480;
    const pulse = (Math.sin(particleFrame.current / 10) + 1) * 0.5;

    edges.forEach((edge, index) => {
      const from = nodeMap.get(edge.fromId);
      const to = nodeMap.get(edge.toId);
      if (!from || !to) return;
      if (from.x < visibleX0 && to.x < visibleX0) return;
      if (from.x > visibleX1 && to.x > visibleX1) return;
      if (from.y < visibleY0 && to.y < visibleY0) return;
      if (from.y > visibleY1 && to.y > visibleY1) return;

      const cp1x = from.x + Math.max(160, Math.abs(to.x - from.x) * 0.32);
      const cp1y = from.y;
      const cp2x = to.x - Math.max(160, Math.abs(to.x - from.x) * 0.32);
      const cp2y = to.y;

      const edgeFocused =
        !selectedNodeId || edge.fromId === selectedNodeId || edge.toId === selectedNodeId;

      // Base edge
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.18)';
      ctx.lineWidth = 1.6;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, to.x, to.y);
      ctx.stroke();

      // Progress bar via lineDash (O(1) per frame after cache warm-up)
      const fromProgress = (Number(from.metadata?.progress ?? 0)) / 100;
      if (fromProgress > 0) {
        const cacheKey = `${from.x},${from.y},${cp1x},${cp1y},${cp2x},${cp2y},${to.x},${to.y}`;
        let totalLen = edgeLengthCache.current.get(cacheKey);
        if (totalLen === undefined) {
          totalLen = approximateBezierLength(from.x, from.y, cp1x, cp1y, cp2x, cp2y, to.x, to.y);
          edgeLengthCache.current.set(cacheKey, totalLen);
        }
        const filledLen = totalLen * fromProgress;
        const remainder = totalLen - filledLen;

        ctx.strokeStyle = edgeFocused ? 'rgba(96, 165, 250, 0.6)' : 'rgba(96, 165, 250, 0.4)';
        ctx.lineWidth = 2.6;
        ctx.setLineDash([filledLen, remainder > 0 ? remainder : totalLen]);
        ctx.lineDashOffset = 0;
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, to.x, to.y);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Particle dot along edge
      const particlePosition = ((particleFrame.current + index * 12) % 180) / 180;
      const px = computeBezierPoint(particlePosition, from.x, cp1x, cp2x, to.x);
      const py = computeBezierPoint(particlePosition, from.y, cp1y, cp2y, to.y);
      ctx.fillStyle = edgeFocused ? 'rgba(255,255,255,0.95)' : 'rgba(148,163,184,0.45)';
      ctx.beginPath();
      ctx.arc(px, py, 3.2, 0, Math.PI * 2);
      ctx.fill();
    });

    nodes.forEach((node) => {
      if (node.x < visibleX0 || node.x > visibleX1 || node.y < visibleY0 || node.y > visibleY1) return;
      const isSelected = node.id === selectedNodeId;
      const isHovered = node.id === hoveredNodeId;
      const isConnected = selectedAdjacency.has(node.id);
      const nodeColor = getStatusColor(node.status);
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(node.x - 96, node.y - 28, 192, 56, 20);
      ctx.fillStyle = isSelected
        ? 'rgba(31, 41, 55, 0.98)'
        : isConnected
        ? 'rgba(15, 23, 42, 0.96)'
        : 'rgba(15, 23, 42, 0.86)';
      ctx.fill();
      ctx.strokeStyle = isSelected
        ? 'rgba(56, 189, 248, 0.92)'
        : isConnected
        ? 'rgba(56, 189, 248, 0.42)'
        : 'rgba(148, 163, 184, 0.18)';
      ctx.lineWidth = isHovered || isSelected ? 3 : 1.5;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(node.x - 66, node.y, 18, 0, Math.PI * 2);
      ctx.fillStyle = nodeColor;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.14)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      const normalizedStatus = node.status.toLowerCase();
      if (ANIMATED_STATUSES.has(normalizedStatus)) {
        ctx.beginPath();
        ctx.arc(node.x - 66, node.y, 22 + pulse * 4, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(251, 191, 36, ${0.24 + pulse * 0.3})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      ctx.fillStyle = '#e2e8f0';
      ctx.font = '600 12px Inter, system-ui, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      const text = node.label.length > 24 ? `${node.label.slice(0, 24)}…` : node.label;
      ctx.fillText(text, node.x - 44, node.y);
      ctx.restore();
    });

    ctx.restore();
  }, [edges, nodeMap, nodes, selectedAdjacency, selectedNodeId, hoveredNodeId, viewState]);

  useEffect(() => {
    resizeCanvas();
    const handleResize = () => {
      resizeCanvas();
      setIsMobileFallback(window.innerWidth < 720);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [resizeCanvas]);

  const drawSceneRef = useRef(drawScene);
  useEffect(() => {
    drawSceneRef.current = drawScene;
  }, [drawScene]);

  // ── Idle-aware render loop ─────────────────────────────────────────────────
  useEffect(() => {
    const loop = () => {
      const hasAnimating = nodes.some((n) => ANIMATED_STATUSES.has(n.status.toLowerCase()));

      if (hasAnimating) {
        particleFrame.current += 1;
        needsRedraw.current = true;
      }

      if (needsRedraw.current) {
        drawSceneRef.current();
        needsRedraw.current = false;
      }

      rafId.current = window.requestAnimationFrame(loop);
    };
    rafId.current = window.requestAnimationFrame(loop);
    return () => {
      if (rafId.current) window.cancelAnimationFrame(rafId.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, viewState]);

  // ── RAF-flush for batched streaming updates ───────────────────────────────
  const flushPendingUpdates = useCallback(() => {
    flushRafId.current = null;
    const batch = pendingUpdates.current.splice(0);
    if (batch.length === 0) return;

    // Deduplicate by task_id: keep the latest event per task
    const deduped = new Map<string, TimelineEventPayload>();
    for (const ev of batch) {
      if (ev.task_id) deduped.set(ev.task_id, ev);
    }

    setNodes((prev) => {
      let next = prev;
      for (const payload of deduped.values()) {
        const existingIndex = next.findIndex((n) => n.id === payload.task_id);
        const label = payload.task_name || payload.task_id;
        const status = payload.status || 'running';
        if (existingIndex >= 0) {
          if (next === prev) next = [...prev];
          next[existingIndex] = {
            ...next[existingIndex],
            status,
            label: label ?? next[existingIndex].label,
            metadata: {
              ...next[existingIndex].metadata,
              progress: payload.progress,
              summary: payload.summary,
            },
          };
        } else {
          if (next === prev) next = [...prev];
          next = [
            ...next,
            {
              id: payload.task_id ?? '',
              label: label ?? '',
              type: 'reasoning' as const,
              status,
              x: 180 + (next.length % 6) * 260,
              y: 120 + Math.floor(next.length / 6) * 100,
              metadata: {
                progress: payload.progress,
                summary: payload.summary,
              },
            },
          ];
        }
      }
      return next;
    });
    needsRedraw.current = true;
  }, []);

  const connectTimelineStream = useCallback(
    (threadId: string, onEvent: (payload: TimelineEventPayload) => void) => {
      let socket: WebSocket | null = null;
      let eventSource: EventSource | null = null;
      let closed = false;

      const dispatchPayload = (rawData: string) => {
        try {
          const payload = JSON.parse(rawData) as TimelineEventPayload;
          const payloadThreadId = payload.thread_id || payload.threadId;
          if (payloadThreadId && payloadThreadId !== threadId) return;
          onEvent(payload);
        } catch {
          // ignore malformed payloads
        }
      };

      const createSse = () => {
        eventSource = new EventSource(buildTimelineStreamUrl(threadId));
        eventSource.onmessage = (ev) => dispatchPayload(ev.data);
        eventSource.onerror = () => {
          if (eventSource?.readyState === EventSource.CLOSED) eventSource.close();
        };
      };

      const createWebSocket = () => {
        try {
          socket = new WebSocket(buildTimelineWebSocketUrl(threadId));
          socket.onopen = () => setStatusMessage('Connected to live agent thread.');
          socket.onmessage = (event) => dispatchPayload(event.data);
          socket.onclose = () => { if (!closed) createSse(); };
          socket.onerror = () => socket?.close();
        } catch {
          createSse();
        }
      };

      if (typeof WebSocket !== 'undefined') {
        createWebSocket();
      } else {
        createSse();
      }

      return () => {
        closed = true;
        socket?.close();
        eventSource?.close();
      };
    },
    []
  );

  // ── Auto-fit view to all nodes ─────────────────────────────────────────────
  const autoFitNodes = useCallback((nodeList: VisualNode[]) => {
    if (nodeList.length === 0) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const W = canvas.clientWidth;
    const H = canvas.clientHeight;
    if (!W || !H) return;

    const padding = 60;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodeList) {
      if (n.x - NODE_HALF_W < minX) minX = n.x - NODE_HALF_W;
      if (n.y - NODE_HALF_H < minY) minY = n.y - NODE_HALF_H;
      if (n.x + NODE_HALF_W > maxX) maxX = n.x + NODE_HALF_W;
      if (n.y + NODE_HALF_H > maxY) maxY = n.y + NODE_HALF_H;
    }
    const contentW = maxX - minX + padding * 2;
    const contentH = maxY - minY + padding * 2;
    const scale = Math.min(1.2, Math.max(0.4, Math.min(W / contentW, H / contentH)));
    const x = (W - (maxX + minX) * scale) / 2;
    const y = (H - (maxY + minY) * scale) / 2;
    setViewState({ x, y, scale });
    needsRedraw.current = true;
  }, []);

  useEffect(() => {
    if (!taskThreadId) {
      setStatusMessage('No active agent thread yet. Start a Concierge goal or ask for a plan.');
      return;
    }

    let isMounted = true;
    fetchTaskTree(taskThreadId)
      .then((tree) => {
        if (!isMounted) return;
        const graph = buildGraphFromTree(tree);
        setNodes(graph.nodes);
        setEdges(graph.edges);
        setStatusMessage('Streaming agent thread updates…');
        // Auto-fit after a microtask so canvas dimensions are settled
        setTimeout(() => autoFitNodes(graph.nodes), 0);
      })
      .catch(() => {
        if (!isMounted) return;
        setStatusMessage('Unable to load thread graph yet. Retrying as the agent starts.');
      });

    const disconnect = connectTimelineStream(taskThreadId, (payload) => {
      if (payload.type === 'plan') return;

      if (payload.type === 'task_update' && payload.task_id) {
        // Push to batch buffer and schedule a RAF flush
        pendingUpdates.current.push(payload);
        if (flushRafId.current === null) {
          flushRafId.current = window.requestAnimationFrame(flushPendingUpdates);
        }
        return;
      }

      if (payload.type === 'node_add' && payload.payload) {
        setNodes((prev) => {
          const rawNode = payload.payload as StreamDeltaNodePayload;
          if (prev.some((n) => n.id === rawNode.id)) return prev;
          const nextNode: VisualNode = {
            id: rawNode.id,
            type: rawNode.type ?? 'reasoning',
            label: rawNode.label || rawNode.id,
            status: rawNode.status || 'running',
            x: typeof rawNode.x === 'number' ? rawNode.x : 180 + (prev.length % 6) * 260,
            y: typeof rawNode.y === 'number' ? rawNode.y : 120 + Math.floor(prev.length / 6) * 100,
            metadata: { progress: 0, ...(rawNode.metadata || {}) },
          };
          return [...prev, nextNode];
        });
        needsRedraw.current = true;
      }

      if (payload.type === 'node_update' && payload.payload) {
        const nodeUpdate = payload.payload as Partial<VisualNode> & { id: string };
        setNodes((prev) =>
          prev.map((node) =>
            node.id === nodeUpdate.id
              ? { ...node, ...nodeUpdate, metadata: { ...node.metadata, ...(nodeUpdate.metadata || {}) } }
              : node
          )
        );
        needsRedraw.current = true;
      }

      if (payload.type === 'edge_add' && payload.payload) {
        const edgeUpdate = payload.payload as VisualEdge;
        setEdges((prev) => {
          if (prev.some((e) => e.fromId === edgeUpdate.fromId && e.toId === edgeUpdate.toId)) return prev;
          return [...prev, edgeUpdate];
        });
        needsRedraw.current = true;
      }
    });

    return () => {
      isMounted = false;
      disconnect();
      if (flushRafId.current !== null) {
        window.cancelAnimationFrame(flushRafId.current);
        flushRafId.current = null;
      }
      pendingUpdates.current = [];
    };
  }, [connectTimelineStream, flushPendingUpdates, taskThreadId, autoFitNodes]);

  useEffect(() => {
    if (!taskThreadId || !selectedNodeId) {
      setNodeMemories([]);
      setMemoryStatus('idle');
      return;
    }
    const controller = new AbortController();
    const loadMemories = async () => {
      setMemoryStatus('loading');
      try {
        const response = await fetch(
          makeApiUrl(
            `/api/v1/concierge/threads/${encodeURIComponent(taskThreadId)}/nodes/${encodeURIComponent(selectedNodeId)}/memories?top_k=8`
          ),
          { signal: controller.signal }
        );
        if (!response.ok) throw new Error(`Failed to fetch memories (${response.status})`);
        const json = (await response.json()) as { data?: { memories?: NodeMemory[] } };
        const memories = Array.isArray(json?.data?.memories) ? json.data.memories : [];
        setNodeMemories(memories);
        setMemoryStatus('ready');
      } catch {
        if (!controller.signal.aborted) {
          setNodeMemories([]);
          setMemoryStatus('error');
        }
      }
    };
    loadMemories();
    return () => controller.abort();
  }, [selectedNodeId, taskThreadId]);

  // Large graph worker re-layout (>200 nodes)
  useEffect(() => {
    if (nodes.length <= 200) return;
    const workerScript = `
      self.onmessage = function(event) {
        var nodes = event.data || [];
        var positioned = nodes.map(function(node, index) {
          var col = index % 16;
          var row = Math.floor(index / 16);
          return { id: node.id, x: 180 + col * 190, y: 120 + row * 100 };
        });
        self.postMessage(positioned);
      };
    `;
    const blob = new Blob([workerScript], { type: 'application/javascript' });
    const workerUrl = URL.createObjectURL(blob);
    const worker = new Worker(workerUrl);
    worker.onmessage = (event: MessageEvent<Array<{ id: string; x: number; y: number }>>) => {
      const byId = new Map(event.data.map((item) => [item.id, item]));
      setNodes((prev) =>
        prev.map((node) => {
          const next = byId.get(node.id);
          return next ? { ...node, x: next.x, y: next.y } : node;
        })
      );
      needsRedraw.current = true;
    };
    worker.postMessage(nodes.map((n) => ({ id: n.id })));
    return () => {
      worker.terminate();
      URL.revokeObjectURL(workerUrl);
    };
  }, [nodes.length]);

  const transformPoint = useCallback(
    (clientX: number, clientY: number) => {
      const root = containerRef.current;
      if (!root) return null;
      const rect = root.getBoundingClientRect();
      const x = (clientX - rect.left - viewState.x) / viewState.scale;
      const y = (clientY - rect.top - viewState.y) / viewState.scale;
      return { x, y };
    },
    [viewState]
  );

  const screenPosition = useCallback(
    (x: number, y: number) => ({
      left: x * viewState.scale + viewState.x,
      top: y * viewState.scale + viewState.y,
    }),
    [viewState]
  );

  // ── Spatial-grid hit testing ───────────────────────────────────────────────
  const findNodeAtPoint = useCallback(
    (point: { x: number; y: number } | null) => {
      if (!point) return null;
      const cx = Math.floor(point.x / SPATIAL_CELL_SIZE);
      const cy = Math.floor(point.y / SPATIAL_CELL_SIZE);
      const candidates = new Set<string>();
      for (let dx = -1; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          const key = `${cx + dx},${cy + dy}`;
          const ids = spatialGrid.get(key);
          if (ids) ids.forEach((id) => candidates.add(id));
        }
      }
      for (const id of candidates) {
        const node = nodeMap.get(id);
        if (!node) continue;
        if (Math.abs(point.x - node.x) <= NODE_HALF_W && Math.abs(point.y - node.y) <= NODE_HALF_H) {
          return id;
        }
      }
      return null;
    },
    [nodeMap, spatialGrid]
  );

  // ── Throttled pointer-move (at most 1 hover update per RAF tick) ───────────
  const handleCanvasPointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (isPanning && lastPointer.current) {
        const dx = event.clientX - lastPointer.current.x;
        const dy = event.clientY - lastPointer.current.y;
        if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
          setViewState((current) => ({ ...current, x: current.x + dx, y: current.y + dy }));
          lastPointer.current = { x: event.clientX, y: event.clientY };
        }
      }

      if (hoverRafPending.current !== null) return;
      const clientX = event.clientX;
      const clientY = event.clientY;
      hoverRafPending.current = window.requestAnimationFrame(() => {
        hoverRafPending.current = null;
        const point = transformPoint(clientX, clientY);
        const hoverId = findNodeAtPoint(point);
        setHoveredNodeId((prev) => (prev !== hoverId ? hoverId : prev));
      });
    },
    [findNodeAtPoint, isPanning, transformPoint]
  );

  const handleCanvasPointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    lastPointer.current = { x: event.clientX, y: event.clientY };
    clickStartPointer.current = { x: event.clientX, y: event.clientY };
    setIsPanning(true);
  }, []);

  const handleCanvasPointerUp = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (isPanning && clickStartPointer.current) {
        const moved = Math.hypot(
          event.clientX - clickStartPointer.current.x,
          event.clientY - clickStartPointer.current.y,
        );
        if (moved < 8) {
          const point = transformPoint(event.clientX, event.clientY);
          const clicked = findNodeAtPoint(point);
          setSelectedNodeId(clicked);
        }
      }
      setIsPanning(false);
      lastPointer.current = null;
      clickStartPointer.current = null;
    },
    [findNodeAtPoint, isPanning, transformPoint]
  );

  const handleCanvasWheel = useCallback((event: React.WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const delta = event.deltaY < 0 ? 1.12 : 0.88;
    setViewState((current) => {
      const nextScale = Math.max(0.35, Math.min(2.6, current.scale * delta));
      const offsetX = event.clientX - rect.left;
      const offsetY = event.clientY - rect.top;
      const logicalX = (offsetX - current.x) / current.scale;
      const logicalY = (offsetY - current.y) / current.scale;
      return {
        scale: nextScale,
        x: offsetX - logicalX * nextScale,
        y: offsetY - logicalY * nextScale,
      };
    });
  }, []);

  // ── Side panel callbacks (stable refs, won't cause NodeDetailPanel re-renders) ──
  const handleKillTask = useCallback(async (node: VisualNode) => {
    const celeryTaskId = node.metadata?.celery_task_id;
    if (!celeryTaskId) {
      alert('Cannot kill task: Celery task ID not found in metadata.');
      return;
    }
    try {
      await fetch(makeApiUrl(`/api/v1/tasks/${encodeURIComponent(String(celeryTaskId))}/kill`), { method: 'POST' });
      setStatusMessage(`Sent kill signal to task ${node.label}.`);
    } catch (err) {
      console.error('Failed to kill task', err);
      alert('Failed to send kill signal.');
    }
  }, []);

  const handleOpenThreadStatus = useCallback(() => {
    if (!taskThreadId || !selectedNodeId) return;
    window.open(makeApiUrl(`/tasks/${encodeURIComponent(taskThreadId)}/status`), '_blank');
  }, [taskThreadId, selectedNodeId]);

  const handleDeselect = useCallback(() => setSelectedNodeId(null), []);

  const resetView = useCallback(() => {
    setViewState({ x: 0, y: 0, scale: 1 });
    needsRedraw.current = true;
  }, []);

  const fitView = useCallback(() => autoFitNodes(nodes), [autoFitNodes, nodes]);

  return (
    <div className="agentic-thread-visualizer">
      <div className="agentic-thread-visualizer__status-bar">
        <span>{taskThreadId ? `Thread ${taskThreadId}` : 'Agent thread inactive'}</span>
        <span>{statusMessage}</span>
        <div className="agentic-thread-visualizer__controls">
          <button type="button" onClick={fitView}>Fit view</button>
          <button type="button" onClick={resetView}>Reset view</button>
          <button type="button" onClick={() => setViewState((c) => ({ ...c, scale: Math.min(2.6, c.scale * 1.15) }))}>Zoom in</button>
          <button type="button" onClick={() => setViewState((c) => ({ ...c, scale: Math.max(0.35, c.scale * 0.88) }))}>Zoom out</button>
        </div>
      </div>
      {isMobileFallback ? (
        <div className="agentic-thread-mobile-summary">
          <div className="agentic-thread-mobile-summary__header">
            <h3>Agent thread summary</h3>
            <p>Tap a node to inspect steps, tool calls, and retrievals.</p>
          </div>
          <div className="agentic-thread-mobile-summary__list">
            {nodes.map((node) => (
              <button
                key={node.id}
                type="button"
                className={`agentic-thread-mobile-item ${selectedNodeId === node.id ? 'agentic-thread-mobile-item--active' : ''}`}
                onClick={() => setSelectedNodeId(node.id)}
              >
                <div>
                  <strong>{node.label}</strong>
                  <span>{node.type}</span>
                </div>
                <small>{node.status}</small>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="agentic-thread-visualizer__canvas-wrapper">
          <div
            ref={containerRef}
            className={`agentic-thread-canvas-shell ${isPanning ? 'agentic-thread-canvas-shell--panning' : ''}`}
            onPointerMove={handleCanvasPointerMove}
            onPointerDown={handleCanvasPointerDown}
            onPointerUp={handleCanvasPointerUp}
            onPointerLeave={handleCanvasPointerUp}
            onWheel={handleCanvasWheel}
          >
            <div className="agentic-thread-canvas-inner">
              <canvas ref={canvasRef} className="agentic-thread-canvas" aria-label="Concierge thread graph" />
              {nodes
                .filter((node) => node.id === hoveredNodeId || node.id === selectedNodeId)
                .map((node) => {
                  const { left, top } = screenPosition(node.x, node.y);
                  return (
                    <button
                      key={`overlay-${node.id}`}
                      type="button"
                      className={`agentic-thread-node-chip ${selectedNodeId === node.id ? 'agentic-thread-node-chip--selected' : ''}`}
                      style={{ left, top }}
                      onClick={(event) => {
                        event.stopPropagation();
                        setSelectedNodeId(node.id);
                      }}
                      onMouseEnter={() => setHoveredNodeId(node.id)}
                      onMouseLeave={() => setHoveredNodeId(null)}
                    >
                      <span>{node.label}</span>
                      <small>{node.type.replace('_', ' ')} · {node.status}</small>
                    </button>
                  );
                })}
            </div>
          </div>
          <aside className="agentic-thread-sidepanel">
            <NodeDetailPanel
              selectedNode={selectedNode}
              nodeMemories={nodeMemories}
              memoryStatus={memoryStatus}
              taskThreadId={taskThreadId}
              onKillTask={handleKillTask}
              onOpenThreadStatus={handleOpenThreadStatus}
              onDeselect={handleDeselect}
            />
          </aside>
        </div>
      )}
    </div>
  );
};

export default AgenticThreadCanvas;
