'use client';

import { useState } from 'react';
import { User as UserIcon, Loader2 } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';
import { useAppStore } from '@/store/app-store';
import { loginUser, googleLoginUser } from '@/services/auth';

export function LoginView() {
  const { setUser, setView, showToast } = useAppStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  const googleLogin = useGoogleLogin({
    flow: 'implicit',
    onSuccess: async (tokenResponse) => {
      setIsGoogleLoading(true);
      try {
        // Gửi Google access_token lên backend để verify và tạo JWT
        const user = await googleLoginUser(tokenResponse.access_token);
        setUser(user);
        showToast('Đăng nhập bằng Google thành công!', 'success');
        setView(user.role === 'admin' ? 'admin-users' : 'landing');
      } catch (err: any) {
        console.error('[Auth] Google login error:', err);
        const message =
          err?.response?.data?.detail || 'Đăng nhập bằng Google thất bại.';
        showToast(message, 'error');
      } finally {
        setIsGoogleLoading(false);
      }
    },
    onError: (error) => {
      console.error('[Auth] Google OAuth error:', error);
      showToast('Đăng nhập bằng Google thất bại.', 'error');
    },
  });

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const user = await loginUser(email, password);
      setUser(user);
      showToast('Đăng nhập thành công', 'success');
      setView(user.role === 'admin' ? 'admin-users' : 'landing');
    } catch (err: any) {
      const message =
        err?.response?.data?.detail || 'Thông tin đăng nhập không chính xác.';
      showToast(message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 w-full flex items-center justify-center relative py-20 px-4">
      <div className="w-full max-w-md bg-card p-10 rounded-2xl shadow-lg border border-border animate-in fade-in zoom-in-95 duration-300">
        <div className="flex justify-center mb-8">
          <div className="w-14 h-14 bg-primary/10 text-primary rounded-xl flex items-center justify-center border border-primary/20">
            <UserIcon className="w-7 h-7" />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-center text-foreground mb-2">Đăng nhập</h2>
        <p className="text-center text-muted-foreground mb-8 text-sm">
          Truy cập hồ sơ quản lý và lịch sử phân tích.
        </p>

        <form onSubmit={handleLogin} className="flex flex-col gap-6">
          <div>
            <label className="block text-sm font-semibold text-foreground mb-2">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground placeholder-muted-foreground"
              placeholder="email@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-foreground mb-2">Mật khẩu</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground placeholder-muted-foreground"
              placeholder="********"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 bg-foreground hover:bg-foreground/90 text-background rounded-xl font-bold transition-all flex items-center justify-center disabled:opacity-70 shadow-sm"
          >
            {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Đăng nhập'}
          </button>
        </form>

        {/* Register link */}
        <p className="text-center text-sm text-muted-foreground mt-4">
          Chưa có tài khoản?{' '}
          <button
            onClick={() => setView('register')}
            className="text-primary font-semibold hover:underline transition-colors"
          >
            Đăng ký ngay
          </button>
        </p>

        {/* Divider */}
        <div className="flex items-center gap-3 my-6">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">hoặc</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* Google Sign-in */}
        <button
          onClick={() => googleLogin()}
          disabled={isGoogleLoading}
          className="w-full py-3 bg-card hover:bg-secondary border border-border rounded-xl font-semibold transition-all flex items-center justify-center gap-3 text-foreground shadow-sm disabled:opacity-70"
        >
          {isGoogleLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
              Đăng nhập bằng Google
            </>
          )}
        </button>
      </div>
    </div>
  );
}
