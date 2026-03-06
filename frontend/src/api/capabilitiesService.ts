import axios from 'axios';

const apiClient = axios.create({ baseURL: '/api/v1', timeout: 15000 });

export interface CapabilityItem {
  name: string;
  description: string;
  version?: string;
  type: 'plugin' | 'tool' | 'integration';
  enabled?: boolean;
  service?: string;
}

interface ApiEnvelope<T> {
  status: string;
  data: T;
}

async function fetchCapabilities(path: string): Promise<CapabilityItem[]> {
  const res = await apiClient.get<ApiEnvelope<CapabilityItem[]>>(path);
  return res.data.data ?? [];
}

export const capabilitiesService = {
  plugins: () => fetchCapabilities('/plugins'),
  tools: () => fetchCapabilities('/tools'),
  integrations: () => fetchCapabilities('/integrations'),
};
