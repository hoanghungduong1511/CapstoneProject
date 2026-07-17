'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ChevronDown,
  History,
  Loader2,
  MessageCircle,
  Plus,
  Send,
  Sparkles,
  Stethoscope,
  X,
} from 'lucide-react';
import { createChatSession, generateChatResponse } from '@/services/chat';
import { getDiagnosisHistory } from '@/services/user';
import { useAppStore } from '@/store/app-store';
import type { ChatWidgetMode } from '@/store/app-store';
import type { DiagnosisHistoryItem, Message, SkinAnalysisResponse } from '@/types';

const GENERAL_GREETING = `Xin chào. Tôi là Trợ lý Y khoa AI.

Hiện bạn chưa có kết quả phân tích ảnh da. Bạn có thể tải ảnh lên để tôi hỗ trợ giải thích kết quả, dấu hiệu cần lưu ý và thời điểm nên đi khám.

Thông tin tư vấn chỉ mang tính tham khảo, không thay thế bác sĩ.`;

const LOGIN_GREETING = `Xin chào. Tôi là Trợ lý Y khoa AI.

Bạn cần đăng nhập và phân tích ảnh da để tôi có thể tư vấn theo đúng kết quả của bạn.`;

const quickQuestions = [
  'Dấu hiệu của bệnh này là gì?',
  'Tôi nên chăm sóc thế nào?',
  'Khi nào cần đi khám?',
  'Bệnh này có lây không?',
  'Cho tôi nguồn tham khảo',
];

const formatTime = (date: Date) =>
  date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

const formatMessageContent = (value: string) => {
  const trimmed = value.trim();
  const capitalized = trimmed
    ? trimmed.charAt(0).toLocaleUpperCase('vi-VN') + trimmed.slice(1)
    : '';
  return escapeHtml(capitalized).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
};

function diseaseNameFromResult(result: SkinAnalysisResponse | null): string | null {
  if (!result) return null;
  return (
    result.classification?.candidates?.[0]?.name ||
    result.classification?.top_label ||
    result.validation.class_name ||
    null
  );
}

function contextGreeting(diseaseName: string | null): string {
  return `Xin chào. Tôi là Trợ lý Y khoa AI.

Kết quả phân tích hình ảnh ghi nhận dự đoán chính là **${diseaseName || 'tình trạng da đã phân tích'}**

Bạn có thể hỏi tôi về tình trạng này, cách chăm sóc da cơ bản và thời điểm nên đi khám. Thông tin tư vấn không thay thế chẩn đoán của bác sĩ.`;
}

function contextKey(mode: ChatWidgetMode, aiResultId: string | null) {
  return mode === 'result_context' && aiResultId ? `result:${aiResultId}` : 'general';
}

