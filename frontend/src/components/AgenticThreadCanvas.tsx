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
  metadata: Record<string, any>;
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

const buildGraphFromTree = (tree: TaskTreeNode): { nodes: VisualNode[]; edges: VisualEdge[] } => {
  const nodes: VisualNode[] = [];
  const edges: VisualEdge[] = [];
  let rowIndex = 0;

  const walk = (node: TaskTreeNode, depth = 0, parentId?: string) => {
    const x = 180 + depth * 320;
    const y = 120 + rowIndex * 120;
    const nodeId = node.task_id;
    const status = node.status || 'running';

    nodes.push({
      id: nodeId,
      type: toVisualType(node),
      label: node.task_name || node.task_id,
      status,
      x,
      y,
      metadata: {
        progress: node.progress,
        state: node.state,
        ...node.metadata,
      },
    });

    if (parentId) {
      edges.push({ fromId: parentId, toId: nodeId, type: 'dependency' });
    }

    rowIndex += 1;
    (node.children || []).forEach((child) => walk(child, depth + 1, nodeId));
  };

  walk(tree, 0, undefined);
  return { nodes, edges };
};

const computeBezierPoint = (t: number, p0: number, p1: number, p2: number, p3: number) =>
  ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3;

const getEventSourceUrl = () => makeApiUrl('/api/v1/concierge/timeline/stream');

