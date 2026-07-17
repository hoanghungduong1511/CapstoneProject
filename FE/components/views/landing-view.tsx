'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import {
  ChevronRight,
  ChevronLeft,
  ImageIcon,
  ScanSearch,
  MessageSquare,
  Sparkles,
  ShieldCheck,
  Zap,
  Users,
  Award,
  ArrowRight,
  CheckCircle,
} from 'lucide-react';
import { useAppStore } from '@/store/app-store';
import { cn } from '@/lib/utils';

const heroSlides = [
  {
    src: '/images/hero-slide-1.jpg',
    alt: 'Bác sĩ da liễu khám bệnh nhân',
  },
  {
    src: '/images/hero-slide-2.jpg',
    alt: 'Sử dụng kính soi da chuyên dụng',
  },
  {
    src: '/images/hero-slide-3.jpg',
    alt: 'Công nghệ AI phân tích hình ảnh da',
  },
  {
    src: '/images/hero-slide-4.jpg',
    alt: 'Tư vấn kết quả phân tích cho bệnh nhân',
  },
];

const stats = [
  { value: '100+', label: 'Hình ảnh đã phân tích', icon: ScanSearch },
  { value: '85%', label: 'Độ chính xác mô hình', icon: Award },
  { value: '10+', label: 'Loại bệnh da liễu', icon: ShieldCheck },
  { value: '<5s', label: 'Thời gian phản hồi', icon: Zap },
];

const steps = [
  {
    icon: ImageIcon,
    title: 'Cung cấp hình ảnh',
    desc: 'Tải lên hình ảnh rõ nét vùng da cần kiểm tra. Dữ liệu được xử lý trong môi trường mã hóa an toàn.',
    color: 'from-blue-500/20 to-cyan-500/20',
    iconColor: 'text-blue-600 dark:text-blue-400',
    borderColor: 'border-blue-200 dark:border-blue-800',
  },
  {
    icon: ScanSearch,
    title: 'Nhận diện Đa phương thức',
    desc: 'Sử dụng Gemini Vision để trích xuất đặc trưng lâm sàng như màu sắc, viền và tính đối xứng.',
    color: 'from-violet-500/20 to-purple-500/20',
    iconColor: 'text-violet-600 dark:text-violet-400',
    borderColor: 'border-violet-200 dark:border-violet-800',
  },
  {
    icon: MessageSquare,
    title: 'Tư vấn LLM chuyên sâu',
    desc: 'Nhận báo cáo sàng lọc và thảo luận bằng ngôn ngữ tự nhiên với trợ lý ảo y khoa về các bước tiếp theo.',
    color: 'from-emerald-500/20 to-teal-500/20',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    borderColor: 'border-emerald-200 dark:border-emerald-800',
  },
];

const trustPoints = [
  'Bảo mật dữ liệu theo tiêu chuẩn HIPAA',
  'Mô hình AI được huấn luyện bởi chuyên gia',
  'Kết quả trong vài giây, miễn phí hoàn toàn',
  'Hỗ trợ 24/7 với trợ lý ảo thông minh',
];

