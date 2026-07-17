import Cookies from 'js-cookie';
import type { User, AuthTokens } from '@/types';
import api from './api';

const TOKEN_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

// Cookie options
const COOKIE_OPTIONS: Cookies.CookieAttributes = {
  path: '/',
  sameSite: 'Lax',
  secure: false, // Set true in production with HTTPS
};

// ── Token Storage (Cookies) ─────────────────────────────────────────

export function getAccessToken(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  return Cookies.get(TOKEN_KEY);
}

export function getRefreshToken(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  return Cookies.get(REFRESH_KEY);
}

export function saveTokens(tokens: AuthTokens): void {
  console.log('[Auth] saveTokens called with:', {
    hasAccessToken: !!tokens.access_token,
    hasRefreshToken: !!tokens.refresh_token,
    tokenType: tokens.token_type,
  });

  if (!tokens.access_token || !tokens.refresh_token) {
    console.error('[Auth] Tokens are missing from API response!', tokens);
    return;
  }

  // Access token: expires in 30 minutes
  Cookies.set(TOKEN_KEY, tokens.access_token, {
    ...COOKIE_OPTIONS,
    expires: 1 / 48, // 30 minutes (1/48 of a day)
  });

  // Refresh token: expires in 7 days
  Cookies.set(REFRESH_KEY, tokens.refresh_token, {
    ...COOKIE_OPTIONS,
    expires: 7,
  });

  // Verify tokens were saved
  console.log('[Auth] Tokens saved. Verification:', {
    access_token_saved: !!Cookies.get(TOKEN_KEY),
    refresh_token_saved: !!Cookies.get(REFRESH_KEY),
  });
}

export function clearTokens(): void {
  Cookies.remove(TOKEN_KEY, { path: '/' });
  Cookies.remove(REFRESH_KEY, { path: '/' });
}

// ── Auth API Calls ──────────────────────────────────────────────────

export async function loginUser(email: string, password: string): Promise<User> {
  // 1. Đăng nhập → nhận tokens
  console.log('[Auth] Calling login API...');
  const tokenRes = await api.post<AuthTokens>('/api/v1/auth/login', { email, password });
  console.log('[Auth] Login API response status:', tokenRes.status);
  console.log('[Auth] Login API response data:', tokenRes.data);
  saveTokens(tokenRes.data);

  // 2. Lấy thông tin user
  console.log('[Auth] Fetching current user...');
  const userRes = await api.get<User>('/api/v1/auth/me');
  console.log('[Auth] User data:', userRes.data);
  return userRes.data;
}

export async function registerUser(
  email: string,
  password: string,
  name?: string,
  date_of_birth?: string,
  gender?: string,
): Promise<User> {
  // 1. Đăng ký → nhận user info (chưa có token)
  await api.post('/api/v1/auth/register', { email, password, name, date_of_birth, gender });

  // 2. Tự động đăng nhập sau khi đăng ký
  return loginUser(email, password);
}

export async function googleLoginUser(credential: string): Promise<User> {
  // 1. Gửi Google ID token lên backend → nhận JWT tokens
  console.log('[Auth] Calling Google login API...');
  const tokenRes = await api.post<AuthTokens>('/api/v1/auth/google', { credential });
  console.log('[Auth] Google login response:', tokenRes.data);
  saveTokens(tokenRes.data);

  // 2. Lấy thông tin user
  const userRes = await api.get<User>('/api/v1/auth/me');
  console.log('[Auth] Google user data:', userRes.data);
  return userRes.data;
}

export async function refreshTokens(): Promise<AuthTokens> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error('No refresh token');

  const res = await api.post<AuthTokens>('/api/v1/auth/refresh', {
    refresh_token: refreshToken,
  });
  saveTokens(res.data);
  return res.data;
}

export async function fetchCurrentUser(): Promise<User> {
  const res = await api.get<User>('/api/v1/auth/me');
  return res.data;
}

export async function logoutUser(): Promise<void> {
  try {
    await api.post('/api/v1/auth/logout');
  } catch {
    // Ignore errors - server may be unreachable
  } finally {
    clearTokens();
  }
}
