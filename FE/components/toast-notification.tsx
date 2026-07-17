'use client';

import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAppStore } from '@/store/app-store';

export function ToastNotification() {
  const { toast } = useAppStore();

  if (!toast) return null;

  return (
    <div
      className={`fixed bottom-6 right-6 p-4 rounded-xl shadow-lg flex items-center gap-3 animate-in slide-in-from-bottom-5 z-50 min-w-[300px] border ${
        toast.type === 'error'
          ? 'bg-destructive/10 text-destructive border-destructive/30'
          : 'bg-success/10 text-success border-success/30'
      }`}
    >
      {toast.type === 'error' ? (
        <AlertCircle className="w-5 h-5 text-destructive" />
      ) : (
        <CheckCircle2 className="w-5 h-5 text-success" />
      )}
      <span className="font-semibold text-sm">{toast.message}</span>
    </div>
  );
}
