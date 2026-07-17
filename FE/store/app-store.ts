'use client';

import { create } from 'zustand';
import { pushViewPath } from '@/lib/routes';
import type { ViewState, User, Message, SkinAnalysisResponse, Toast } from '@/types';

// Các view cần đăng nhập mới truy cập được
const PROTECTED_VIEWS: ViewState[] = ['upload', 'validating', 'analyzing', 'result', 'chat', 'profile', 'admin-users'];

export type ChatWidgetMode = 'general' | 'result_context' | 'result_selector';

interface AppState {
  // Navigation
  view: ViewState;
  setView: (view: ViewState) => void;
  syncViewFromRoute: (view: ViewState) => void;

  // User
  user: User | null;
  setUser: (user: User | null) => void;

  // Image analysis
  image: string | null;
  setImage: (image: string | null) => void;
  imageFile: File | null;
  setImageFile: (file: File | null) => void;
  imageHash: string | null;
  setImageHash: (hash: string | null) => void;
  result: SkinAnalysisResponse | null;
  setResult: (result: SkinAnalysisResponse | null) => void;

  // Chat
  chatHistory: Message[];
  chatSessionId: string | null;
  setChatSessionId: (sessionId: string | null) => void;
  setChatHistory: (history: Message[] | ((prev: Message[]) => Message[])) => void;
  addMessage: (message: Message) => void;
  isChatWidgetOpen: boolean;
  chatWidgetMode: ChatWidgetMode;
  activeChatAiResultId: string | null;
  latestAiResultId: string | null;
  openChatWidget: () => void;
  closeChatWidget: () => void;
  openGeneralChat: () => void;
  openChatForResult: (aiResultId?: string | null) => void;
  openResultSelector: () => void;

  // Toast
  toast: Toast | null;
  showToast: (message: string, type?: 'error' | 'success') => void;
  hideToast: () => void;

  // Actions
  resetAnalysis: () => void;

  // Navigation guard: chuyển view an toàn, kiểm tra auth trước
  navigateTo: (view: ViewState) => void;
}

const initialChatMessage: Message = {
  id: '1',
  role: 'ai',
  content: 'Xin chào. Tôi là trợ lý AI Da liễu. Tôi có thể giúp gì cho bạn với kết quả chẩn đoán hôm nay?',
  timestamp: new Date(),
};

export const useAppStore = create<AppState>((set, get) => ({
  // Navigation
  view: 'landing',
  setView: (view) => {
    set({ view });
    pushViewPath(view);
  },
  syncViewFromRoute: (view) => set({ view }),

  // User
  user: null,
  setUser: (user) => set({ user }),

  // Image analysis
  image: null,
  setImage: (image) => set({ image }),
  imageFile: null,
  setImageFile: (imageFile) => set({ imageFile }),
  imageHash: null,
  setImageHash: (imageHash) => set({ imageHash }),
  result: null,
  setResult: (result) =>
    set((state) => {
      const previousResultId = state.result?.ai_result_id || null;
      const nextResultId = result?.ai_result_id || null;
      if (previousResultId !== nextResultId) {
        return {
          result,
          latestAiResultId: nextResultId,
          activeChatAiResultId: nextResultId || state.activeChatAiResultId,
          chatWidgetMode: nextResultId ? 'result_context' : state.chatWidgetMode,
          chatHistory: [initialChatMessage],
          chatSessionId: null,
        };
      }
      return {
        result,
        latestAiResultId: nextResultId || state.latestAiResultId,
      };
    }),

  // Chat
  chatHistory: [initialChatMessage],
  chatSessionId: null,
  isChatWidgetOpen: false,
  chatWidgetMode: 'general',
  activeChatAiResultId: null,
  latestAiResultId: null,
  setChatSessionId: (chatSessionId) => set({ chatSessionId }),
  setChatHistory: (history) =>
    set((state) => ({
      chatHistory: typeof history === 'function' ? history(state.chatHistory) : history,
    })),
  addMessage: (message) =>
    set((state) => ({
      chatHistory: [...state.chatHistory, message],
    })),
  openChatWidget: () =>
    set((state) => {
      const activeAiResultId = state.activeChatAiResultId || state.latestAiResultId;
      return {
        isChatWidgetOpen: true,
        chatWidgetMode: activeAiResultId ? 'result_context' : 'general',
        activeChatAiResultId: activeAiResultId || null,
      };
    }),
  closeChatWidget: () => set({ isChatWidgetOpen: false }),
  openGeneralChat: () =>
    set({
      isChatWidgetOpen: true,
      chatWidgetMode: 'general',
      activeChatAiResultId: null,
    }),
  openChatForResult: (aiResultId) =>
    set((state) => {
      const nextAiResultId = aiResultId || state.result?.ai_result_id || state.latestAiResultId || null;
      return {
        isChatWidgetOpen: true,
        chatWidgetMode: nextAiResultId ? 'result_context' : 'general',
        activeChatAiResultId: nextAiResultId,
        latestAiResultId: nextAiResultId || state.latestAiResultId,
      };
    }),
  openResultSelector: () =>
    set({
      isChatWidgetOpen: true,
      chatWidgetMode: 'result_selector',
    }),

  // Toast
  toast: null,
  showToast: (message, type = 'error') => {
    set({ toast: { message, type } });
    setTimeout(() => {
      set({ toast: null });
    }, 3000);
  },
  hideToast: () => set({ toast: null }),

  // Actions
  resetAnalysis: () => {
    set({
      image: null,
      imageFile: null,
      imageHash: null,
      result: null,
      chatHistory: [initialChatMessage],
      chatSessionId: null,
      activeChatAiResultId: null,
      chatWidgetMode: 'general',
      view: 'upload',
    });
    pushViewPath('upload');
  },

  // Navigation guard: chuyển view an toàn
  navigateTo: (targetView) => {
    const { user, showToast } = get();
    if (PROTECTED_VIEWS.includes(targetView) && !user) {
      set({ view: 'login' });
      pushViewPath('login');
      showToast('Vui lòng đăng nhập để sử dụng tính năng này.', 'error');
      return;
    }
    if (user?.role === 'admin' && targetView !== 'admin-users') {
      set({ view: 'admin-users' });
      pushViewPath('admin-users');
      return;
    }
    if (targetView === 'admin-users' && user?.role !== 'admin') {
      set({ view: 'landing' });
      pushViewPath('landing');
      showToast('Bạn không có quyền truy cập trang quản trị.', 'error');
      return;
    }
    set({ view: targetView });
    pushViewPath(targetView);
  },
}));
