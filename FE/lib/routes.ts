import type { ViewState } from '@/types';

const ANALYSIS_VIEWS: ViewState[] = ['upload', 'validating', 'analyzing', 'result'];

export const VIEW_ROUTES: Partial<Record<ViewState, string>> = {
  landing: '/trang-chu',
  login: '/dang-nhap',
  register: '/dang-ky',
  upload: '/phan-tich',
  validating: '/phan-tich',
  analyzing: '/phan-tich',
  result: '/phan-tich',
  profile: '/quan-lý-tai-khoan',
  'admin-users': '/admin',
};

export const ROUTE_VIEWS: Record<string, ViewState> = {
  '/': 'landing',
  '/trang-chu': 'landing',
  '/dang-nhap': 'login',
  '/dang-ky': 'register',
  '/phan-tich': 'upload',
  '/quan-lý-tai-khoan': 'profile',
  '/quan-ly-tai-khoan': 'profile',
  '/admin': 'admin-users',
};

export function viewToPath(view: ViewState): string {
  return VIEW_ROUTES[view] || '/trang-chu';
}

export function pathToView(pathname: string): ViewState {
  const decodedPathname = decodeURI(pathname);
  return ROUTE_VIEWS[decodedPathname] || 'landing';
}

export function isAnalysisView(view: ViewState): boolean {
  return ANALYSIS_VIEWS.includes(view);
}

export function pushViewPath(view: ViewState) {
  if (typeof window === 'undefined') return;

  const nextPath = viewToPath(view);
  if (decodeURI(window.location.pathname) !== nextPath) {
    window.history.pushState(null, '', nextPath);
  }
}
