import apiClient from './client';
import { ApiResponse } from '../types/api';

export const sendMessage = async (message: string) => {
  return apiClient.post<ApiResponse>('/concierge/message', { message });
};

export const fetchConversation = async () => {
  return apiClient.get<ApiResponse>('/concierge/conversation');
};
