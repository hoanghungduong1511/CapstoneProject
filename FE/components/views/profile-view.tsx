'use client';

import { useEffect, useRef, useState } from 'react';
import { format } from 'date-fns';
import { vi } from 'date-fns/locale';
import {
  Activity,
  Bot,
  Calendar,
  Camera,
  ChevronRight,
  History,
  ImageIcon,
  KeyRound,
  Loader2,
  Lock,
  Mail,
  MessageCircle,
  Save,
  Shield,
  User as UserIcon,
  UserCheck,
} from 'lucide-react';
import { DatePicker } from '@/components/ui/date-picker';
import { getAvatarFallbackUrl, normalizeStorageUrl } from '@/lib/image-url';
import { useAppStore } from '@/store/app-store';
import { fetchCurrentUser } from '@/services/auth';
import {
  changePassword,
  getDiagnosisHistory,
  updateProfile,
  uploadAvatar,
} from '@/services/user';
import { getChatSession, getChatSessions } from '@/services/chat';
import { getAnalysisHistoryDetail } from '@/services/api';
import type {
  ChatSessionDetail,
  ChatSessionSummary,
  DiagnosisHistoryItem,
} from '@/types';

type Tab = 'info' | 'security' | 'history' | 'chats';

export function ProfileView() {
  const {
    user,
    setUser,
    setView,
    setImage,
    setImageFile,
    setResult,
    setChatSessionId,
    showToast,
  } = useAppStore();
  const [activeTab, setActiveTab] = useState<Tab>('info');
  const [name, setName] = useState(user?.name || '');
  const [dateOfBirth, setDateOfBirth] = useState<Date | undefined>(
    user?.date_of_birth ? new Date(user.date_of_birth) : undefined,
  );
  const [gender, setGender] = useState(user?.gender || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [history, setHistory] = useState<DiagnosisHistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [openingHistoryId, setOpeningHistoryId] = useState<string | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSessionSummary[]>([]);
  const [chatTotal, setChatTotal] = useState(0);
  const [selectedChat, setSelectedChat] = useState<ChatSessionDetail | null>(null);
  const [isLoadingChats, setIsLoadingChats] = useState(false);
  const [isLoadingChatDetail, setIsLoadingChatDetail] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!user) return;
    setName(user.name || '');
    setDateOfBirth(user.date_of_birth ? new Date(user.date_of_birth) : undefined);
    setGender(user.gender || '');
  }, [user]);

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory();
    }
    if (activeTab === 'chats') {
      loadChatHistory();
    }
  }, [activeTab]);

  const loadHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const data = await getDiagnosisHistory();
      setHistory(data.items);
      setHistoryTotal(data.total);
    } catch {
      showToast('Không thể tải lịch sử phân tích.', 'error');
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const openAnalysisHistory = async (item: DiagnosisHistoryItem) => {
    if (openingHistoryId) return;
    setOpeningHistoryId(item.id);
    try {
      const detail = await getAnalysisHistoryDetail(item.id);
      setImage(null);
      setImageFile(null);
      setChatSessionId(null);
      setResult(detail);
      setView('result');
    } catch {
      showToast('Không thể mở lại kết quả phân tích này.', 'error');
    } finally {
      setOpeningHistoryId(null);
    }
  };

  const loadChatDetail = async (sessionId: string) => {
    setIsLoadingChatDetail(true);
    try {
      setSelectedChat(await getChatSession(sessionId));
    } catch {
      showToast('Không thể tải nội dung cuộc tư vấn.', 'error');
    } finally {
      setIsLoadingChatDetail(false);
    }
  };

  const loadChatHistory = async () => {
    setIsLoadingChats(true);
    try {
      const data = await getChatSessions();
      setChatSessions(data.items);
      setChatTotal(data.total);
      if (data.items.length > 0) {
        await loadChatDetail(data.items[0].id);
      } else {
        setSelectedChat(null);
      }
    } catch {
      showToast('Không thể tải lịch sử tư vấn.', 'error');
    } finally {
      setIsLoadingChats(false);
    }
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      const updatedUser = await updateProfile({
        name: name || undefined,
        date_of_birth: dateOfBirth ? format(dateOfBirth, 'yyyy-MM-dd') : undefined,
        gender: gender || undefined,
      });
      setUser(updatedUser);
      showToast('Cập nhật thông tin thành công.', 'success');
    } catch {
      showToast('Cập nhật thất bại. Vui lòng thử lại.', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (user?.provider === 'google') {
      showToast('Tài khoản Google không sử dụng mật khẩu nội bộ.', 'error');
      return;
    }

    if (!currentPassword || !newPassword || !confirmPassword) {
      showToast('Vui lòng nhập đầy đủ thông tin mật khẩu.', 'error');
      return;
    }

    if (newPassword.length < 6) {
      showToast('Mật khẩu mới phải có ít nhất 6 ký tự.', 'error');
      return;
    }

    if (newPassword !== confirmPassword) {
      showToast('Xác nhận mật khẩu mới không khớp.', 'error');
      return;
    }

    if (currentPassword === newPassword) {
      showToast('Mật khẩu mới phải khác mật khẩu hiện tại.', 'error');
      return;
    }

    setIsChangingPassword(true);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      showToast('Đổi mật khẩu thành công.', 'success');
    } catch {
      showToast('Đổi mật khẩu thất bại. Vui lòng kiểm tra mật khẩu hiện tại.', 'error');
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      showToast('Ảnh avatar không được vượt quá 5MB.', 'error');
      return;
    }

    setIsUploadingAvatar(true);
    try {
      await uploadAvatar(file);
      const refreshedUser = await fetchCurrentUser();
      setUser(refreshedUser);
      showToast('Cập nhật avatar thành công.', 'success');
    } catch {
      showToast('Upload avatar thất bại. Vui lòng thử lại.', 'error');
    } finally {
      setIsUploadingAvatar(false);
      event.target.value = '';
    }
  };

  const avatarFallback = getAvatarFallbackUrl(user?.name || user?.email, 200);
  const userAvatar = user?.avatar_url ? normalizeStorageUrl(user.avatar_url) : avatarFallback;
  const isGoogleAccount = user?.provider === 'google';

  const genderLabel: Record<string, string> = {
    male: 'Nam',
    female: 'Nữ',
    other: 'Khác',
  };

  const tabs: { id: Tab; label: string; icon: typeof UserIcon }[] = [
    { id: 'info', label: 'Thông tin cá nhân', icon: UserIcon },
    { id: 'security', label: 'Bảo mật', icon: Lock },
    { id: 'history', label: 'Lịch sử phân tích', icon: History },
    { id: 'chats', label: 'Lịch sử tư vấn', icon: MessageCircle },
  ];

  return (
    <div className="flex-1 w-full bg-slate-50/70">
      <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-teal-700">
            Hồ sơ người dùng
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Quản lý tài khoản
          </h1>
          <p className="max-w-2xl text-sm text-slate-600">
            Cập nhật thông tin cá nhân, bảo mật tài khoản và theo dõi lịch sử phân tích da liễu.
          </p>
        </div>

        <div className="mt-7 border-b border-slate-200">
          <div className="flex gap-1 overflow-x-auto">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold transition-colors ${
                    isActive
                      ? 'border-teal-700 text-teal-800'
                      : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        {activeTab === 'info' && (
          <div className="mt-7 grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
            <ProfileSummaryCard
              avatarFallback={avatarFallback}
              userAvatar={userAvatar}
              gender={gender}
              genderLabel={genderLabel}
              isUploadingAvatar={isUploadingAvatar}
              onAvatarClick={handleAvatarClick}
              onAvatarChange={handleAvatarChange}
              fileInputRef={fileInputRef}
            />

            <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 px-6 py-5">
                <h2 className="text-lg font-bold text-slate-950">Thông tin hồ sơ</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Thông tin này được dùng để cá nhân hóa hồ sơ và lịch sử phân tích.
                </p>
              </div>

              <div className="p-6">
                <div className="grid grid-cols-1 gap-5">
                  <div>
                    <label className="mb-2 block text-sm font-semibold text-slate-800">
                      Email
                    </label>
                    <input
                      type="email"
                      value={user?.email || ''}
                      disabled
                      className="h-12 w-full rounded-lg border border-slate-200 bg-slate-100 px-4 text-sm text-slate-500 outline-none"
                    />
                    <p className="mt-1.5 text-xs text-slate-500">Email không thể thay đổi.</p>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-semibold text-slate-800">
                      Họ và tên
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      className="h-12 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-950 outline-none transition-colors placeholder:text-slate-400 focus:border-teal-700 focus:ring-2 focus:ring-teal-700/10"
                      placeholder="Nguyễn Văn A"
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                    <div>
                      <label className="mb-2 block text-sm font-semibold text-slate-800">
                        Ngày sinh
                      </label>
                      <DatePicker
                        value={dateOfBirth}
                        onChange={setDateOfBirth}
                        placeholder="dd/mm/yyyy"
                        maxDate={new Date()}
                      />
                    </div>
                    <div>
                      <label className="mb-2 block text-sm font-semibold text-slate-800">
                        Giới tính
                      </label>
                      <select
                        value={gender}
                        onChange={(event) => setGender(event.target.value)}
                        className="h-12 w-full cursor-pointer appearance-none rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-950 outline-none transition-colors focus:border-teal-700 focus:ring-2 focus:ring-teal-700/10"
                      >
                        <option value="">-- Chọn --</option>
                        <option value="male">Nam</option>
                        <option value="female">Nữ</option>
                        <option value="other">Khác</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex justify-end border-t border-slate-100 pt-5">
                    <button
                      type="button"
                      onClick={handleSaveProfile}
                      disabled={isSaving}
                      className="inline-flex h-11 min-w-40 items-center justify-center rounded-lg bg-teal-700 px-5 text-sm font-bold text-white shadow-sm transition-colors hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-70"
                    >
                      {isSaving ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <Save className="mr-2 h-4 w-4" />
                          Lưu thay đổi
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}

        {activeTab === 'security' && (
          <div className="mt-7 grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
            <ProfileSummaryCard
              avatarFallback={avatarFallback}
              userAvatar={userAvatar}
              gender={gender}
              genderLabel={genderLabel}
              isUploadingAvatar={isUploadingAvatar}
              onAvatarClick={handleAvatarClick}
              onAvatarChange={handleAvatarChange}
              fileInputRef={fileInputRef}
            />

            <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 px-6 py-5">
                <h2 className="text-lg font-bold text-slate-950">Đổi mật khẩu</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Cập nhật mật khẩu định kỳ giúp bảo vệ tài khoản và dữ liệu phân tích của bạn.
                </p>
              </div>

              <div className="p-6">
                {isGoogleAccount ? (
                  <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-4 text-sm text-blue-800">
                    Tài khoản này đang đăng nhập bằng Google, vì vậy mật khẩu được quản lý bởi Google.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-5">
                    <PasswordField
                      label="Mật khẩu hiện tại"
                      value={currentPassword}
                      onChange={setCurrentPassword}
                      placeholder="Nhập mật khẩu hiện tại"
                    />
                    <PasswordField
                      label="Mật khẩu mới"
                      value={newPassword}
                      onChange={setNewPassword}
                      placeholder="Tối thiểu 6 ký tự"
                    />
                    <PasswordField
                      label="Xác nhận mật khẩu mới"
                      value={confirmPassword}
                      onChange={setConfirmPassword}
                      placeholder="Nhập lại mật khẩu mới"
                    />

                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-600">
                      Mật khẩu nên có ít nhất 6 ký tự. Nên kết hợp chữ hoa, chữ thường, số và ký tự đặc biệt để tăng độ an toàn.
                    </div>

                    <div className="flex justify-end border-t border-slate-100 pt-5">
                      <button
                        type="button"
                        onClick={handleChangePassword}
                        disabled={isChangingPassword}
                        className="inline-flex h-11 min-w-44 items-center justify-center rounded-lg bg-teal-700 px-5 text-sm font-bold text-white shadow-sm transition-colors hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-70"
                      >
                        {isChangingPassword ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <>
                            <KeyRound className="mr-2 h-4 w-4" />
                            Cập nhật mật khẩu
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>
        )}

        {activeTab === 'history' && (
          <section className="mt-7 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
              <div>
                <h2 className="text-lg font-bold text-slate-950">Lịch sử phân tích</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Tổng cộng {historyTotal} lần phân tích đã được ghi nhận.
                </p>
              </div>
              <div className="hidden h-10 w-10 items-center justify-center rounded-lg bg-teal-50 text-teal-700 sm:flex">
                <Activity className="h-5 w-5" />
              </div>
            </div>

            {isLoadingHistory ? (
              <div className="flex items-center justify-center py-20 text-slate-500">
                <Loader2 className="h-6 w-6 animate-spin text-teal-700" />
                <span className="ml-3 text-sm font-medium">Đang tải lịch sử...</span>
              </div>
            ) : history.length === 0 ? (
              <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                  <ImageIcon className="h-7 w-7" />
                </div>
                <h3 className="text-base font-bold text-slate-950">
                  Chưa có lịch sử phân tích
                </h3>
                <p className="mt-2 max-w-sm text-sm text-slate-500">
                  Các kết quả phân tích hình ảnh da liễu sẽ được lưu tại đây.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {history.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => openAnalysisHistory(item)}
                    disabled={openingHistoryId !== null}
                    className="grid w-full grid-cols-[64px_1fr] gap-4 px-6 py-4 text-left transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600 disabled:cursor-wait disabled:opacity-70 sm:grid-cols-[64px_1fr_auto]"
                  >
                    <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
                      {item.image_url ? (
                        <img
                          src={normalizeStorageUrl(item.image_url)}
                          alt="Ảnh phân tích"
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center">
                          <ImageIcon className="h-6 w-6 text-slate-400" />
                        </div>
                      )}
                    </div>

                    <div className="min-w-0">
                      <p className="truncate font-semibold text-slate-950">
                        {item.top1_label || 'Đang xử lý...'}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        {item.top1_confidence != null && (
                          <span className="rounded-md bg-teal-50 px-2 py-1 text-xs font-semibold text-teal-700">
                            {(item.top1_confidence * 100).toFixed(1)}% chính xác
                          </span>
                        )}
                        <span
                          className={`rounded-md px-2 py-1 text-xs font-semibold ${
                            item.status === 'completed'
                              ? 'bg-emerald-50 text-emerald-700'
                              : item.status === 'failed'
                              ? 'bg-red-50 text-red-700'
                              : 'bg-amber-50 text-amber-700'
                          }`}
                        >
                          {item.status === 'completed'
                            ? 'Hoàn thành'
                            : item.status === 'failed'
                            ? 'Thất bại'
                            : 'Đang xử lý'}
                        </span>
                      </div>
                    </div>

                    <div className="col-span-2 flex items-center gap-3 text-xs text-slate-500 sm:col-span-1 sm:flex-col sm:items-end sm:justify-center">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5" />
                        {format(new Date(item.created_at), 'dd/MM/yyyy', { locale: vi })}
                      </div>
                      <span>{format(new Date(item.created_at), 'HH:mm', { locale: vi })}</span>
                      <span className="flex items-center gap-1 font-semibold text-teal-700">
                        {openingHistoryId === item.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5" />
                        )}
                        Xem kết quả
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        {activeTab === 'chats' && (
          <section className="mt-7 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
              <div>
                <h2 className="text-lg font-bold text-slate-950">Lịch sử tư vấn</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {chatTotal} cuộc hội thoại với trợ lý y khoa đã được lưu.
                </p>
              </div>
              <div className="hidden h-10 w-10 items-center justify-center rounded-lg bg-teal-50 text-teal-700 sm:flex">
                <MessageCircle className="h-5 w-5" />
              </div>
            </div>

            {isLoadingChats ? (
              <div className="flex items-center justify-center py-20 text-slate-500">
                <Loader2 className="h-6 w-6 animate-spin text-teal-700" />
                <span className="ml-3 text-sm font-medium">Đang tải lịch sử tư vấn...</span>
              </div>
            ) : chatSessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                  <MessageCircle className="h-7 w-7" />
                </div>
                <h3 className="text-base font-bold text-slate-950">
                  Chưa có lịch sử tư vấn
                </h3>
                <p className="mt-2 max-w-sm text-sm text-slate-500">
                  Các cuộc trao đổi với trợ lý y khoa sẽ được lưu tại đây.
                </p>
              </div>
            ) : (
              <div className="grid min-h-[520px] lg:grid-cols-[340px_1fr]">
                <div className="border-b border-slate-200 lg:border-b-0 lg:border-r">
                  <div className="max-h-[520px] divide-y divide-slate-100 overflow-y-auto">
                    {chatSessions.map((session) => {
                      const isSelected = selectedChat?.id === session.id;
                      return (
                        <button
                          key={session.id}
                          type="button"
                          onClick={() => loadChatDetail(session.id)}
                          className={`flex w-full items-start gap-3 px-5 py-4 text-left transition-colors ${
                            isSelected
                              ? 'bg-teal-50'
                              : 'bg-white hover:bg-slate-50'
                          }`}
                        >
                          <div className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                            isSelected
                              ? 'bg-teal-700 text-white'
                              : 'bg-slate-100 text-slate-500'
                          }`}>
                            <MessageCircle className="h-4 w-4" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold text-slate-950">
                              {session.title}
                            </p>
                            <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                              {session.last_message || 'Chưa có tin nhắn'}
                            </p>
                            <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-400">
                              <span>{session.message_count} tin nhắn</span>
                              <span>•</span>
                              <span>
                                {format(new Date(session.last_message_at), 'dd/MM/yyyy HH:mm')}
                              </span>
                            </div>
                          </div>
                          <ChevronRight className="mt-2 h-4 w-4 shrink-0 text-slate-400" />
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="flex min-h-[420px] flex-col bg-slate-50/60">
                  {isLoadingChatDetail ? (
                    <div className="flex flex-1 items-center justify-center text-slate-500">
                      <Loader2 className="h-5 w-5 animate-spin text-teal-700" />
                    </div>
                  ) : selectedChat ? (
                    <>
                      <div className="border-b border-slate-200 bg-white px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
                            <Bot className="h-4 w-4" />
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-slate-950">
                              Trợ lý Y khoa AI
                            </p>
                            <p className="text-xs text-slate-500">
                              {format(new Date(selectedChat.created_at), 'dd/MM/yyyy HH:mm')}
                            </p>
                          </div>
                        </div>
                      </div>
                      <div className="flex max-h-[455px] flex-1 flex-col gap-4 overflow-y-auto p-5">
                        {selectedChat.messages.map((message) => (
                          <div
                            key={message.id}
                            className={`flex ${
                              message.role === 'user' ? 'justify-end' : 'justify-start'
                            }`}
                          >
                            <div className={`max-w-[88%] rounded-lg px-4 py-3 text-sm shadow-sm ${
                              message.role === 'user'
                                ? 'bg-teal-700 text-white'
                                : 'border border-slate-200 bg-white text-slate-700'
                            }`}>
                              <p className="whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word] leading-6">
                                {message.content.trim()
                                  ? message.content.trim().charAt(0).toLocaleUpperCase('vi-VN') +
                                    message.content.trim().slice(1)
                                  : ''}
                              </p>
                              <p className={`mt-2 text-[10px] ${
                                message.role === 'user'
                                  ? 'text-right text-teal-100'
                                  : 'text-slate-400'
                              }`}>
                                {format(new Date(message.created_at), 'HH:mm')}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="flex flex-1 items-center justify-center text-sm text-slate-500">
                      Chọn một cuộc hội thoại để xem nội dung.
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

function PasswordField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <div>
      <label className="mb-2 block text-sm font-semibold text-slate-800">{label}</label>
      <div className="relative">
        <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="password"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="h-12 w-full rounded-lg border border-slate-200 bg-white pl-10 pr-4 text-sm text-slate-950 outline-none transition-colors placeholder:text-slate-400 focus:border-teal-700 focus:ring-2 focus:ring-teal-700/10"
          placeholder={placeholder}
          autoComplete="new-password"
        />
      </div>
    </div>
  );
}

function ProfileSummaryCard({
  avatarFallback,
  userAvatar,
  gender,
  genderLabel,
  isUploadingAvatar,
  onAvatarClick,
  onAvatarChange,
  fileInputRef,
}: {
  avatarFallback: string;
  userAvatar: string;
  gender: string;
  genderLabel: Record<string, string>;
  isUploadingAvatar: boolean;
  onAvatarClick: () => void;
  onAvatarChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
}) {
  const { user } = useAppStore();

  return (
    <aside className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="h-1 bg-teal-700" />
      <div className="p-6">
        <div className="flex flex-col items-center text-center">
          <div className="relative">
            <img
              src={userAvatar}
              alt="Avatar"
              className="h-28 w-28 rounded-full border border-slate-200 bg-slate-100 object-cover shadow-sm"
              onError={(event) => {
                if (event.currentTarget.src !== avatarFallback) {
                  event.currentTarget.src = avatarFallback;
                }
              }}
            />
            <button
              type="button"
              onClick={onAvatarClick}
              disabled={isUploadingAvatar}
              className="absolute bottom-1 right-1 flex h-9 w-9 items-center justify-center rounded-full border border-white bg-teal-700 text-white shadow-sm transition-colors hover:bg-teal-800 disabled:opacity-60"
              aria-label="Cập nhật avatar"
            >
              {isUploadingAvatar ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Camera className="h-4 w-4" />
              )}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={onAvatarChange}
            />
          </div>

          <h2 className="mt-4 text-lg font-bold text-slate-950">
            {user?.name || 'Chưa đặt tên'}
          </h2>
          <p className="mt-1 text-sm text-slate-500">{user?.email}</p>
        </div>

        <dl className="mt-6 divide-y divide-slate-100 rounded-lg border border-slate-200 bg-slate-50">
          <ProfileMetaRow
            icon={Shield}
            label="Vai trò"
            value={user?.role === 'admin' ? 'Admin' : 'Người dùng'}
          />
          <ProfileMetaRow
            icon={Mail}
            label="Tài khoản"
            value={user?.provider === 'google' ? 'Google' : 'Email'}
          />
          <ProfileMetaRow
            icon={UserCheck}
            label="Giới tính"
            value={gender ? genderLabel[gender] || gender : 'Chưa cập nhật'}
          />
          <ProfileMetaRow
            icon={Calendar}
            label="Tham gia"
            value={
              user?.created_at
                ? format(new Date(user.created_at), 'dd/MM/yyyy', { locale: vi })
                : '-'
            }
          />
        </dl>
      </div>
    </aside>
  );
}

function ProfileMetaRow({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Shield;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3">
      <dt className="flex items-center gap-2 text-xs font-medium text-slate-500">
        <Icon className="h-4 w-4 text-teal-700" />
        {label}
      </dt>
      <dd className="text-sm font-semibold text-slate-900">{value}</dd>
    </div>
  );
}