export function ChatWidget() {
  const {
    user,
    result,
    view,
    navigateTo,
    showToast,
    isChatWidgetOpen,
    chatWidgetMode,
    activeChatAiResultId,
    latestAiResultId,
    openChatWidget,
    closeChatWidget,
    openGeneralChat,
    openChatForResult,
    openResultSelector,
  } = useAppStore();

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [historyItems, setHistoryItems] = useState<DiagnosisHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [selectedHistoryItem, setSelectedHistoryItem] =
    useState<DiagnosisHistoryItem | null>(null);
  const [messagesByContext, setMessagesByContext] = useState<Record<string, Message[]>>({});
  const sessionByContextRef = useRef<Record<string, string>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isAdmin = user?.role === 'admin';
  const activeAiResultId =
    activeChatAiResultId || result?.ai_result_id || latestAiResultId || null;
  const activeCurrentResult =
    result?.ai_result_id && result.ai_result_id === activeAiResultId ? result : null;
  const selectedSummary =
    selectedHistoryItem?.id === activeAiResultId ? selectedHistoryItem : null;
  const diseaseName =
    diseaseNameFromResult(activeCurrentResult) ||
    selectedSummary?.top1_label ||
    diseaseNameFromResult(result);
  const currentMode: ChatWidgetMode =
    chatWidgetMode === 'result_context' && activeAiResultId
      ? 'result_context'
      : chatWidgetMode === 'result_selector'
        ? 'result_selector'
        : 'general';
  const key = contextKey(currentMode, activeAiResultId);
  const messages = messagesByContext[key] || [];

  const hasAnalysis = Boolean(activeAiResultId || result?.ai_result_id || latestAiResultId);
  const canSend = Boolean(user) && !isTyping && input.trim().length > 0;

  const initialMessage = useMemo<Message>(() => {
    if (!user) {
      return {
        id: 'login-greeting',
        role: 'ai',
        content: LOGIN_GREETING,
        timestamp: new Date(),
      };
    }
    return {
      id: `${key}-greeting`,
      role: 'ai',
      content:
        currentMode === 'result_context'
          ? contextGreeting(diseaseName)
          : GENERAL_GREETING,
      timestamp: new Date(),
    };
  }, [currentMode, diseaseName, key, user]);

  useEffect(() => {
    if (!isChatWidgetOpen) return;
    setMessagesByContext((prev) => {
      if (prev[key]?.length) return prev;
      return { ...prev, [key]: [initialMessage] };
    });
  }, [initialMessage, isChatWidgetOpen, key]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isTyping, currentMode]);

  useEffect(() => {
    if (!isChatWidgetOpen || currentMode !== 'result_selector' || !user) return;
    setIsLoadingHistory(true);
    getDiagnosisHistory(0, 10)
      .then((data) => setHistoryItems(data.items))
      .catch(() => showToast('Không thể tải danh sách lịch sử phân tích.', 'error'))
      .finally(() => setIsLoadingHistory(false));
  }, [currentMode, isChatWidgetOpen, showToast, user]);

  if (isAdmin) return null;

  const appendMessage = (chatKey: string, message: Message) => {
    setMessagesByContext((prev) => ({
      ...prev,
      [chatKey]: [...(prev[chatKey] || [initialMessage]), message],
    }));
  };

  const handleAnalyzeClick = () => {
    closeChatWidget();
    navigateTo('upload');
  };

  const handleOpen = () => {
    if (result?.ai_result_id) {
      openChatForResult(result.ai_result_id);
      return;
    }
    openChatWidget();
  };

  const handleSelectResult = (item: DiagnosisHistoryItem) => {
    setSelectedHistoryItem(item);
    openChatForResult(item.id);
  };

  const handleSend = async (messageText?: string) => {
    const text = (messageText || input).trim();
    if (!text || !user) return;

    const chatKey = key;
    const userMessage: Message = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    appendMessage(chatKey, userMessage);
    setInput('');
    setIsTyping(true);

    try {
      let sessionId = sessionByContextRef.current[chatKey];
      if (!sessionId) {
        const session = await createChatSession(
          currentMode === 'result_context' ? activeAiResultId || undefined : undefined,
          (messagesByContext[chatKey] || [initialMessage])[0]?.content,
        );
        sessionId = session.id;
        sessionByContextRef.current[chatKey] = session.id;
      }

      const response = await generateChatResponse(
        sessionId,
        text,
        currentMode === 'result_context' ? activeAiResultId : null,
      );

      appendMessage(chatKey, {
        id: response.message_id,
        role: 'ai',
        content: response.answer,
        timestamp: new Date(),
      });
    } catch {
      appendMessage(chatKey, {
        id: `${Date.now()}-error`,
        role: 'ai',
        content:
          currentMode === 'general'
            ? 'Hiện tôi chưa thể kết nối dịch vụ tư vấn. Bạn vẫn có thể phân tích ảnh trước để hệ thống tạo ngữ cảnh chính xác hơn.'
            : 'Không thể kết nối với trợ lý y khoa. Vui lòng thử lại.',
        timestamp: new Date(),
      });
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <>
      {!isChatWidgetOpen && (
        <button
          type="button"
          onClick={handleOpen}
          className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-teal-700 text-white shadow-[0_14px_36px_rgba(15,118,110,0.24)] transition hover:-translate-y-0.5 hover:bg-teal-800 md:bottom-8 md:right-8 md:h-14 md:w-14"
          aria-label="Mở trợ lý y khoa AI"
        >
          <Stethoscope className="h-6 w-6" />
          {hasAnalysis && (
            <span className="absolute right-1 top-1 h-3 w-3 rounded-full border-2 border-white bg-emerald-400" />
          )}
        </button>
      )}

      {isChatWidgetOpen && (
        <section className="fixed bottom-3 right-3 z-50 flex h-[min(720px,calc(100vh-96px))] w-[min(440px,calc(100vw-24px))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl md:bottom-8 md:right-8">
          <header className="border-b border-slate-200 bg-slate-50 px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-700 text-white">
                  <Stethoscope className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-bold text-slate-950">
                    Trợ lý Y khoa AI
                  </h3>
                  <p className="truncate text-xs text-slate-500">
                    {currentMode === 'result_context'
                      ? `Đang tư vấn theo: ${diseaseName || 'kết quả phân tích'}`
                      : 'Hỗ trợ thông tin da liễu tham khảo'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {hasAnalysis && currentMode !== 'result_selector' && (
                  <button
                    type="button"
                    onClick={openResultSelector}
                    className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:text-teal-700"
                    title="Đổi kết quả phân tích"
                  >
                    <History className="h-4 w-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={closeChatWidget}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:text-slate-900"
                  aria-label="Đóng chat"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {currentMode === 'result_context' && (
              <button
                type="button"
                onClick={openResultSelector}
                className="mt-3 flex w-full items-center justify-between rounded-lg border border-teal-100 bg-teal-50 px-3 py-2 text-left text-xs text-teal-800"
              >
                <span className="truncate">
                  Context: {diseaseName || 'Kết quả phân tích hiện tại'}
                </span>
                <ChevronDown className="h-4 w-4 shrink-0" />
              </button>
            )}
          </header>

          {currentMode === 'result_selector' ? (
            <div className="flex-1 overflow-y-auto bg-slate-50 p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-slate-950">Chọn kết quả tư vấn</h4>
                  <p className="mt-1 text-xs text-slate-500">
                    Mỗi kết quả phân tích sẽ có phiên tư vấn riêng.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={openGeneralChat}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:text-teal-700"
                >
                  Chat chung
                </button>
              </div>

              {isLoadingHistory ? (
                <div className="flex h-40 items-center justify-center text-slate-500">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Đang tải lịch sử...
                </div>
              ) : historyItems.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white p-5 text-center">
                  <Sparkles className="mx-auto h-7 w-7 text-teal-700" />
                  <p className="mt-3 text-sm font-semibold text-slate-900">
                    Chưa có kết quả phân tích
                  </p>
                  <button
                    type="button"
                    onClick={handleAnalyzeClick}
                    className="mt-4 rounded-lg bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800"
                  >
                    Phân tích ảnh ngay
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {historyItems.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => handleSelectResult(item)}
                      className="flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 text-left transition hover:border-teal-200 hover:bg-teal-50"
                    >
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt=""
                          className="h-12 w-12 rounded-lg object-cover"
                        />
                      ) : (
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-100 text-slate-400">
                          <Stethoscope className="h-5 w-5" />
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-bold text-slate-900">
                          {item.top1_label || 'Kết quả phân tích'}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {new Date(item.created_at).toLocaleDateString('vi-VN')}
                          {item.top1_confidence != null &&
                            ` · ${(item.top1_confidence * 100).toFixed(1)}%`}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="flex-1 overflow-y-auto bg-slate-50 p-4">
                <div className="flex flex-col gap-3">
                  {(messages.length ? messages : [initialMessage]).map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[86%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                          message.role === 'user'
                            ? 'rounded-br-sm bg-teal-700 text-white'
                            : 'rounded-bl-sm border border-slate-200 bg-white text-slate-900'
                        }`}
                      >
                        <div
                          className="whitespace-pre-wrap break-words leading-6 [&_strong]:font-bold"
                          dangerouslySetInnerHTML={{
                            __html: formatMessageContent(message.content),
                          }}
                        />
                        <span className="mt-2 block text-[10px] opacity-60">
                          {formatTime(message.timestamp)}
                        </span>
                      </div>
                    </div>
                  ))}

                  {isTyping && (
                    <div className="flex justify-start">
                      <div className="rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
                        <div className="flex gap-1.5">
                          <span className="h-2 w-2 animate-bounce rounded-full bg-teal-700" />
                          <span className="h-2 w-2 animate-bounce rounded-full bg-teal-700 [animation-delay:150ms]" />
                          <span className="h-2 w-2 animate-bounce rounded-full bg-teal-700 [animation-delay:300ms]" />
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              <div className="border-t border-slate-200 bg-white p-3">
                {currentMode === 'result_context' && (
                  <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                    {quickQuestions.map((question) => (
                      <button
                        key={question}
                        type="button"
                        onClick={() => handleSend(question)}
                        disabled={isTyping || !user}
                        className="shrink-0 rounded-full border border-teal-100 bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-800 disabled:opacity-50"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                )}

                {!user && (
                  <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    Vui lòng đăng nhập để lưu và sử dụng phiên tư vấn.
                  </div>
                )}

                {currentMode === 'general' && user && (
                  <div className="mb-3 flex gap-2">
                    <button
                      type="button"
                      onClick={handleAnalyzeClick}
                      className="flex items-center gap-1.5 rounded-lg bg-teal-700 px-3 py-2 text-xs font-bold text-white hover:bg-teal-800"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Phân tích ảnh ngay
                    </button>
                    <button
                      type="button"
                      onClick={openResultSelector}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:text-teal-700"
                    >
                      Chọn lịch sử
                    </button>
                  </div>
                )}

                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    handleSend();
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    disabled={!user}
                    placeholder={
                      user
                        ? 'Hỏi về tình trạng của bạn...'
                        : 'Đăng nhập để tư vấn...'
                    }
                    className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:opacity-60"
                  />
                  <button
                    type="submit"
                    disabled={!canSend}
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-700 text-white transition hover:bg-teal-800 disabled:bg-slate-200 disabled:text-slate-400"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </form>
              </div>
            </>
          )}
        </section>
      )}
    </>
  );
}
