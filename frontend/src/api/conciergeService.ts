import apiClient from './client';
import { ApiResponse } from '../types/api';

export const sendMessage = async (message: string) => {
  const res = await apiClient.post<ApiResponse>('/concierge/message', { message });
  if ((res as any).error) {
    throw new Error((res as any).error);
  }
  return res;
};

export const fetchConversation = async () => {
  const res = await apiClient.get<ApiResponse>('/concierge/conversation');
  if ((res as any).error) {
    throw new Error((res as any).error);
  }
  return res;
};