const AgenticThreadCanvas: React.FC = () => {
  const taskThreadId = useAppStore((s) => s.taskThreadId);
  const [nodes, setNodes] = useState<VisualNode[]>([]);
  const [edges, setEdges] = useState<VisualEdge[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('Loading thread graph…');
  const [isMobileFallback, setIsMobileFallback] = useState(false);
  const [lastEventAt, setLastEventAt] = useState<number>(0);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const rafId = useRef<number | null>(null);
  const particleFrame = useRef(0);

  const [viewState, setViewState] = useState({ x: 0, y: 0, scale: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const lastPointer = useRef<{ x: number; y: number } | null>(null);

  const selectedNode = useMemo(
    () => nodes.find((node) => node.id === selectedNodeId) || null,
    [nodes, selectedNodeId]
  );

  const nodeMap = useMemo(
    () => new Map(nodes.map((node) => [node.id, node])),
    [nodes]
  );

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
    if (ctx) {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
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

      ctx.strokeStyle = 'rgba(96, 165, 250, 0.28)';
      ctx.lineWidth = 2.4;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, to.x, to.y);
      ctx.stroke();

      const particlePosition = ((particleFrame.current + index * 12) % 180) / 180;
      const px = computeBezierPoint(particlePosition, from.x, cp1x, cp2x, to.x);
      const py = computeBezierPoint(particlePosition, from.y, cp1y, cp2y, to.y);
      ctx.fillStyle = 'rgba(255,255,255,0.95)';
      ctx.beginPath();
      ctx.arc(px, py, 3.2, 0, Math.PI * 2);
      ctx.fill();
    });

    nodes.forEach((node) => {
      if (node.x < visibleX0 || node.x > visibleX1 || node.y < visibleY0 || node.y > visibleY1) {
        return;
      }
      const isSelected = node.id === selectedNodeId;
      const isHovered = node.id === hoveredNodeId;
      const nodeColor = getStatusColor(node.status);
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(node.x - 96, node.y - 28, 192, 56, 20);
      ctx.fillStyle = isSelected ? 'rgba(31, 41, 55, 0.98)' : 'rgba(15, 23, 42, 0.92)';
      ctx.fill();
      ctx.strokeStyle = isSelected ? 'rgba(56, 189, 248, 0.92)' : 'rgba(148, 163, 184, 0.18)';
      ctx.lineWidth = isHovered || isSelected ? 3 : 1.5;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(node.x - 66, node.y, 18, 0, Math.PI * 2);
      ctx.fillStyle = nodeColor;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.14)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.fillStyle = '#e2e8f0';
      ctx.font = '600 12px Inter, system-ui, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      const text = node.label.length > 24 ? `${node.label.slice(0, 24)}…` : node.label;
      ctx.fillText(text, node.x - 44, node.y);
      ctx.restore();
    });

    ctx.restore();
  }, [edges, nodeMap, nodes, selectedNodeId, hoveredNodeId, viewState]);

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

  useEffect(() => {
    const loop = () => {
      particleFrame.current += 1;
      drawScene();
      rafId.current = window.requestAnimationFrame(loop);
    };
    rafId.current = window.requestAnimationFrame(loop);
    return () => {
      if (rafId.current) {
        window.cancelAnimationFrame(rafId.current);
      }
    };
  }, [drawScene]);

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
      })
      .catch(() => {
        if (!isMounted) return;
        setStatusMessage('Unable to load thread graph yet. Retrying as the agent starts.');
      });

    const eventSource = new EventSource(getEventSourceUrl());
    eventSource.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        if (payload.thread_id && payload.thread_id !== taskThreadId) {
          return;
        }
        setLastEventAt(Date.now());
        if (payload.type === 'task_update' && payload.task_id) {
          setNodes((prev) => {
            const existingIndex = prev.findIndex((node) => node.id === payload.task_id);
            const label = payload.task_name || payload.task_id;
            const status = payload.status || 'running';
            if (existingIndex >= 0) {
              const next = [...prev];
              next[existingIndex] = {
                ...next[existingIndex],
                status,
                label,
                metadata: {
                  ...next[existingIndex].metadata,
                  progress: payload.progress,
                  summary: payload.summary,
                },
              };
              return next;
            }
            const nextNode: VisualNode = {
              id: payload.task_id,
              label,
              type: 'reasoning',
              status,
              x: 180 + (prev.length % 6) * 260,
              y: 120 + Math.floor(prev.length / 6) * 100,
              metadata: {
                progress: payload.progress,
                summary: payload.summary,
              },
            };
            return [...prev, nextNode];
          });
        }
        if (payload.type === 'node_add' && payload.payload) {
          setNodes((prev) => {
            const rawNode = payload.payload as Partial<VisualNode> & { id: string };
            if (prev.some((n) => n.id === rawNode.id)) return prev;
            const nextNode: VisualNode = {
              id: rawNode.id,
              type: rawNode.type ?? 'reasoning',
              label: rawNode.label || rawNode.id,
              status: rawNode.status || 'running',
              x: typeof rawNode.x === 'number' ? rawNode.x : 180 + (prev.length % 6) * 260,
              y: typeof rawNode.y === 'number' ? rawNode.y : 120 + Math.floor(prev.length / 6) * 100,
              metadata: {
                progress: 0,
                ...(rawNode.metadata || {}),
              },
            };
            return [...prev, nextNode];
          });
        }
        if (payload.type === 'node_update' && payload.payload) {
          const nodeUpdate = payload.payload as Partial<VisualNode> & { id: string };
          setNodes((prev) => prev.map((node) => (node.id === nodeUpdate.id ? { ...node, ...nodeUpdate } : node)));
        }
        if (payload.type === 'edge_add' && payload.payload) {
          const edgeUpdate = payload.payload as VisualEdge;
          setEdges((prev) => {
            if (prev.some((edge) => edge.fromId === edgeUpdate.fromId && edge.toId === edgeUpdate.toId)) return prev;
            return [...prev, edgeUpdate];
          });
        }
      } catch {
        // ignore malformed messages
      }
    };
    eventSource.onerror = () => {
      if (eventSource.readyState === EventSource.CLOSED) {
        eventSource.close();
      }
    };

    return () => {
      isMounted = false;
      eventSource.close();
    };
  }, [taskThreadId]);

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

  const findNodeAtPoint = useCallback(
    (point: { x: number; y: number } | null) => {
      if (!point) return null;
      return nodes.find((node) => {
        const dx = point.x - node.x;
        const dy = point.y - node.y;
        return Math.abs(dx) <= 96 && Math.abs(dy) <= 28;
      })?.id || null;
    },
    [nodes]
  );

  const handleCanvasPointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const point = transformPoint(event.clientX, event.clientY);
      const hoverId = findNodeAtPoint(point);
      setHoveredNodeId(hoverId);
      if (isPanning && lastPointer.current) {
        const dx = event.clientX - lastPointer.current.x;
        const dy = event.clientY - lastPointer.current.y;
        setViewState((current) => ({ ...current, x: current.x + dx, y: current.y + dy }));
        lastPointer.current = { x: event.clientX, y: event.clientY };
      }
    },
    [findNodeAtPoint, isPanning, transformPoint]
  );

  const handleCanvasPointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    lastPointer.current = { x: event.clientX, y: event.clientY };
    setIsPanning(true);
  }, []);

  const handleCanvasPointerUp = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (isPanning && lastPointer.current) {
        const moved = Math.hypot(event.clientX - lastPointer.current.x, event.clientY - lastPointer.current.y);
        if (moved < 8) {
          const point = transformPoint(event.clientX, event.clientY);
          const clicked = findNodeAtPoint(point);
          setSelectedNodeId(clicked);
        }
      }
      setIsPanning(false);
      lastPointer.current = null;
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

  const renderNodeDetails = () => {
    if (!selectedNode) {
      return (
        <div className="agentic-thread-panel-empty">
          Select any node to inspect execution metadata, retrieved documents, and tool context.
        </div>
      );
    }

    const documents: RetrievalDocument[] =
      selectedNode.metadata?.retrieved_documents || selectedNode.metadata?.documents || selectedNode.metadata?.matches || [];

    return (
      <div className="agentic-thread-sidepanel__content">
        <h3>{selectedNode.label}</h3>
        <div className="agentic-thread-node-meta">
          <span>Status: {selectedNode.status}</span>
          <span>Type: {selectedNode.type}</span>
          <span>Progress: {selectedNode.metadata?.progress ?? 'N/A'}</span>
          {typeof selectedNode.metadata?.confidence === 'number' ? (
            <span>Confidence: {(selectedNode.metadata.confidence * 100).toFixed(0)}%</span>
          ) : null}
        </div>
        {selectedNode.metadata?.summary ? (
          <section>
            <h4>Summary</h4>
            <p>{selectedNode.metadata.summary}</p>
          </section>
        ) : null}
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
                  {doc.url ? (
                    <a href={doc.url} target="_blank" rel="noreferrer">Open source</a>
                  ) : null}
                </article>
              ))}
            </div>
          </section>
        ) : null}
        {selectedNode.metadata?.agent_type || selectedNode.metadata?.tool_name ? (
          <section>
            <h4>Tool / agent context</h4>
            <p>{selectedNode.metadata?.agent_type || selectedNode.metadata?.tool_name}</p>
            <pre>{JSON.stringify(selectedNode.metadata, null, 2)}</pre>
          </section>
        ) : null}
        <div className="agentic-thread-sidepanel__actions">
          <button
            className="agentic-thread-action"
            onClick={() => {
              if (!taskThreadId || !selectedNode) return;
              window.open(makeApiUrl(`/tasks/${encodeURIComponent(taskThreadId)}/status`), '_blank');
            }}
          >
            Open thread status
          </button>
          <button
            className="agentic-thread-action agentic-thread-action--secondary"
            onClick={() => setSelectedNodeId(null)}
          >
            Deselect node
          </button>
        </div>
      </div>
    );
  };

  const resetView = useCallback(() => {
    setViewState({ x: 0, y: 0, scale: 1 });
  }, []);

  return (
    <div className="agentic-thread-visualizer">
      <div className="agentic-thread-visualizer__status-bar">
        <span>{taskThreadId ? `Thread ${taskThreadId}` : 'Agent thread inactive'}</span>
        <span>{statusMessage}</span>
        <div className="agentic-thread-visualizer__controls">
          <button type="button" onClick={resetView}>Reset view</button>
          <button type="button" onClick={() => setViewState((current) => ({ ...current, scale: Math.min(2.6, current.scale * 1.15) }))}>Zoom in</button>
          <button type="button" onClick={() => setViewState((current) => ({ ...current, scale: Math.max(0.35, current.scale * 0.88) }))}>Zoom out</button>
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
              {nodes.filter((node) => node.id === hoveredNodeId || node.id === selectedNodeId).map((node) => {
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
            {renderNodeDetails()}
          </aside>
        </div>
      )}
    </div>
  );
};

export default AgenticThreadCanvas;
