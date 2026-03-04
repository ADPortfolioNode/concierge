import apiClient from './client';
import { ApiResponse } from '../types/api';

export const getTasks = async () => {
  return apiClient.get<ApiResponse>('/tasks');
};

export const updateTask = async (id: string, data: any) => {
  return apiClient.put<ApiResponse>(`/tasks/${id}`, data);
};
