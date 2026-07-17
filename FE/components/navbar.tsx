'use client';

import { useState } from 'react';
import {
  LogOut,
  Menu,
  Moon,
  ShieldCheck,
  Sun,
  User as UserIcon,
  Users,
  X,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { getAvatarFallbackUrl, normalizeStorageUrl } from '@/lib/image-url';
import { logoutUser } from '@/services/auth';
import { useAppStore } from '@/store/app-store';

export function Navbar() {
  const { view, setView, user, setUser, navigateTo } = useAppStore();
  const { setTheme } = useTheme();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const isAdmin = user?.role === 'admin';

  const avatarFallback = getAvatarFallbackUrl(user?.name || user?.email, 96);
  const userAvatar = user?.avatar_url
    ? normalizeStorageUrl(user.avatar_url)
    : avatarFallback;

  const handleLogout = async () => {
    await logoutUser();
    setUser(null);
    setIsDropdownOpen(false);
    setIsMobileMenuOpen(false);
    setView('landing');
  };

  const handleLogoClick = () => {
    setView(isAdmin ? 'admin-users' : 'landing');
  };

  const UserNavLinks = ({ mobile = false }: { mobile?: boolean }) => (
    <>
      <NavButton
        active={view === 'landing'}
        mobile={mobile}
        onClick={() => {
          setView('landing');
          setIsMobileMenuOpen(false);
        }}
      >
        Trang chủ
      </NavButton>
      <NavButton
        active={['upload', 'validating', 'analyzing', 'result'].includes(view)}
        mobile={mobile}
        onClick={() => {
          navigateTo('upload');
          setIsMobileMenuOpen(false);
        }}
      >
        Phân tích
      </NavButton>
    </>
  );

  return (
    <header className="sticky top-0 z-30 w-full border-b border-slate-200 bg-white shadow-sm">
      <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={handleLogoClick}
          className="flex items-center gap-2"
        >
          <img
            src="/icon-skin.png"
            alt="SkinAI"
            className="h-8 w-8 rounded-full border border-slate-200 bg-slate-50 object-cover p-0.5"
          />
          <span className="text-xl font-extrabold tracking-tight text-slate-950">
            Skin<span className="text-teal-700">AI</span>
          </span>
          {isAdmin && (
            <span className="ml-2 hidden rounded-md bg-slate-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-600 sm:inline">
              Admin
            </span>
          )}
        </button>

        <nav className="hidden items-center gap-8 md:flex">
          {isAdmin ? (
            <button
              type="button"
              onClick={() => setView('admin-users')}
              className="flex items-center gap-2 text-sm font-bold text-teal-700"
            >
              <Users className="h-4 w-4" />
              Quản lý người dùng
            </button>
          ) : (
            <UserNavLinks />
          )}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <ThemeMenu setTheme={setTheme} />

          {user ? (
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsDropdownOpen((open) => !open)}
                className="flex items-center gap-2 rounded-full border border-slate-200 bg-white p-1 pr-3 shadow-sm transition-colors hover:bg-slate-50"
              >
                <img
                  src={userAvatar}
                  alt={user.name || user.email}
                  className="h-8 w-8 rounded-full bg-slate-100 object-cover"
                  onError={(event) => {
                    event.currentTarget.src = avatarFallback;
                  }}
                />
                <span className="max-w-44 truncate text-sm font-semibold text-slate-800">
                  {user.name || user.email}
                </span>
              </button>

              {isDropdownOpen && (
                <>
                  <button
                    type="button"
                    className="fixed inset-0 z-40 cursor-default"
                    onClick={() => setIsDropdownOpen(false)}
                    aria-label="Đóng menu"
                  />
                  <div className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
                    <div className="border-b border-slate-100 bg-slate-50 px-4 py-3">
                      <div className="flex items-center gap-2">
                        {isAdmin && <ShieldCheck className="h-4 w-4 text-teal-700" />}
                        <p className="truncate text-sm font-bold text-slate-900">
                          {user.name || 'Người dùng'}
                        </p>
                      </div>
                      <p className="mt-1 truncate text-xs text-slate-500">{user.email}</p>
                      {isAdmin && (
                        <p className="mt-2 text-xs font-semibold text-teal-700">
                          Quản trị viên hệ thống
                        </p>
                      )}
                    </div>

                    {!isAdmin && (
                      <button
                        type="button"
                        onClick={() => {
                          setView('profile');
                          setIsDropdownOpen(false);
                        }}
                        className="flex w-full items-center px-4 py-3 text-left text-sm font-semibold text-slate-600 hover:bg-slate-50"
                      >
                        <UserIcon className="mr-2 h-4 w-4" />
                        Quản lý tài khoản
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="flex w-full items-center px-4 py-3 text-left text-sm font-semibold text-red-600 hover:bg-red-50"
                    >
                      <LogOut className="mr-2 h-4 w-4" />
                      Đăng xuất
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setView('login')}
              className="rounded-md bg-slate-900 px-5 py-2.5 text-sm font-bold text-white hover:bg-slate-800"
            >
              Đăng nhập
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <ThemeMenu setTheme={setTheme} />
          <button
            type="button"
            onClick={() => setIsMobileMenuOpen((open) => !open)}
            className="flex h-9 w-9 items-center justify-center text-slate-600"
            aria-label="Menu"
          >
            {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {isMobileMenuOpen && (
        <div className="absolute left-0 top-16 z-40 w-full border-b border-slate-200 bg-white px-5 py-5 shadow-lg md:hidden">
          <nav className="flex flex-col">
            {isAdmin ? (
              <NavButton
                active
                mobile
                onClick={() => {
                  setView('admin-users');
                  setIsMobileMenuOpen(false);
                }}
              >
                Quản lý người dùng
              </NavButton>
            ) : (
              <UserNavLinks mobile />
            )}
          </nav>
          <div className="mt-4 border-t border-slate-100 pt-4">
            {user ? (
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center py-3 text-sm font-bold text-red-600"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Đăng xuất
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setView('login');
                  setIsMobileMenuOpen(false);
                }}
                className="h-11 w-full rounded-md bg-slate-900 text-sm font-bold text-white"
              >
                Đăng nhập
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

function NavButton({
  active,
  mobile,
  onClick,
  children,
}: {
  active: boolean;
  mobile?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`font-semibold transition-colors ${
        mobile ? 'w-full py-3 text-left text-base' : 'text-sm'
      } ${active ? 'text-teal-700' : 'text-slate-500 hover:text-slate-900'}`}
    >
      {children}
    </button>
  );
}

function ThemeMenu({ setTheme }: { setTheme: (theme: string) => void }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Đổi giao diện</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme('light')}>
          <Sun className="mr-2 h-4 w-4" />
          Sáng
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('dark')}>
          <Moon className="mr-2 h-4 w-4" />
          Tối
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

