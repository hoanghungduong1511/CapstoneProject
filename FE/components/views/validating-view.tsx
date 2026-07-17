'use client';

import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  LoaderCircle,
  RotateCcw,
  ShieldCheck,
  X,
} from 'lucide-react';
import { useAppStore } from '@/store/app-store';
import { validateSkinImage } from '@/services/api';
import type { ValidationResult } from '@/types';

type Status = 'loading' | 'passed' | 'failed' | 'error';

export function ValidatingView() {
  const { image, imageFile, setView, showToast } = useAppStore();
  const [status, setStatus] = useState<Status>('loading');
  const [validation, setValidation] = useState<ValidationResult | null>(null);

  useEffect(() => {
    if (!imageFile) {
      setView('upload');
      return;
    }

    let cancelled = false;

    validateSkinImage(imageFile)
      .then((data) => {
        if (cancelled) return;
        setValidation(data);
        setStatus(data.is_skin && data.confidence >= 0.65 ? 'passed' : 'failed');
      })
      .catch(() => {
        if (!cancelled) setStatus('error');
      });

    return () => {
      cancelled = true;
    };
  }, [imageFile, setView]);

  const confidence = Math.round((validation?.confidence ?? 0) * 100);
  const passed = status === 'passed';

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 items-start px-4 py-8">
      <section className="w-full overflow-hidden rounded-lg border border-border bg-card shadow-sm">
        <header className="flex items-center gap-3 border-b border-border px-6 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-foreground">Kiểm tra chất lượng ảnh</h1>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Xác nhận ảnh phù hợp trước khi bắt đầu phân tích
            </p>
          </div>
        </header>

        <div className="grid gap-6 p-6 md:grid-cols-[1.05fr_0.95fr] md:p-8">
          <div className="relative aspect-[4/3] overflow-hidden rounded-md bg-secondary">
            {image && <img src={image} alt="Ảnh cần kiểm tra" className="h-full w-full object-contain" />}

            {status === 'loading' && (
              <>
                <div className="absolute inset-0 bg-background/35 backdrop-blur-[1px]" />
                <div className="medical-scan-line absolute inset-x-0 h-px bg-primary shadow-[0_0_18px_4px_color-mix(in_oklab,var(--primary)_45%,transparent)]" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-card/90 shadow-lg">
                    <LoaderCircle className="h-7 w-7 animate-spin text-primary" />
                  </div>
                </div>
              </>
            )}

            {(status === 'passed' || status === 'failed') && (
              <div className={`absolute inset-0 flex items-center justify-center ${passed ? 'bg-emerald-600/10' : 'bg-red-600/10'}`}>
                <div className={`flex h-14 w-14 animate-[result-pop_.45s_ease-out] items-center justify-center rounded-full text-white shadow-lg ${passed ? 'bg-emerald-600' : 'bg-red-600'}`}>
                  {passed ? <Check className="h-7 w-7" /> : <X className="h-7 w-7" />}
                </div>
              </div>
            )}
          </div>

          <div className="flex min-h-64 flex-col justify-center">
            {status === 'loading' && (
              <div>
                <p className="text-sm font-semibold text-foreground">Đang kiểm tra ảnh...</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Hệ thống đang đánh giá vùng da và chất lượng hình ảnh.
                </p>
                <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-secondary">
                  <div className="h-full w-2/3 animate-pulse rounded-full bg-primary" />
                </div>
              </div>
            )}

            {(status === 'passed' || status === 'failed') && validation && (
              <div className="animate-[result-rise_.45s_ease-out]">
                <div className={`flex items-start gap-3 rounded-md border p-4 ${passed ? 'border-emerald-200 bg-emerald-50/70 dark:border-emerald-900 dark:bg-emerald-950/25' : 'border-red-200 bg-red-50/70 dark:border-red-900 dark:bg-red-950/25'}`}>
                  <div className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white ${passed ? 'bg-emerald-600' : 'bg-red-600'}`}>
                    {passed ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
                  </div>
                  <div>
                    <p className="font-bold text-foreground">
                      {passed ? 'Ảnh phù hợp để phân tích' : 'Ảnh chưa phù hợp'}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      {passed
                        ? 'Đã nhận diện được vùng da người rõ ràng.'
                        : 'Vui lòng dùng ảnh chụp trực tiếp vùng da, đủ sáng và rõ nét.'}
                    </p>
                  </div>
                </div>

                <div className="mt-6">
                  <div className="flex items-end justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Độ chính xác</span>
                    <span className={`text-3xl font-black ${passed ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'}`}>
                      {confidence}%
                    </span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-secondary">
                    <div
                      className={`h-full rounded-full transition-[width] duration-1000 ${passed ? 'bg-emerald-600' : 'bg-red-600'}`}
                      style={{ width: `${confidence}%` }}
                    />
                  </div>
                </div>
              </div>
            )}

            {status === 'error' && (
              <div className="rounded-md border border-amber-200 bg-amber-50/70 p-4 dark:border-amber-900 dark:bg-amber-950/25">
                <AlertTriangle className="h-5 w-5 text-amber-700" />
                <p className="mt-3 font-bold text-foreground">Không thể kiểm tra ảnh</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Kết nối đến dịch vụ phân tích bị gián đoạn. Vui lòng thử lại.
                </p>
              </div>
            )}
          </div>
        </div>

        {status !== 'loading' && (
          <footer className="flex gap-3 border-t border-border px-6 py-4">
            <button
              type="button"
              onClick={() => setView('upload')}
              className="flex h-11 flex-1 items-center justify-center gap-2 rounded-md border border-border bg-card text-sm font-semibold text-foreground transition-colors hover:bg-secondary"
            >
              <ArrowLeft className="h-4 w-4" />
              Chọn ảnh khác
            </button>

            {passed ? (
              <button
                type="button"
                onClick={() => {
                  showToast('Ảnh hợp lệ. Bắt đầu phân tích.', 'success');
                  setView('analyzing');
                }}
                className="flex h-11 flex-[1.6] items-center justify-center gap-2 rounded-md bg-primary text-sm font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 hover:shadow-md"
              >
                Phân tích hình ảnh
                <ArrowRight className="h-4 w-4" />
              </button>
            ) : status === 'error' ? (
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="flex h-11 flex-[1.6] items-center justify-center gap-2 rounded-md bg-primary text-sm font-bold text-primary-foreground"
              >
                <RotateCcw className="h-4 w-4" />
                Thử lại
              </button>
            ) : null}
          </footer>
        )}
      </section>
    </div>
  );
}
