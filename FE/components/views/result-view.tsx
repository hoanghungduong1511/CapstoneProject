'use client';

import { useEffect, useState } from 'react';
import {
  AlertCircle,
  Check,
  Eye,
  Flame,
  Layers3,
  MessageSquareText,
  RotateCcw,
  ScanLine,
  Stethoscope,
} from 'lucide-react';
import { useAppStore } from '@/store/app-store';
import type { ClassificationCandidate } from '@/types';

type OverlayMode = 'original' | 'outline' | 'mask' | 'heatmap';

interface OverlayImages {
  outline: string | null;
  mask: string | null;
  heatmap: string | null;
}

const emptyOverlays: OverlayImages = {
  outline: null,
  mask: null,
  heatmap: null,
};

const urgencyConfig = {
  low: {
    label: 'Theo dõi',
    className: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/35 dark:text-emerald-300',
  },
  medium: {
    label: 'Nên thăm khám',
    className: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/35 dark:text-amber-300',
  },
  high: {
    label: 'Cần thăm khám sớm',
    className: 'border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/35 dark:text-red-300',
  },
};

function buildOverlayImages(maskUrl: string): Promise<OverlayImages> {
  return new Promise((resolve) => {
    const image = new Image();
    image.crossOrigin = 'anonymous';
    image.src = maskUrl;

    image.onload = () => {
      const width = image.naturalWidth || image.width;
      const height = image.naturalHeight || image.height;
      const sourceCanvas = document.createElement('canvas');
      const outlineCanvas = document.createElement('canvas');
      const maskCanvas = document.createElement('canvas');
      const heatMaskCanvas = document.createElement('canvas');
      const heatBlurCanvas = document.createElement('canvas');
      const heatmapCanvas = document.createElement('canvas');

      [sourceCanvas, outlineCanvas, maskCanvas, heatMaskCanvas, heatBlurCanvas, heatmapCanvas].forEach((canvas) => {
        canvas.width = width;
        canvas.height = height;
      });

      const sourceContext = sourceCanvas.getContext('2d');
      const outlineContext = outlineCanvas.getContext('2d');
      const maskContext = maskCanvas.getContext('2d');
      const heatMaskContext = heatMaskCanvas.getContext('2d');
      const heatBlurContext = heatBlurCanvas.getContext('2d');
      const heatmapContext = heatmapCanvas.getContext('2d');

      if (!sourceContext || !outlineContext || !maskContext || !heatMaskContext || !heatBlurContext || !heatmapContext) {
        resolve(emptyOverlays);
        return;
      }

      try {
        sourceContext.drawImage(image, 0, 0, width, height);
        const sourceData = sourceContext.getImageData(0, 0, width, height);
        const outlineData = outlineContext.createImageData(width, height);
        const maskData = maskContext.createImageData(width, height);
        const heatMaskData = heatMaskContext.createImageData(width, height);
        const lesion = new Uint8Array(width * height);

        for (let offset = 0; offset < sourceData.data.length; offset += 4) {
          const pixel = offset / 4;
          const luminance =
            sourceData.data[offset] * 0.299 +
            sourceData.data[offset + 1] * 0.587 +
            sourceData.data[offset + 2] * 0.114;
          lesion[pixel] = luminance > 32 ? 1 : 0;

          if (lesion[pixel]) {
            maskData.data[offset] = 239;
            maskData.data[offset + 1] = 68;
            maskData.data[offset + 2] = 68;
            maskData.data[offset + 3] = 82;

            heatMaskData.data[offset] = 255;
            heatMaskData.data[offset + 1] = 255;
            heatMaskData.data[offset + 2] = 255;
            heatMaskData.data[offset + 3] = 255;
          }
        }

        for (let y = 0; y < height; y += 1) {
          for (let x = 0; x < width; x += 1) {
            const pixel = y * width + x;
            if (!lesion[pixel]) continue;

            let edge = false;
            for (let dy = -2; dy <= 2 && !edge; dy += 1) {
              for (let dx = -2; dx <= 2; dx += 1) {
                const nextX = x + dx;
                const nextY = y + dy;
                if (
                  nextX < 0 ||
                  nextY < 0 ||
                  nextX >= width ||
                  nextY >= height ||
                  !lesion[nextY * width + nextX]
                ) {
                  edge = true;
                  break;
                }
              }
            }

            if (edge) {
              const offset = pixel * 4;
              outlineData.data[offset] = 239;
              outlineData.data[offset + 1] = 45;
              outlineData.data[offset + 2] = 45;
              outlineData.data[offset + 3] = 255;

              maskData.data[offset] = 239;
              maskData.data[offset + 1] = 45;
              maskData.data[offset + 2] = 45;
              maskData.data[offset + 3] = 255;
            }
          }
        }

        outlineContext.putImageData(outlineData, 0, 0);
        maskContext.putImageData(maskData, 0, 0);
        heatMaskContext.putImageData(heatMaskData, 0, 0);

        const blurRadius = Math.max(12, Math.round(Math.min(width, height) * 0.045));
        heatBlurContext.filter = `blur(${blurRadius}px)`;
        heatBlurContext.drawImage(heatMaskCanvas, 0, 0);
        heatBlurContext.filter = 'none';

        const blurred = heatBlurContext.getImageData(0, 0, width, height);
        const heatmapData = heatmapContext.createImageData(width, height);

        for (let offset = 0; offset < heatmapData.data.length; offset += 4) {
          const pixel = offset / 4;
          const glow = blurred.data[offset + 3] / 255;
          const intensity = lesion[pixel] ? 1 : glow;

          if (intensity < 0.06) continue;

          if (intensity > 0.82) {
            heatmapData.data[offset] = 239;
            heatmapData.data[offset + 1] = 35;
            heatmapData.data[offset + 2] = 35;
            heatmapData.data[offset + 3] = 175;
          } else if (intensity > 0.52) {
            heatmapData.data[offset] = 249;
            heatmapData.data[offset + 1] = 115;
            heatmapData.data[offset + 2] = 22;
            heatmapData.data[offset + 3] = 145;
          } else if (intensity > 0.24) {
            heatmapData.data[offset] = 250;
            heatmapData.data[offset + 1] = 204;
            heatmapData.data[offset + 2] = 21;
            heatmapData.data[offset + 3] = 110;
          } else {
            heatmapData.data[offset] = 14;
            heatmapData.data[offset + 1] = 165;
            heatmapData.data[offset + 2] = 233;
            heatmapData.data[offset + 3] = 70;
          }
        }

        heatmapContext.putImageData(heatmapData, 0, 0);
        resolve({
          outline: outlineCanvas.toDataURL('image/png'),
          mask: maskCanvas.toDataURL('image/png'),
          heatmap: heatmapCanvas.toDataURL('image/png'),
        });
      } catch {
        resolve(emptyOverlays);
      }
    };

    image.onerror = () => resolve(emptyOverlays);
  });
}