export function LandingView() {
  const { setView, navigateTo } = useAppStore();
  const [currentSlide, setCurrentSlide] = useState(0);
  const isTransitioningRef = useRef(false);

  const goToSlide = useCallback((index: number) => {
    if (isTransitioningRef.current) return;
    isTransitioningRef.current = true;
    setCurrentSlide(index);
    setTimeout(() => {
      isTransitioningRef.current = false;
    }, 700);
  }, []);

  const nextSlide = useCallback(() => {
    setCurrentSlide((prev) => (prev + 1) % heroSlides.length);
  }, []);

  const prevSlide = useCallback(() => {
    setCurrentSlide((prev) => (prev - 1 + heroSlides.length) % heroSlides.length);
  }, []);

  // Auto-slide every 5 seconds
  useEffect(() => {
    const interval = setInterval(nextSlide, 5000);
    return () => clearInterval(interval);
  }, [nextSlide]);

  return (
    <div className="flex-1 w-full flex flex-col items-center animate-in fade-in duration-500">
      {/* ===== HERO SECTION ===== */}
      <section className="group relative w-full min-h-[86vh] flex items-center justify-center overflow-hidden">
        {/* Carousel Background - Only render current slide to save memory/GPU */}
        <div className="absolute inset-0 z-0">
          <img
            key={currentSlide}
            src={heroSlides[currentSlide].src}
            alt={heroSlides[currentSlide].alt}
            className="w-full h-full object-cover object-center animate-in fade-in duration-700"
            loading="eager"
          />
          {/* Dark overlay for text readability */}
          <div className="absolute inset-0 bg-gradient-to-r from-black/65 via-black/42 to-black/10 z-10" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/28 via-transparent to-black/10 z-10" />
        </div>

        {/* Carousel Navigation Arrows */}
        <button
          onClick={prevSlide}
          className="absolute left-4 md:left-8 top-1/2 -translate-y-1/2 z-20 flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-black/20 opacity-70 transition-all duration-300 hover:bg-black/40 hover:opacity-100 md:opacity-0 md:group-hover:opacity-80"
          aria-label="Ảnh trước"
        >
          <ChevronLeft className="w-4 h-4 text-white transition-transform" />
        </button>
        <button
          onClick={nextSlide}
          className="absolute right-4 md:right-8 top-1/2 -translate-y-1/2 z-20 flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-black/20 opacity-70 transition-all duration-300 hover:bg-black/40 hover:opacity-100 md:opacity-0 md:group-hover:opacity-80"
          aria-label="Ảnh tiếp theo"
        >
          <ChevronRight className="w-4 h-4 text-white transition-transform" />
        </button>

        {/* Carousel Indicators */}
        <div className="absolute bottom-12 left-1/2 z-20 flex -translate-x-1/2 items-center gap-2">
          {heroSlides.map((_, index) => (
            <button
              key={index}
              onClick={() => goToSlide(index)}
              className={cn(
                'h-2 rounded-full transition-all duration-300',
                index === currentSlide
                  ? 'w-8 bg-white'
                  : 'w-2 bg-white/40 hover:bg-white/65'
              )}
              aria-label={`Chuyển đến ảnh ${index + 1}`}
            />
          ))}
        </div>

        {/* Hero Content */}
        <div className="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24 pt-16 flex flex-col items-start text-left">
          <div className="max-w-2xl">
            <div className="inline-flex items-center justify-center px-4 py-2 bg-black/30 text-white rounded-full text-sm font-semibold mb-8 border border-white/20">
              <Sparkles className="w-4 h-4 mr-2 text-blue-300" />
              Công nghệ AI Phân tích Da liễu
            </div>

            <h1
              className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight text-white mb-5 leading-[1.1]"
              style={{ textShadow: '0 2px 20px rgba(0,0,0,0.3)' }}
            >
              Chẩn đoán Da liễu{' '}
              <br className="hidden sm:block" />
              bằng{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-cyan-300">
                AI
              </span>
            </h1>

            <p
              className="text-base sm:text-lg md:text-xl text-white/85 mb-8 leading-relaxed max-w-xl"
              style={{ textShadow: '0 1px 8px rgba(0,0,0,0.2)' }}
            >
              Ứng dụng AI tiên tiến phân tích hình ảnh tổn thương da, trả kết quả nhanh chóng,
              hỗ trợ quyết định y tế chuyên sâu.
            </p>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <button
                onClick={() => navigateTo('upload')}
                className="group relative inline-flex items-center justify-center px-8 py-4 font-bold text-white transition-all duration-300 bg-gradient-to-r from-blue-600 to-blue-500 rounded-xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5 hover:from-blue-500 hover:to-blue-400"
              >
                Bắt đầu chẩn đoán miễn phí
                <ChevronRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
              <button className="px-8 py-4 font-semibold text-white bg-black/30 border border-white/25 hover:bg-black/50 rounded-xl transition-all duration-300 flex items-center justify-center">
                Tìm hiểu thêm
              </button>
            </div>
          </div>
        </div>

        <span className="sr-only">
          Anh {currentSlide + 1} tren {heroSlides.length}
        </span>
      </section>

      {/* ===== STATS SECTION ===== */}
      <section className="w-full relative -mt-10 z-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-0 bg-card rounded-lg shadow-lg border border-border overflow-hidden">
            {stats.map((stat, i) => (
              <div
                key={i}
                className={cn(
                  'flex flex-col items-center justify-center py-6 px-4 text-center transition-colors hover:bg-secondary/50',
                  i % 2 === 0 && 'border-r border-border',
                  i < 2 && 'border-b md:border-b-0 border-border',
                  'md:[&:not(:last-child)]:border-r md:border-r-border'
                )}
              >
                <stat.icon className="w-6 h-6 text-primary mb-3" />
                <p className="text-2xl md:text-3xl font-extrabold text-foreground tracking-tight">
                  {stat.value}
                </p>
                <p className="text-xs md:text-sm text-muted-foreground font-medium mt-1">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== HOW IT WORKS ===== */}
      <section className="w-full py-24 bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center justify-center px-4 py-1.5 bg-primary/10 text-primary rounded-full text-xs font-bold uppercase tracking-wider mb-4">
              Quy trình
            </div>
            <h2 className="text-3xl md:text-4xl font-extrabold text-foreground mb-4 tracking-tight">
              Sàng lọc Y tế chỉ trong 3 bước
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto text-base md:text-lg leading-relaxed">
              Quy trình đơn giản, nhanh chóng – nhận diện các dấu hiệu lâm sàng chỉ trong vài giây.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
            {steps.map((item, i) => (
              <div
                key={i}
                className={cn(
                  'relative bg-card rounded-2xl p-8 border hover:-translate-y-1 hover:shadow-lg transition-all duration-300 flex flex-col text-center items-center group',
                  item.borderColor
                )}
              >
                {/* Step number */}
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-extrabold shadow-md">
                  {i + 1}
                </div>

                <div
                  className={cn(
                    'w-16 h-16 rounded-2xl flex items-center justify-center mb-6 mt-2 bg-gradient-to-br',
                    item.color
                  )}
                >
                  <item.icon className={cn('w-7 h-7', item.iconColor)} />
                </div>

                <h3 className="font-bold text-foreground text-lg mb-3">{item.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== CTA SECTION ===== */}
      <section className="w-full py-24 bg-gradient-to-br from-primary/5 via-background to-accent/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-card rounded-3xl border border-border shadow-sm overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
              {/* Left: Content */}
              <div className="p-8 md:p-12 lg:p-16 flex flex-col justify-center">
                <h2 className="text-3xl md:text-4xl font-extrabold text-foreground mb-6 tracking-tight leading-tight">
                  Sẵn sàng kiểm tra{' '}
                  <span className="text-primary">sức khỏe làn da</span> của bạn?
                </h2>
                <p className="text-muted-foreground text-base md:text-lg mb-8 leading-relaxed">
                  Chỉ cần một bức ảnh, hệ thống AI sẽ phân tích và đưa ra nhận định ban đầu trong vài giây.
                  Hoàn toàn miễn phí, bảo mật tuyệt đối.
                </p>

                <ul className="space-y-3 mb-10">
                  {trustPoints.map((point, i) => (
                    <li key={i} className="flex items-center gap-3 text-sm text-foreground">
                      <CheckCircle className="w-5 h-5 text-emerald-500 shrink-0" />
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>

                <div>
                  <button
                    onClick={() => navigateTo('upload')}
                    className="group inline-flex items-center justify-center px-8 py-4 font-bold text-primary-foreground transition-all duration-300 bg-primary rounded-xl shadow-md hover:bg-primary/90 hover:-translate-y-0.5 hover:shadow-lg"
                  >
                    Phân tích ngay
                    <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>

              {/* Right: Visual */}
              <div className="hidden lg:flex items-center justify-center bg-gradient-to-br from-primary/10 via-primary/5 to-accent/10 p-12 relative overflow-hidden">
                <div className="relative z-10 text-center">
                  <div className="w-32 h-32 mx-auto mb-6 bg-primary/15 rounded-3xl flex items-center justify-center border border-primary/20">
                    <Users className="w-14 h-14 text-primary" />
                  </div>
                  <p className="text-4xl font-extrabold text-foreground mb-2">10,000+</p>
                  <p className="text-muted-foreground font-medium">người dùng đã tin tưởng</p>
                </div>
                {/* Decorative circles */}
                <div className="absolute top-8 right-8 w-32 h-32 bg-primary/5 rounded-full" />
                <div className="absolute bottom-12 left-8 w-20 h-20 bg-accent/10 rounded-full" />
                <div className="absolute top-1/2 right-1/4 w-12 h-12 bg-primary/8 rounded-full" />
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
