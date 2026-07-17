'use client';

import { useEffect, useState } from 'react';
import { Check, Circle, LoaderCircle, ScanLine, XCircle } from 'lucide-react';
import { analyzeImage } from '@/services/api';
import { useAppStore } from '@/store/app-store';

const phases = [
  'Xác định vùng cần quan sát',
  'Phân tích đặc điểm hình ảnh',
  'Tổng hợp các dự đoán chính xác',
];

export function AnalyzingView() {
  const { image, imageFile, setResult, setView, showToast } = useAppStore();
  const [activePhase, setActivePhase] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!imageFile) {
      setView('upload');
      return;
    }

    let cancelled = false;
    const phaseTimer = window.setInterval(() => {
      setActivePhase((current) => Math.min(current + 1, phases.length - 1));
    }, 700);

    analyzeImage(imageFile)
      .then((data) => {
        if (cancelled) return;
        setActivePhase(phases.length);
        setResult(data);
        window.setTimeout(() => {
          if (!cancelled) setView('result');
        }, 650);
      })
      .catch(() => {
        if (cancelled) return;
        setFailed(true);
        showToast('Không thể hoàn tất phân tích. Vui lòng thử lại.', 'error');
      })
      .finally(() => window.clearInterval(phaseTimer));

    return () => {
      cancelled = true;
      window.clearInterval(phaseTimer);
    };
  }, [imageFile, setResult, setView, showToast]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 items-start px-4 py-8">
      <section className="w-full overflow-hidden rounded-lg border border-border bg-card shadow-sm">
        <div className="grid min-h-[430px] md:grid-cols-[1.05fr_0.95fr]">
          <div className="relative min-h-72 overflow-hidden bg-secondary">
            {image && <img src={image} alt="Ảnh đang phân tích" className="absolute inset-0 h-full w-full object-contain" />}
            <div className="absolute inset-0 bg-background/20" />
            {!failed && (
              <>
                <div className="medical-scan-line absolute inset-x-0 h-px bg-primary shadow-[0_0_20px_5px_color-mix(in_oklab,var(--primary)_45%,transparent)]" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/60 bg-card/90 shadow-xl backdrop-blur">
                    <ScanLine className="h-7 w-7 animate-pulse text-primary" />
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="flex flex-col justify-center p-7 md:p-9">
            {failed ? (
              <div className="text-center md:text-left">
                <XCircle className="mx-auto h-9 w-9 text-destructive md:mx-0" />
                <h1 className="mt-4 text-xl font-bold text-foreground">Phân tích chưa hoàn tất</h1>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Dịch vụ đang tạm thời gián đoạn. Bạn có thể quay lại và thử với ảnh khác.
                </p>
                <button
                  type="button"
                  onClick={() => setView('upload')}
                  className="mt-6 h-11 w-full rounded-md bg-primary text-sm font-bold text-primary-foreground"
                >
                  Quay lại tải ảnh
                </button>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3">
                  <LoaderCircle className="h-6 w-6 animate-spin text-primary" />
                  <div>
                    <h1 className="text-xl font-bold text-foreground">Đang phân tích hình ảnh</h1>
                    <p className="mt-1 text-xs text-muted-foreground">Vui lòng giữ trang này trong giây lát</p>
                  </div>
                </div>

                <div className="mt-8 space-y-5">
                  {phases.map((phase, index) => {
                    const done = index < activePhase;
                    const active = index === activePhase;

                    return (
                      <div
                        key={phase}
                        className="flex items-center gap-3 transition-all duration-500"
                        style={{ opacity: index <= activePhase ? 1 : 0.45 }}
                      >
                        <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border ${
                          done
                            ? 'border-emerald-600 bg-emerald-600 text-white'
                            : active
                              ? 'border-primary bg-primary/10 text-primary'
                              : 'border-border text-muted-foreground'
                        }`}>
                          {done ? <Check className="h-3.5 w-3.5" /> : active ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Circle className="h-2.5 w-2.5" />}
                        </div>
                        <span className={`text-sm ${done || active ? 'font-semibold text-foreground' : 'text-muted-foreground'}`}>
                          {phase}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
