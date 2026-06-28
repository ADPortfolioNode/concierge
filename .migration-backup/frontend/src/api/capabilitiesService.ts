<<<<<<<< HEAD:artifacts/concierge/src/api/capabilitiesService.ts
import axios from 'axios';
import { makeApiUrl } from '@/config/activeServer';

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
========
import axios from 'axios';
import { makeApiUrl } from '@/config/activeServer';

const apiClient = axios.create({ baseURL: makeApiUrl('/api/v1'), timeout: 15000 });

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
>>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5:.migration-backup/frontend/src/api/capabilitiesService.ts
