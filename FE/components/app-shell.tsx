'use client';

import { useEffect, useRef, useState } from 'react';
import type { ViewState } from '@/types';
import { useAppStore } from '@/store/app-store';
import { pathToView } from '@/lib/routes';
import { StepIndicator } from '@/components/step-indicator';
import { Footer } from '@/components/footer';
import { ToastNotification } from '@/components/toast-notification';
import { LandingView } from '@/components/views/landing-view';
import { LoginView } from '@/components/views/login-view';
import { RegisterView } from '@/components/views/register-view';
import { UploadView } from '@/components/views/upload-view';
import { ValidatingView } from '@/components/views/validating-view';
import { AnalyzingView } from '@/components/views/analyzing-view';
import { ResultView } from '@/components/views/result-view';
import { ProfileView } from '@/components/views/profile-view';
import { AdminUsersView } from '@/components/views/admin-users-view';
import { ChatWidget } from '@/components/chat-widget';
import { fetchCurrentUser, clearTokens, getAccessToken } from '@/services/auth';

const PROTECTED_VIEWS = ['upload', 'validating', 'analyzing', 'result', 'profile', 'admin-users'] as const;

interface AppShellProps {
  initialView: ViewState;
}

export function AppShell({ initialView }: AppShellProps) {
  const { view, setUser, setView, syncViewFromRoute, user, showToast } = useAppStore();
  const hasRedirectedRef = useRef(false);
  const hasSyncedInitialRouteRef = useRef(false);
  const [isSessionReady, setIsSessionReady] = useState(false);

  useEffect(() => {
    if (hasSyncedInitialRouteRef.current) return;
    hasSyncedInitialRouteRef.current = true;
    syncViewFromRoute(initialView);
  }, [initialView, syncViewFromRoute]);

  useEffect(() => {
    const handlePopState = () => {
      syncViewFromRoute(pathToView(window.location.pathname));
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [syncViewFromRoute]);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setIsSessionReady(true);
      return;
    }

    fetchCurrentUser()
      .then((currentUser) => {
        setUser(currentUser);
        if (currentUser.role === 'admin') {
          setView('admin-users');
        }
      })
      .catch(() => {
        clearTokens();
        setUser(null);
      })
      .finally(() => setIsSessionReady(true));
  }, [setUser, setView]);

  useEffect(() => {
    if (user?.role === 'admin' && view !== 'admin-users') {
      setView('admin-users');
    } else if (user && user.role !== 'admin' && view === 'admin-users') {
      setView('landing');
      showToast('Bạn không có quyền truy cập trang quản trị.', 'error');
    }
  }, [user, view, setView, showToast]);

  useEffect(() => {
    if (!isSessionReady) return;

    if (!user && PROTECTED_VIEWS.includes(view as any)) {
      if (!hasRedirectedRef.current) {
        hasRedirectedRef.current = true;
        setView('login');
        showToast('Vui lòng đăng nhập để sử dụng tính năng này.', 'error');
      }
    } else {
      hasRedirectedRef.current = false;
    }
  }, [view, user, isSessionReady, setView, showToast]);

  useEffect(() => {
    const handleLogout = () => {
      setUser(null);
      setView('login');
      showToast('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error');
    };

    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, [setUser, setView, showToast]);

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground font-sans">
      <main className="flex-1 w-full flex flex-col items-center relative">
        <StepIndicator />

        {view === 'landing' && <LandingView />}
        {view === 'login' && <LoginView />}
        {view === 'register' && <RegisterView />}
        {view === 'upload' && <UploadView />}
        {view === 'validating' && <ValidatingView />}
        {view === 'analyzing' && <AnalyzingView />}
        {view === 'result' && <ResultView />}
        {view === 'profile' && <ProfileView />}
        {view === 'admin-users' && <AdminUsersView />}
      </main>

      {view !== 'admin-users' && <Footer />}
      <ChatWidget />
      <ToastNotification />
    </div>
  );
}
