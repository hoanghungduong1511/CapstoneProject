import type {
  AdminUserDetail,
  AdminUserListResponse,
} from '@/types';
import api from './api';

export async function getAdminUsers(params?: {
  search?: string;
  status?: 'active' | 'inactive' | '';
  skip?: number;
  limit?: number;
}): Promise<AdminUserListResponse> {
  const response = await api.get<AdminUserListResponse>('/api/v1/admin/users', {
    params: {
      search: params?.search || undefined,
      status: params?.status || undefined,
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 20,
    },
  });
  return response.data;
}

export async function getAdminUserDetail(userId: string): Promise<AdminUserDetail> {
  const response = await api.get<AdminUserDetail>(`/api/v1/admin/users/${userId}`);
  return response.data;
}

export async function setAdminUserLocked(
  userId: string,
  locked: boolean,
): Promise<{ id: string; status: string; message: string }> {
  const response = await api.patch(`/api/v1/admin/users/${userId}/status`, {
    locked,
  });
  return response.data;
}
