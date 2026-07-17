'use client';

import { useCallback, useEffect, useState } from 'react';
import { format } from 'date-fns';
import { vi } from 'date-fns/locale';
import {
  Activity,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  CircleSlash2,
  Eye,
  ImageIcon,
  Loader2,
  Lock,
  Search,
  ShieldCheck,
  Unlock,
  UserCheck,
  Users,
  X,
} from 'lucide-react';
import {
  getAdminUserDetail,
  getAdminUsers,
  setAdminUserLocked,
} from '@/services/admin';
import { getAvatarFallbackUrl, normalizeStorageUrl } from '@/lib/image-url';
import { useAppStore } from '@/store/app-store';
import type {
  AdminAnalysisHistoryItem,
  AdminUserDetail,
  AdminUserListItem,
  AdminUserListResponse,
} from '@/types';

const PAGE_SIZE = 12;

const EMPTY_RESPONSE: AdminUserListResponse = {
  items: [],
  total: 0,
  active: 0,
  inactive: 0,
  total_analyses: 0,
};

export function AdminUsersView() {
  const { showToast } = useAppStore();
  const [data, setData] = useState<AdminUserListResponse>(EMPTY_RESPONSE);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'active' | 'inactive' | ''>('');
  const [page, setPage] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<AdminUserDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [pendingStatusUser, setPendingStatusUser] = useState<AdminUserDetail | null>(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  const loadUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await getAdminUsers({
        search,
        status: statusFilter,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      });
      setData(response);
    } catch {
      showToast('Không thể tải danh sách người dùng.', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [page, search, showToast, statusFilter]);

  useEffect(() => {
    const timer = window.setTimeout(loadUsers, 250);
    return () => window.clearTimeout(timer);
  }, [loadUsers]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(0);
  };

  const handleStatusChange = (value: 'active' | 'inactive' | '') => {
    setStatusFilter(value);
    setPage(0);
  };

  const openUserDetail = async (userId: string) => {
    setIsLoadingDetail(true);
    setSelectedUser(null);
    try {
      setSelectedUser(await getAdminUserDetail(userId));
    } catch {
      showToast('Không thể tải thông tin người dùng.', 'error');
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const confirmStatusUpdate = async () => {
    if (!pendingStatusUser) return;

    const shouldLock = pendingStatusUser.status === 'active';
    setIsUpdatingStatus(true);
    try {
      const response = await setAdminUserLocked(pendingStatusUser.id, shouldLock);
      showToast(response.message, 'success');
      setPendingStatusUser(null);
      await loadUsers();
      setSelectedUser(await getAdminUserDetail(pendingStatusUser.id));
    } catch {
      showToast('Không thể cập nhật trạng thái tài khoản.', 'error');
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const pageCount = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="min-h-[calc(100vh-4rem)] w-full bg-slate-50">
      <div className="mx-auto w-full max-w-[1440px] px-4 py-7 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-teal-700">
              <ShieldCheck className="h-4 w-4" />
              Bảng điều khiển quản trị
            </div>
            <h1 className="mt-2 text-2xl font-bold text-slate-950 sm:text-3xl">
              Quản lý người dùng
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Theo dõi tài khoản, lịch sử phân tích và kiểm soát quyền truy cập hệ thống.
            </p>
          </div>
          <div className="text-sm text-slate-500">
            Dữ liệu cập nhật theo thời gian thực
          </div>
        </header>

        <section className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            icon={Users}
            label="Tổng người dùng"
            value={data.total}
            tone="slate"
          />
          <StatCard
            icon={UserCheck}
            label="Đang hoạt động"
            value={data.active}
            tone="green"
          />
          <StatCard
            icon={CircleSlash2}
            label="Đã bị khóa"
            value={data.inactive}
            tone="red"
          />
          <StatCard
            icon={Activity}
            label="Lượt phân tích"
            value={data.total_analyses}
            tone="teal"
          />
        </section>

        <section className="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:max-w-sm">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={search}
                onChange={(event) => handleSearchChange(event.target.value)}
                placeholder="Tìm theo tên hoặc email"
                className="h-10 w-full rounded-md border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-teal-700 focus:ring-2 focus:ring-teal-700/10"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="hidden text-xs font-medium text-slate-500 sm:inline">
                Trạng thái:
              </span>
              <select
                value={statusFilter}
                onChange={(event) =>
                  handleStatusChange(event.target.value as 'active' | 'inactive' | '')
                }
                className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none focus:border-teal-700"
              >
                <option value="">Tất cả</option>
                <option value="active">Đang hoạt động</option>
                <option value="inactive">Đã bị khóa</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left">
                  <TableHeading>Người dùng</TableHeading>
                  <TableHeading>Tài khoản</TableHeading>
                  <TableHeading>Trạng thái</TableHeading>
                  <TableHeading>Phân tích</TableHeading>
                  <TableHeading>Lần gần nhất</TableHeading>
                  <TableHeading align="right">Thao tác</TableHeading>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td colSpan={6}>
                      <div className="flex h-56 items-center justify-center text-slate-500">
                        <Loader2 className="mr-2 h-5 w-5 animate-spin text-teal-700" />
                        Đang tải danh sách...
                      </div>
                    </td>
                  </tr>
                ) : data.items.length === 0 ? (
                  <tr>
                    <td colSpan={6}>
                      <div className="flex h-56 flex-col items-center justify-center text-center">
                        <Users className="h-8 w-8 text-slate-300" />
                        <p className="mt-3 font-semibold text-slate-700">
                          Không tìm thấy người dùng
                        </p>
                        <p className="mt-1 text-sm text-slate-500">
                          Thử thay đổi từ khóa hoặc bộ lọc trạng thái.
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  data.items.map((user) => (
                    <UserTableRow
                      key={user.id}
                      user={user}
                      onView={() => openUserDetail(user.id)}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
            <p className="text-xs text-slate-500">
              Hiển thị {data.items.length} trên {data.total} người dùng
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((current) => Math.max(0, current - 1))}
                disabled={page === 0 || isLoading}
                className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Trang trước"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="min-w-20 text-center text-sm font-semibold text-slate-700">
                {page + 1} / {pageCount}
              </span>
              <button
                type="button"
                onClick={() =>
                  setPage((current) => Math.min(pageCount - 1, current + 1))
                }
                disabled={page + 1 >= pageCount || isLoading}
                className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Trang sau"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </section>
      </div>

      {(selectedUser || isLoadingDetail) && (
        <UserDetailDrawer
          user={selectedUser}
          isLoading={isLoadingDetail}
          onClose={() => setSelectedUser(null)}
          onRequestStatusChange={() => selectedUser && setPendingStatusUser(selectedUser)}
        />
      )}

      {pendingStatusUser && (
        <StatusConfirmDialog
          user={pendingStatusUser}
          isUpdating={isUpdatingStatus}
          onCancel={() => setPendingStatusUser(null)}
          onConfirm={confirmStatusUpdate}
        />
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Users;
  label: string;
  value: number;
  tone: 'slate' | 'green' | 'red' | 'teal';
}) {
  const tones = {
    slate: 'bg-slate-100 text-slate-700',
    green: 'bg-emerald-50 text-emerald-700',
    red: 'bg-red-50 text-red-700',
    teal: 'bg-teal-50 text-teal-700',
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className={`flex h-9 w-9 items-center justify-center rounded-md ${tones[tone]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <p className="mt-4 text-2xl font-bold text-slate-950">{value.toLocaleString('vi-VN')}</p>
      <p className="mt-1 text-xs font-medium text-slate-500">{label}</p>
    </div>
  );
}

function TableHeading({
  children,
  align = 'left',
}: {
  children: React.ReactNode;
  align?: 'left' | 'right';
}) {
  return (
    <th
      className={`px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500 ${
        align === 'right' ? 'text-right' : 'text-left'
      }`}
    >
      {children}
    </th>
  );
}

function UserTableRow({
  user,
  onView,
}: {
  user: AdminUserListItem;
  onView: () => void;
}) {
  const fallback = getAvatarFallbackUrl(user.name || user.email, 80);
  const avatar = user.avatar_url ? normalizeStorageUrl(user.avatar_url) : fallback;

  return (
    <tr className="transition-colors hover:bg-slate-50/80">
      <td className="px-4 py-4">
        <div className="flex items-center gap-3">
          <img
            src={avatar}
            alt={user.name || user.email}
            className="h-10 w-10 rounded-full border border-slate-200 bg-slate-100 object-cover"
            onError={(event) => {
              event.currentTarget.src = fallback;
            }}
          />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">
              {user.name || 'Chưa cập nhật tên'}
            </p>
            <p className="truncate text-xs text-slate-500">{user.email}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-4">
        <span className="text-sm font-medium text-slate-700">
          {user.provider === 'google' ? 'Google' : 'Email'}
        </span>
        <p className="mt-0.5 text-xs text-slate-500">
          Tạo {formatDate(user.created_at)}
        </p>
      </td>
      <td className="px-4 py-4">
        <StatusBadge status={user.status} />
      </td>
      <td className="px-4 py-4">
        <span className="text-sm font-bold text-slate-900">{user.analysis_count}</span>
        <span className="ml-1 text-xs text-slate-500">lượt</span>
      </td>
      <td className="px-4 py-4 text-sm text-slate-600">
        {user.last_analysis_at ? formatDateTime(user.last_analysis_at) : 'Chưa có'}
      </td>
      <td className="px-4 py-4 text-right">
        <button
          type="button"
          onClick={onView}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 px-3 text-xs font-bold text-slate-700 transition-colors hover:border-teal-200 hover:bg-teal-50 hover:text-teal-800"
        >
          <Eye className="h-4 w-4" />
          Chi tiết
        </button>
      </td>
    </tr>
  );
}

function UserDetailDrawer({
  user,
  isLoading,
  onClose,
  onRequestStatusChange,
}: {
  user: AdminUserDetail | null;
  isLoading: boolean;
  onClose: () => void;
  onRequestStatusChange: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/25" role="dialog">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
        aria-label="Đóng"
      />
      <aside className="relative z-10 flex h-full w-full max-w-2xl flex-col bg-white shadow-2xl">
        <div className="flex h-16 items-center justify-between border-b border-slate-200 px-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-teal-700">
              Hồ sơ người dùng
            </p>
            <h2 className="text-lg font-bold text-slate-950">Thông tin và lịch sử</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100"
            aria-label="Đóng"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {isLoading || !user ? (
          <div className="flex flex-1 items-center justify-center text-slate-500">
            <Loader2 className="mr-2 h-5 w-5 animate-spin text-teal-700" />
            Đang tải hồ sơ...
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <UserProfileSummary user={user} />

            <div className="border-t border-slate-200 px-5 py-5">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-950">Lịch sử phân tích</h3>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {user.analysis_count} lần phân tích được ghi nhận
                  </p>
                </div>
              </div>

              {user.history.length === 0 ? (
                <div className="mt-5 flex flex-col items-center rounded-lg border border-dashed border-slate-200 py-12 text-center">
                  <ImageIcon className="h-7 w-7 text-slate-300" />
                  <p className="mt-3 text-sm font-semibold text-slate-700">
                    Chưa có lịch sử phân tích
                  </p>
                </div>
              ) : (
                <div className="mt-4 divide-y divide-slate-100 border-y border-slate-100">
                  {user.history.map((item) => (
                    <HistoryRow key={item.id} item={item} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {user && !isLoading && (
          <div className="border-t border-slate-200 bg-white px-5 py-4">
            <button
              type="button"
              onClick={onRequestStatusChange}
              className={`flex h-11 w-full items-center justify-center gap-2 rounded-md text-sm font-bold transition-colors ${
                user.status === 'active'
                  ? 'border border-red-200 bg-white text-red-700 hover:bg-red-50'
                  : 'bg-teal-700 text-white hover:bg-teal-800'
              }`}
            >
              {user.status === 'active' ? (
                <>
                  <Lock className="h-4 w-4" />
                  Khóa tài khoản
                </>
              ) : (
                <>
                  <Unlock className="h-4 w-4" />
                  Mở khóa tài khoản
                </>
              )}
            </button>
          </div>
        )}
      </aside>
    </div>
  );
}

function UserProfileSummary({ user }: { user: AdminUserDetail }) {
  const fallback = getAvatarFallbackUrl(user.name || user.email, 120);
  const avatar = user.avatar_url ? normalizeStorageUrl(user.avatar_url) : fallback;

  return (
    <div className="px-5 py-6">
      <div className="flex items-start gap-4">
        <img
          src={avatar}
          alt={user.name || user.email}
          className="h-16 w-16 rounded-full border border-slate-200 bg-slate-100 object-cover"
          onError={(event) => {
            event.currentTarget.src = fallback;
          }}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-lg font-bold text-slate-950">
              {user.name || 'Chưa cập nhật tên'}
            </h3>
            <StatusBadge status={user.status} />
          </div>
          <p className="mt-1 text-sm text-slate-500">{user.email}</p>
          <p className="mt-2 text-xs text-slate-500">
            Tài khoản {user.provider === 'google' ? 'Google' : 'Email'} · Tham gia{' '}
            {formatDate(user.created_at)}
          </p>
        </div>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-slate-200 bg-slate-200">
        <InfoCell label="Ngày sinh" value={user.date_of_birth ? formatDate(user.date_of_birth) : 'Chưa cập nhật'} />
        <InfoCell label="Giới tính" value={formatGender(user.gender)} />
        <InfoCell label="Số lượt phân tích" value={`${user.analysis_count} lượt`} />
        <InfoCell label="Cập nhật hồ sơ" value={formatDate(user.updated_at)} />
      </dl>
    </div>
  );
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-50 px-4 py-3">
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

function HistoryRow({ item }: { item: AdminAnalysisHistoryItem }) {
  return (
    <div className="grid grid-cols-[56px_1fr] gap-3 py-4 sm:grid-cols-[56px_1fr_auto]">
      <div className="h-14 w-14 overflow-hidden rounded-md border border-slate-200 bg-slate-100">
        {item.image_url ? (
          <img
            src={normalizeStorageUrl(item.image_url)}
            alt="Ảnh phân tích"
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <ImageIcon className="h-5 w-5 text-slate-400" />
          </div>
        )}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-bold text-slate-900">
          {item.top1_label || 'Chưa có kết quả phân loại'}
        </p>
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
          {item.top1_confidence != null && (
            <span>{(item.top1_confidence * 100).toFixed(1)}% chính xác</span>
          )}
          {item.lesion_area_percent != null && (
            <span>{item.lesion_area_percent.toFixed(1)}% vùng tổn thương</span>
          )}
          <span>{formatAnalysisStatus(item.status)}</span>
        </div>
      </div>
      <div className="col-span-2 flex items-center gap-1 text-xs text-slate-500 sm:col-span-1 sm:block sm:text-right">
        <CalendarDays className="h-3.5 w-3.5 sm:hidden" />
        <p>{formatDate(item.created_at)}</p>
        <p className="sm:mt-1">{format(new Date(item.created_at), 'HH:mm')}</p>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const active = status === 'active';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${
        active ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-emerald-500' : 'bg-red-500'}`} />
      {active ? 'Hoạt động' : 'Đã khóa'}
    </span>
  );
}

function StatusConfirmDialog({
  user,
  isUpdating,
  onCancel,
  onConfirm,
}: {
  user: AdminUserDetail;
  isUpdating: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const shouldLock = user.status === 'active';
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/40 px-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-xl">
        <div
          className={`flex h-11 w-11 items-center justify-center rounded-md ${
            shouldLock ? 'bg-red-50 text-red-700' : 'bg-teal-50 text-teal-700'
          }`}
        >
          {shouldLock ? <Lock className="h-5 w-5" /> : <Unlock className="h-5 w-5" />}
        </div>
        <h2 className="mt-4 text-lg font-bold text-slate-950">
          {shouldLock ? 'Khóa tài khoản?' : 'Mở khóa tài khoản?'}
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {shouldLock
            ? `${user.name || user.email} sẽ không thể đăng nhập hoặc tiếp tục sử dụng hệ thống.`
            : `${user.name || user.email} sẽ có thể đăng nhập và sử dụng hệ thống trở lại.`}
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isUpdating}
            className="h-10 rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isUpdating}
            className={`flex h-10 min-w-28 items-center justify-center rounded-md px-4 text-sm font-bold text-white disabled:opacity-60 ${
              shouldLock ? 'bg-red-600 hover:bg-red-700' : 'bg-teal-700 hover:bg-teal-800'
            }`}
          >
            {isUpdating ? <Loader2 className="h-4 w-4 animate-spin" /> : shouldLock ? 'Khóa' : 'Mở khóa'}
          </button>
        </div>
      </div>
    </div>
  );
}

function formatDate(value: string) {
  return format(new Date(value), 'dd/MM/yyyy', { locale: vi });
}

function formatDateTime(value: string) {
  return format(new Date(value), 'dd/MM/yyyy HH:mm', { locale: vi });
}

function formatGender(gender: string | null) {
  if (gender === 'male') return 'Nam';
  if (gender === 'female') return 'Nữ';
  if (gender === 'other') return 'Khác';
  return 'Chưa cập nhật';
}

function formatAnalysisStatus(status: string) {
  if (status === 'completed') return 'Hoàn thành';
  if (status === 'failed') return 'Thất bại';
  return 'Đang xử lý';
}
