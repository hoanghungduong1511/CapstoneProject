'use client';

import { useRef, useState } from 'react';
import { ArrowRight, FileImage, Info, UploadCloud, X } from 'lucide-react';
import { useAppStore } from '@/store/app-store';

async function getFileSha256(file: File): Promise<string | null> {
  if (!globalThis.crypto?.subtle) return null;
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

export function UploadView() {
  const { image, setImage, setImageFile, setImageHash, setView, showToast } = useAppStore();
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      showToast('Vui lòng tải lên tệp hình ảnh hợp lệ.', 'error');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showToast('File quá lớn. Vui lòng chọn ảnh nhỏ hơn 10MB.', 'error');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      setImage(e.target?.result as string);
      setImageFile(file);
    };
    reader.readAsDataURL(file);
    setImageHash(null);
    getFileSha256(file)
      .then(setImageHash)
      .catch(() => setImageHash(null));
  };

  const handleStartValidation = () => {
    if (!image) return;
    setView('validating');
  };

  return (
    <div className="flex-1 w-full max-w-3xl mx-auto py-10 px-4 animate-in fade-in duration-300">
      <div className="bg-card rounded-2xl shadow-md border border-border overflow-hidden">
        {/* Header */}
        <div className="px-8 pt-8 pb-6 border-b border-border">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <FileImage className="w-5 h-5 text-primary" />
            </div>
            <h2 className="text-xl font-bold text-foreground">Tải ảnh lâm sàng</h2>
          </div>
          <p className="text-muted-foreground text-sm ml-12">
            Ảnh sẽ được kiểm tra qua 3 bước AI trước khi hiển thị kết quả.
          </p>
        </div>

        <div className="p-8">
          {!image ? (
            <>
              {/* Drop zone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
                }}
                onClick={() => fileInputRef.current?.click()}
                className={`relative flex flex-col items-center justify-center w-full h-[280px] border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-200 ${
                  isDragging
                    ? 'border-primary bg-primary/5 scale-[1.01]'
                    : 'border-border hover:border-primary/50 bg-secondary/50 hover:bg-secondary'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={(e) => e.target.files && handleFile(e.target.files[0])}
                  accept="image/*"
                  className="hidden"
                />
                <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 transition-all ${isDragging ? 'bg-primary/20 text-primary' : 'bg-card text-muted-foreground border border-border'}`}>
                  <UploadCloud className="w-8 h-8" />
                </div>
                <p className="text-foreground font-bold text-sm mb-1">
                  {isDragging ? 'Thả ảnh vào đây...' : 'Kéo & thả ảnh vào đây'}
                </p>
                <p className="text-muted-foreground text-xs">hoặc click để chọn file</p>
                <p className="text-muted-foreground text-xs mt-1">PNG, JPG, WebP — tối đa 10MB</p>
              </div>

              {/* Pipeline info */}
              <div className="mt-6 bg-primary/5 border border-primary/15 rounded-xl p-4">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                  <div className="text-xs text-muted-foreground space-y-1">
                    <p className="font-semibold text-foreground">Quy trình phân tích 3 bước AI:</p>
                    <p>① Kiểm tra da người → ② Khoanh vùng tổn thương → ③ Phân loại &amp; Chẩn đoán</p>
                    <p>Mỗi bước bạn có thể xem kết quả trước khi tiếp tục.</p>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col gap-5">
              {/* Preview */}
              <div className="relative rounded-2xl overflow-hidden bg-secondary h-[380px] flex items-center justify-center border border-border">
                <img src={image} alt="Bản xem trước" className="max-w-full max-h-full object-contain rounded-xl" />
                <button
                  onClick={() => { setImage(null); setImageFile(null); setImageHash(null); }}
                  className="absolute top-3 right-3 bg-card/90 hover:bg-destructive hover:text-white text-muted-foreground p-2 rounded-full shadow-md border border-border transition-all backdrop-blur-sm"
                >
                  <X className="w-4 h-4" />
                </button>
                <div className="absolute bottom-3 left-3 bg-card/90 backdrop-blur px-3 py-1.5 rounded-lg border border-border text-xs text-foreground font-medium">
                  ✓ Ảnh đã sẵn sàng
                </div>
              </div>

              {/* Action */}
              <button
                onClick={handleStartValidation}
                className="w-full py-4 bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl font-bold transition-all flex items-center justify-center gap-2 shadow-md hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
              >
                <span>Bắt đầu kiểm tra</span>
                <ArrowRight className="w-5 h-5" />
              </button>
              <p className="text-center text-xs text-muted-foreground -mt-2">
                Bước tiếp theo: Kiểm tra ảnh có phải da người
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
