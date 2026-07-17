'use client';

import { useState } from 'react';
import { format } from 'date-fns';
import { UserPlus, Loader2 } from 'lucide-react';
import { useAppStore } from '@/store/app-store';
import { registerUser } from '@/services/auth';
import { DatePicker } from '@/components/ui/date-picker';

export function RegisterView() {
  const { setUser, setView, showToast } = useAppStore();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState<Date | undefined>(undefined);
  const [gender, setGender] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      showToast('Mật khẩu xác nhận không khớp', 'error');
      return;
    }

    if (password.length < 6) {
      showToast('Mật khẩu phải có ít nhất 6 ký tự', 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      const user = await registerUser(
        email,
        password,
        name || undefined,
        dateOfBirth ? format(dateOfBirth, 'yyyy-MM-dd') : undefined,
        gender || undefined,
      );
      setUser(user);
      showToast('Đăng ký thành công! Chào mừng bạn đến SkinAI.', 'success');
      setView('landing');
    } catch (err: any) {
      const message =
        err?.response?.data?.detail || 'Đăng ký thất bại. Vui lòng thử lại.';
      showToast(message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 w-full flex items-center justify-center relative py-20 px-4">
      <div className="w-full max-w-lg bg-card p-10 rounded-2xl shadow-lg border border-border animate-in fade-in zoom-in-95 duration-300">
        <div className="flex justify-center mb-8">
          <div className="w-14 h-14 bg-emerald-500/10 text-emerald-600 rounded-xl flex items-center justify-center border border-emerald-500/20">
            <UserPlus className="w-7 h-7" />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-center text-foreground mb-2">Tạo tài khoản</h2>
        <p className="text-center text-muted-foreground mb-8 text-sm">
          Đăng ký để sử dụng đầy đủ tính năng SkinAI.
        </p>

        <form onSubmit={handleRegister} className="flex flex-col gap-5">
          <div>
            <label className="block text-sm font-semibold text-foreground mb-2">Họ và tên</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground placeholder-muted-foreground"
              placeholder="Nguyễn Văn A"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-foreground mb-2">
              Email <span className="text-destructive">*</span>
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground placeholder-muted-foreground"
              placeholder="email@example.com"
            />
          </div>

          {/* Date of Birth & Gender row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-foreground mb-2">Ngày sinh</label>
              <DatePicker
                value={dateOfBirth}
                onChange={setDateOfBirth}
                placeholder="dd/mm/yyyy"
                maxDate={new Date()}
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-foreground mb-2">Giới tính</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full bg-secondary border border-border rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground appearance-none cursor-pointer"
              >
                <option value="">-- Chọn --</option>
                <option value="male">Nam</option>
                <option value="female">Nữ</option>
                <option value="other">Khác</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-foreground mb-2">
              Mật khẩu <span className="text-destructive">*</span>
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground placeholder-muted-foreground"
              placeholder="Ít nhất 6 ký tự"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-foreground mb-2">
              Xác nhận mật khẩu <span className="text-destructive">*</span>
            </label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground placeholder-muted-foreground"
              placeholder="Nhập lại mật khẩu"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 bg-foreground hover:bg-foreground/90 text-background rounded-xl font-bold transition-all flex items-center justify-center disabled:opacity-70 shadow-sm mt-1"
          >
            {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Đăng ký'}
          </button>
        </form>

        {/* Login link */}
        <p className="text-center text-sm text-muted-foreground mt-6">
          Đã có tài khoản?{' '}
          <button
            onClick={() => setView('login')}
            className="text-primary font-semibold hover:underline transition-colors"
          >
            Đăng nhập
          </button>
        </p>
      </div>
    </div>
  );
}
