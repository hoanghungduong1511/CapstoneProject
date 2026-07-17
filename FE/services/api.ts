import axios from 'axios';
import Cookies from 'js-cookie';
import type { AuthTokens, ClassificationCandidate, SkinAnalysisResponse, ValidationResult } from '@/types';
import { normalizeStorageUrl } from '@/lib/image-url';

// Configure axios instance
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 60000, // 60 seconds for image processing
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request Interceptor: tự động gắn access token ──────────────────
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = Cookies.get('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: tự động refresh khi 401 ─────────────────
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Nếu 401 và chưa retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Không refresh nếu đang gọi endpoint login/register/refresh
      const url = originalRequest.url || '';
      if (url.includes('/auth/login') || url.includes('/auth/register') || url.includes('/auth/refresh')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Nếu đang refresh → đợi queue
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = Cookies.get('refresh_token');
        if (!refreshToken) throw new Error('No refresh token');

        const res = await axios.post<AuthTokens>(
          `${api.defaults.baseURL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token: newRefreshToken } = res.data;

        // Lưu tokens mới vào cookies
        Cookies.set('access_token', access_token, { path: '/', sameSite: 'Lax', expires: 1 / 48 });
        Cookies.set('refresh_token', newRefreshToken, { path: '/', sameSite: 'Lax', expires: 7 });

        // Retry original request
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        processQueue(null, access_token);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        // Refresh thất bại → xóa tokens, redirect về login
        Cookies.remove('access_token', { path: '/' });
        Cookies.remove('refresh_token', { path: '/' });
        // Dispatch custom event để app biết cần logout
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('auth:logout'));
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Types (ChatResponse is still needed)
export interface ChatResponse {
  success: boolean;
  data: {
    message: string;
  };
  error?: string;
}

// API Functions

function normalizeClassificationCandidate(candidate: ClassificationCandidate): ClassificationCandidate {
  if (
    candidate.icd === 'B35' ||
    candidate.id === 'TINEA' ||
    candidate.latinName?.toLowerCase() === 'dermatophytosis'
  ) {
    return {
      ...candidate,
      latinName: 'TINEA',
    };
  }

  return candidate;
}

function normalizeAnalysisResponse(data: SkinAnalysisResponse): SkinAnalysisResponse {
  return {
    ...data,
    original_image_url: normalizeStorageUrl(data.original_image_url),
    classification: data.classification
      ? {
          ...data.classification,
          candidates: data.classification.candidates.map(normalizeClassificationCandidate),
        }
      : undefined,
    segmentation: data.segmentation
      ? {
          ...data.segmentation,
          mask_url: normalizeStorageUrl(data.segmentation.mask_url),
          roi_url: normalizeStorageUrl(data.segmentation.roi_url),
        }
      : undefined,
  };
}

/**
 * Validate uploaded image before running segmentation.
 */
export async function validateSkinImage(imageFile: File): Promise<ValidationResult> {
  const formData = new FormData();
  formData.append('file', imageFile);

  const response = await api.post<ValidationResult>('/api/v1/analyze/validate-skin', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Upload and analyze skin image via backend API
 */
export async function analyzeImage(imageFile: File): Promise<SkinAnalysisResponse> {
  const formData = new FormData();
  formData.append('file', imageFile);

  const response = await api.post<SkinAnalysisResponse>('/api/v1/analyze/skin', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return normalizeAnalysisResponse(response.data);
}

/**
 * Restore a previously saved analysis for the result screen.
 */
export async function getAnalysisHistoryDetail(
  aiResultId: string,
): Promise<SkinAnalysisResponse> {
  const response = await api.get<SkinAnalysisResponse>(
    `/api/v1/analyze/history/${aiResultId}`,
  );
  return normalizeAnalysisResponse(response.data);
}

/**
 * Send chat message to AI
 */
export async function sendChatMessage(
  message: string,
  context: {
    predictedDisease: string;
    confidence: number;
    basicInfo: string;
  }
): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/api/chat', {
    message,
    context,
  });

  return response.data;
}

/**
 * Health check
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await api.get('/health');
    return response.status === 200;
  } catch {
    return false;
  }
}

export default api;