export function ResultView() {
  const { image, result, resetAnalysis, openChatForResult } = useAppStore();
  const [overlayMode, setOverlayMode] = useState<OverlayMode>('outline');
  const [overlays, setOverlays] = useState<OverlayImages>(emptyOverlays);
  const [selectedCandidate, setSelectedCandidate] = useState(0);

  const maskUrl = result?.segmentation?.mask_url;
  const roiUrl = result?.segmentation?.roi_url;

  useEffect(() => {
    if (!maskUrl) {
      setOverlays(emptyOverlays);
      setOverlayMode('original');
      return;
    }

    let cancelled = false;
    buildOverlayImages(maskUrl).then((generated) => {
      if (!cancelled) setOverlays(generated);
    });

    return () => {
      cancelled = true;
    };
  }, [maskUrl]);

  if (!result) return null;

  const classification = result.classification;
  const candidates = classification?.candidates ?? [];
  const activeCandidate = candidates[selectedCandidate] ?? candidates[0];
  const topCandidate = candidates[0];
  const topUrgency =
    urgencyConfig[(topCandidate?.urgency ?? 'low') as keyof typeof urgencyConfig] ??
    urgencyConfig.low;

  const overlayUrl =
    overlayMode === 'outline'
      ? overlays.outline
      : overlayMode === 'mask'
        ? overlays.mask
        : overlayMode === 'heatmap'
          ? overlays.heatmap
          : null;

  const imageModes: Array<{ id: OverlayMode; label: string; icon: typeof Eye }> = [
    { id: 'original', label: 'Gốc', icon: Eye },
    { id: 'outline', label: 'Viền', icon: ScanLine },
    { id: 'mask', label: 'Mask', icon: Layers3 },
    { id: 'heatmap', label: 'Heatmap', icon: Flame },
  ];

  return (
    <>
      <div className="mx-auto w-full max-w-7xl flex-1 px-4 py-7">
        <div className="mb-5 animate-[result-rise_.45s_ease-out]">
          <div className="flex items-center gap-2 text-sm font-semibold text-primary">
            <Check className="h-4 w-4" />
            Phân tích hoàn tất
          </div>
          <h1 className="mt-1 text-2xl font-bold text-foreground">Kết quả phân tích hình ảnh</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Quan sát vùng được phát hiện và các dự đoán chính xác nhất.
          </p>
        </div>

        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.08fr)_minmax(390px,0.92fr)]">
          <section className="animate-[result-rise_.5s_ease-out] overflow-hidden rounded-lg border border-border bg-card shadow-sm">
            <header className="flex flex-col gap-3 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="font-bold text-foreground">Hình ảnh phân tích</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Chuyển chế độ để quan sát vùng hệ thống đã nhận diện
                </p>
              </div>

              <div className="grid grid-cols-4 rounded-md border border-border bg-secondary p-1">
                {imageModes.map((mode) => {
                  const Icon = mode.icon;
                  const disabled = mode.id !== 'original' && !maskUrl;
                  return (
                    <button
                      key={mode.id}
                      type="button"
                      disabled={disabled}
                      onClick={() => setOverlayMode(mode.id)}
                      title={mode.id === 'heatmap' ? 'Heatmap vùng hệ thống chú ý' : mode.label}
                      className={`flex h-9 items-center justify-center gap-1.5 rounded px-2 text-xs font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-35 ${
                        overlayMode === mode.id
                          ? 'bg-card text-primary shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">{mode.label}</span>
                    </button>
                  );
                })}
              </div>
            </header>

            <div className="relative aspect-[4/3] min-h-[390px] overflow-hidden bg-[oklch(0.13_0.01_215)]">
              <img
                src={image || result.original_image_url}
                alt="Ảnh vùng da được phân tích"
                className="absolute inset-0 h-full w-full object-contain"
              />

              {overlayUrl && (
                <img
                  key={overlayMode}
                  src={overlayUrl}
                  alt={`Lớp hiển thị ${overlayMode}`}
                  className={`absolute inset-0 h-full w-full animate-[overlay-fade_.3s_ease-out] object-contain ${
                    overlayMode === 'outline'
                      ? 'drop-shadow-[0_0_5px_rgba(239,45,45,0.75)]'
                      : ''
                  }`}
                />
              )}

              <div className="absolute bottom-3 left-3 rounded-md border border-white/20 bg-black/55 px-3 py-2 text-xs font-medium text-white backdrop-blur">
                {overlayMode === 'original' && 'Ảnh gốc'}
                {overlayMode === 'outline' && 'Viền vùng được phát hiện'}
                {overlayMode === 'mask' && 'Mask vùng được phát hiện'}
                {overlayMode === 'heatmap' && 'Heatmap vùng chú ý'}
              </div>
            </div>

            {roiUrl && (
              <div className="border-t border-border bg-card px-5 py-4">
                <div className="grid gap-4 sm:grid-cols-[180px_minmax(0,1fr)] sm:items-center">
                  <div className="overflow-hidden rounded-md border border-border bg-secondary">
                    <div className="relative aspect-[4/3]">
                      <img
                        src={roiUrl}
                        alt="Ảnh crop ROI vùng tổn thương"
                        className="absolute inset-0 h-full w-full object-contain"
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 text-sm font-bold text-foreground">
                      <ScanLine className="h-4 w-4 text-primary" />
                      ROI vùng tổn thương
                    </div>
                    {result.segmentation?.bbox?.length === 4 && (
                      <div className="mt-3 grid grid-cols-4 gap-2 text-center text-[11px]">
                        {['x1', 'y1', 'x2', 'y2'].map((label, index) => (
                          <div key={label} className="rounded border border-border bg-secondary px-2 py-1.5">
                            <span className="block font-semibold text-muted-foreground">{label}</span>
                            <span className="font-bold text-foreground">
                              {Math.round(result.segmentation?.bbox[index] ?? 0)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>

          <section className="animate-[result-rise_.55s_ease-out] overflow-hidden rounded-lg border border-border bg-card shadow-sm">
            {!classification || !topCandidate ? (
              <div className="flex min-h-[520px] flex-col items-center justify-center px-8 text-center">
                <AlertCircle className="h-9 w-9 text-amber-600" />
                <h2 className="mt-4 text-lg font-bold text-foreground">Chưa có kết quả phân loại</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Hệ thống đã xử lý hình ảnh nhưng chưa nhận được danh sách dự đoán.
                </p>
              </div>
            ) : (
              <>
                <div className="border-b border-border p-5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase text-primary">
                    <Stethoscope className="h-4 w-4" />
                    Dự đoán chính xác nhất
                  </div>

                  <div className="mt-3 flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h2 className="text-2xl font-bold text-foreground">{topCandidate.name}</h2>
                      <p className="mt-1 text-xs italic text-muted-foreground">
                        {topCandidate.latinName} · {topCandidate.icd}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-3xl font-black text-primary">
                        {topCandidate.confidence.toFixed(1)}%
                      </p>
                      <p className="text-[10px] text-muted-foreground">độ chính xác</p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-start gap-2">
                    <span className={`shrink-0 rounded border px-2 py-1 text-[11px] font-semibold ${topUrgency.className}`}>
                      {topUrgency.label}
                    </span>
                    <p className="text-xs leading-5 text-muted-foreground">{topCandidate.recommendation}</p>
                  </div>
                </div>

                <div className="p-5">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-foreground">Các dự đoán được đề xuất</h3>
                    <span className="text-xs text-muted-foreground">Top {candidates.length}</span>
                  </div>

                  <div className="mt-3 divide-y divide-border">
                    {candidates.map((candidate, index) => (
                      <button
                        key={candidate.id}
                        type="button"
                        onClick={() => setSelectedCandidate(index)}
                        className={`result-candidate-row w-full py-3 text-left transition-colors ${
                          selectedCandidate === index ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
                        }`}
                        style={{ animationDelay: `${index * 60}ms` }}
                      >
                        <div className="flex items-center gap-3">
                          <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded text-xs font-bold ${
                            selectedCandidate === index
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-secondary text-muted-foreground'
                          }`}>
                            {index + 1}
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-3">
                              <span className="truncate text-sm font-semibold">{candidate.name}</span>
                              <span className="shrink-0 text-sm font-bold text-foreground">
                                {candidate.confidence.toFixed(1)}%
                              </span>
                            </div>
                            <div className="mt-2 h-1 overflow-hidden rounded-full bg-secondary">
                              <div
                                className="h-full rounded-full bg-primary transition-[width] duration-700"
                                style={{ width: `${Math.max(candidate.confidence, 2)}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>

                  {activeCandidate && (
                    <div key={activeCandidate.id} className="mt-3 animate-[overlay-fade_.25s_ease-out] border-t border-border pt-4">
                      <p className="text-sm leading-6 text-muted-foreground">{activeCandidate.description}</p>
                      <p className="mt-2 text-xs font-medium leading-5 text-foreground">
                        {activeCandidate.recommendation}
                      </p>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3 border-t border-border p-5">
                  <button
                    type="button"
                    onClick={resetAnalysis}
                    className="flex h-11 items-center justify-center gap-2 rounded-md border border-border text-sm font-semibold text-foreground transition-colors hover:bg-secondary"
                  >
                    <RotateCcw className="h-4 w-4" />
                    Ảnh khác
                  </button>
                  <button
                    type="button"
                    onClick={() => openChatForResult(result.ai_result_id)}
                    className="flex h-11 items-center justify-center gap-2 rounded-md bg-primary text-sm font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 hover:shadow-md"
                  >
                    <MessageSquareText className="h-4 w-4" />
                    Tư vấn AI
                  </button>
                </div>
              </>
            )}
          </section>
        </div>

        <div className="mx-auto mt-5 flex max-w-3xl items-start justify-center gap-2 text-center">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <p className="text-[11px] leading-5 text-muted-foreground">
            Kết quả chỉ hỗ trợ tham khảo và không thay thế chẩn đoán trực tiếp của bác sĩ da liễu.
          </p>
        </div>
      </div>

    </>
  );
}
