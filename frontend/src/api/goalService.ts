import apiClient from './client';
import { ApiResponse } from '../types/api';

export const getGoals = async () => {
  return apiClient.get<ApiResponse>('/goals');
};

export const createGoal = async (data: any) => {
  return apiClient.post<ApiResponse>('/goals', data);
};
