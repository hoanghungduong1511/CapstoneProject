import type { DiagnosisHistory, User } from '@/types';
import api from './api';

export async function updateProfile(data: {
  name?: string;
  date_of_birth?: string;
  gender?: string;
}): Promise<User> {
  const res = await api.put('/api/v1/auth/me', data);
  return res.data;
}

export async function uploadAvatar(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await api.put('/api/v1/auth/me/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return res.data.avatar_url;
}

export async function changePassword(data: {
  current_password: string;
  new_password: string;
}): Promise<void> {
  await api.put('/api/v1/auth/me/password', data);
}

export async function getDiagnosisHistory(
  skip = 0,
  limit = 50,
): Promise<DiagnosisHistory> {
  const res = await api.get('/api/v1/auth/me/history', {
    params: { skip, limit },
  });

  return res.data;
}
