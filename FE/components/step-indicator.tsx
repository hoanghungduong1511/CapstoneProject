'use client';

import { Check, FileSearch, ImageUp, Stethoscope } from 'lucide-react';
import { useAppStore } from '@/store/app-store';
import type { ViewState } from '@/types';

const stepIndex: Partial<Record<ViewState, number>> = {
  upload: 0,
  validating: 1,
  analyzing: 2,
  result: 2,
};

export function StepIndicator() {
  const { view } = useAppStore();
  const currentIndex = stepIndex[view];

  if (currentIndex === undefined) return null;

  const steps = [
    { label: 'Tải ảnh', icon: ImageUp },
    { label: 'Kiểm tra ảnh', icon: FileSearch },
    {
      label: view === 'result' ? 'Kết quả' : 'Phân tích',
      icon: Stethoscope,
    },
  ];

  return (
    <div className="mx-auto w-full max-w-3xl px-5 pb-1 pt-8">
      <div className="relative flex items-start justify-between">
        <div className="absolute left-[16.67%] right-[16.67%] top-5 h-px bg-border" />
        <div
          className="absolute left-[16.67%] top-5 h-px bg-primary transition-[width] duration-700 ease-out"
          style={{ width: `${currentIndex * 33.33}%` }}
        />

        {steps.map((step, index) => {
          const Icon = step.icon;
          const isDone = index < currentIndex;
          const isActive = index === currentIndex;

          return (
            <div key={step.label} className="relative z-10 flex w-1/3 flex-col items-center">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full border transition-all duration-500 ${
                  isDone
                    ? 'border-emerald-600 bg-emerald-600 text-white'
                    : isActive
                      ? 'border-primary bg-primary text-primary-foreground shadow-[0_0_0_6px_color-mix(in_oklab,var(--primary)_12%,transparent)]'
                      : 'border-border bg-card text-muted-foreground'
                }`}
              >
                {isDone ? <Check className="h-4 w-4" strokeWidth={2.5} /> : <Icon className="h-4 w-4" />}
              </div>
              <span
                className={`mt-2 text-xs font-semibold ${
                  isDone || isActive ? 'text-foreground' : 'text-muted-foreground'
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
