import React, { useEffect, useState } from 'react';
import { capabilitiesService, CapabilityItem } from '@/api/capabilitiesService';

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
        background: 'var(--color-surface, #1e1e2f)',
        border: '1px solid var(--color-border, #333)',
        borderRadius: 8,
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
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
              background: '#374151',
              color: '#9ca3af',
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 99,
            }}
          >
            disabled
          </span>
        )}
      </div>
      <div style={{ fontWeight: 600, fontSize: 15 }}>{item.name}</div>
      {item.service && (
        <div style={{ fontSize: 12, color: '#9ca3af' }}>Service: {item.service}</div>
      )}
      <div style={{ fontSize: 13, color: '#cbd5e1' }}>{item.description}</div>
      {item.version && (
        <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>v{item.version}</div>
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
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: '1rem', color: 'var(--color-text, #e2e8f0)' }}>
        {title}
        <span style={{ fontWeight: 400, fontSize: 13, color: '#9ca3af', marginLeft: 8 }}>
          ({loading ? '…' : items.length})
        </span>
      </h2>
      {error && (
        <p style={{ color: '#f87171', fontSize: 13 }}>Failed to load: {error}</p>
      )}
      {!loading && !error && items.length === 0 && (
        <p style={{ color: '#6b7280', fontSize: 13 }}>No items registered.</p>
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

  useEffect(() => {
    CATEGORIES.forEach(({ key }) => {
      capabilitiesService[key]()
        .then((items) => {
          setData((prev) => ({ ...prev, [key]: items }));
        })
        .catch((err: Error) => {
          setErrors((prev) => ({ ...prev, [key]: err.message ?? 'Unknown error' }));
        })
        .finally(() => {
          setLoading((prev) => ({ ...prev, [key]: false }));
        });
    });
  }, []);

  return (
    <div style={{ padding: '1.5rem', maxWidth: 1100, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: '0.5rem', color: 'var(--color-text, #e2e8f0)' }}>
        Capabilities
      </h1>
      <p style={{ color: '#9ca3af', fontSize: 14, marginBottom: '2rem' }}>
        Registered plugins, tools, and external integrations available to the orchestration engine.
      </p>

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
