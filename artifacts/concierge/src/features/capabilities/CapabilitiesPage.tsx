import React, { useEffect, useState, useCallback } from 'react';
import { CapabilityItem } from '@/api/capabilitiesService';
import { makeApiUrl } from '@/config/activeServer';

type Category = 'plugins' | 'tools' | 'integrations';

const CATEGORIES: { key: Category; label: string }[] = [
  { key: 'plugins', label: 'Plugins' },
  { key: 'tools', label: 'Tools' },
  { key: 'integrations', label: 'Integrations' },
];

const badgeColor: Record<string, string> = {
  plugin: '#4f46e5',
  tool: '#0891b2',
  integration: '#059669',
};

function CapabilityCard({ item }: { item: CapabilityItem }) {
  const color = badgeColor[item.type] ?? '#6b7280';
  return (
    <div
      style={{
        background: '#FFFFFF',
        border: '1px solid #DBEAFE',
        borderRadius: 8,
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        boxShadow: '0 1px 4px rgba(37,99,235,0.06)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{
            background: color,
            color: '#fff',
            fontSize: 11,
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: 99,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {item.type}
        </span>
        {item.enabled === false && (
          <span
            style={{
              background: '#F0F8FF',
              color: '#64748B',
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 99,
              border: '1px solid #DBEAFE',
            }}
          >
            disabled
          </span>
        )}
      </div>
      <div style={{ fontWeight: 600, fontSize: 15, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#0F172A' }} title={item.name}>{item.name}</div>
      {item.service && (
        <div style={{ fontSize: 12, color: '#64748B', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Service: {item.service}</div>
      )}
      <div style={{ fontSize: 13, color: '#475569', overflowWrap: 'break-word', wordBreak: 'break-word' }}>{item.description}</div>
      {item.version && (
        <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>v{item.version}</div>
      )}
    </div>
  );
}

function Section({
  title,
  items,
  loading,
  error,
}: {
  title: string;
  items: CapabilityItem[];
  loading: boolean;
  error: string | null;
}) {
  return (
    <section style={{ marginBottom: '2rem' }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: '1rem', color: '#0F172A' }}>
        {title}
        <span style={{ fontWeight: 400, fontSize: 13, color: '#64748B', marginLeft: 8 }}>
          ({loading ? '…' : items.length})
        </span>
      </h2>
      {error && (
        <p style={{ color: '#DC2626', fontSize: 13 }}>Failed to load: {error}</p>
      )}
      {!loading && !error && items.length === 0 && (
        <p style={{ color: '#64748B', fontSize: 13 }}>No items registered.</p>
      )}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: '1rem',
        }}
      >
        {items.map((item) => (
          <CapabilityCard key={`${item.type}-${item.name}`} item={item} />
        ))}
      </div>
    </section>
  );
}

export default function CapabilitiesPage() {
  const [data, setData] = useState<Record<Category, CapabilityItem[]>>({
    plugins: [],
    tools: [],
    integrations: [],
  });
  const [loading, setLoading] = useState<Record<Category, boolean>>({
    plugins: true,
    tools: true,
    integrations: true,
  });
  const [errors, setErrors] = useState<Record<Category, string | null>>({
    plugins: null,
    tools: null,
    integrations: null,
  });
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchCapabilities = useCallback(async (force = false) => {
    setLoading({ plugins: true, tools: true, integrations: true });
    setErrors({ plugins: null, tools: null, integrations: null });

    try {
      const base = force ? '/api/v1/capabilities?force=true' : '/api/v1/capabilities';
      const url = makeApiUrl ? makeApiUrl(base) : base;  // use configured base when available
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Network error: ${response.status} ${response.statusText}`);
      }
      const jsonResponse = await response.json();
      if (jsonResponse.status !== 'success') {
        throw new Error(jsonResponse.errors?.message ?? 'API returned an error');
      }
      const capabilities = jsonResponse.data;
      setData({
        plugins: capabilities.plugins || [],
        tools: capabilities.tools || [],
        integrations: capabilities.integrations || [],
      });
      setLastUpdated(new Date());
    } catch (err: any) {
      const errorMessage = err.message ?? 'Unknown error';
      setErrors({
        plugins: errorMessage,
        tools: errorMessage,
        integrations: errorMessage,
      });
    } finally {
      setLoading({ plugins: false, tools: false, integrations: false });
    }
  }, []);

  useEffect(() => {
    fetchCapabilities();
  }, [fetchCapabilities]);

  const isAnyLoading = Object.values(loading).some(Boolean);

  return (
    <div className="page-content" style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0, letterSpacing: '-0.01em', color: '#0F172A' }}>
          Capabilities
        </h1>
        <button
          onClick={() => fetchCapabilities(true)}
          disabled={isAnyLoading}
          title="Force a refresh, bypassing the cache"
          style={{
            background: '#EFF6FF',
            border: '1px solid #BFDBFE',
            color: '#2563EB',
            borderRadius: 6,
            padding: '6px 12px',
            cursor: isAnyLoading ? 'not-allowed' : 'pointer',
            opacity: isAnyLoading ? 0.6 : 1,
            fontWeight: 600,
            fontSize: 13,
          }}
        >
          {isAnyLoading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      <p style={{ color: '#64748B', fontSize: 14, marginBottom: '2rem', marginTop: 0 }}>
        Registered plugins, tools, and external integrations available to the orchestration engine.
      </p>

      {lastUpdated && !isAnyLoading && (
        <div style={{ textAlign: 'right', color: '#94A3B8', fontSize: 12, marginTop: '-1.5rem', marginBottom: '1.5rem' }}>
          Last updated: {lastUpdated.toLocaleTimeString()}
        </div>
      )}

      {isAnyLoading && (
        <div style={{
          marginBottom: '2rem',
          textAlign: 'center',
          color: '#475569',
          fontSize: 16,
          padding: '1rem',
          background: '#F0F8FF',
          border: '1px solid #DBEAFE',
          borderRadius: 8,
        }}>
          Loading capabilities...
        </div>
      )}
      {CATEGORIES.map(({ key, label }) => (
        <Section
          key={key}
          title={label}
          items={data[key]}
          loading={loading[key]}
          error={errors[key]}
        />
      ))}
    </div>
  );
}
