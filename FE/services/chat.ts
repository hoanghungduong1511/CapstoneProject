import api from './api';
import type {
  ChatMessageRecord,
  ChatSessionDetail,
  ChatSessionListResponse,
  ChatTurnResponse,
} from '@/types';

export async function createChatSession(
  aiResultId?: string,
  initialMessage?: string,
): Promise<ChatSessionDetail> {
  const response = await api.post<ChatSessionDetail>('/api/v1/chat/sessions', {
    ai_result_id: aiResultId || null,
    initial_message: initialMessage || null,
  });
  return response.data;
}

export async function saveChatMessage(
  sessionId: string,
  role: 'user' | 'assistant',
  content: string,
  metadata?: Record<string, unknown>,
): Promise<ChatMessageRecord> {
  const response = await api.post<ChatMessageRecord>(
    `/api/v1/chat/sessions/${sessionId}/messages`,
    { role, content, metadata: metadata || null },
  );
  return response.data;
}

export async function generateChatResponse(
  sessionId: string,
  message: string,
  aiResultId?: string | null,
): Promise<ChatTurnResponse> {
  const response = await api.post<ChatTurnResponse>(
    `/api/v1/chat/sessions/${sessionId}/messages`,
    { message, ai_result_id: aiResultId || null },
  );
  return response.data;
}

export async function getChatSessions(
  skip = 0,
  limit = 30,
): Promise<ChatSessionListResponse> {
  const response = await api.get<ChatSessionListResponse>('/api/v1/chat/sessions', {
    params: { skip, limit },
  });
  return response.data;
}

export async function getChatSession(sessionId: string): Promise<ChatSessionDetail> {
  const response = await api.get<ChatSessionDetail>(
    `/api/v1/chat/sessions/${sessionId}`,
  );
  return response.data;
}
