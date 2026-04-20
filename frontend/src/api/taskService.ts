import apiClient from './client';
import { ApiResponse } from '../types/api';

export interface TaskTreeNode {
  task_id: string;
  parent_id?: string | null;
  task_name?: string;
  status: string;
  state: string;
  progress: number;
  color?: string;
  metadata?: Record<string, unknown>;
  children: TaskTreeNode[];
}

export interface TaskTree {
  task_id: string;
  parent_id?: string | null;
  task_name?: string;
  status: string;
  state: string;
  progress: number;
  color?: string;
  metadata?: Record<string, unknown>;
  children: TaskTreeNode[];
}

export const getTasks = async () => {
  return apiClient.get<ApiResponse>('/tasks');
};

export const updateTask = async (id: string, data: any) => {
  return apiClient.put<ApiResponse>(`/tasks/${id}`, data);
};

export async function fetchTaskTree(taskId: string): Promise<TaskTree> {
  const { data } = await apiClient.get<{ data: TaskTree }>(`/tasks/${encodeURIComponent(taskId)}/status`);
  return data.data;
}
