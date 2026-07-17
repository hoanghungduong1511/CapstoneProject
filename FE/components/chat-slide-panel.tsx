'use client';

import { useState, useEffect, useRef } from 'react';
import { X, Send, Stethoscope, AlertCircle } from 'lucide-react';
import type { Message, MedicalContext, SkinAnalysisResponse } from '@/types';
import {
  buildMedicalContext,
  generateInitialGreeting,
} from '@/services/chat-context';
import { createChatSession, generateChatResponse } from '@/services/chat';
import { useAppStore } from '@/store/app-store';

interface ChatSlidePanelProps {
  isOpen: boolean;
  onClose: () => void;
  result: SkinAnalysisResponse;
}


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

export function ChatSlidePanel({ isOpen, onClose, result }: ChatSlidePanelProps) {
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [medicalContext, setMedicalContext] = useState<MedicalContext | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef<string | null>(null);
  const isInitializingRef = useRef(false);
  const activeResultIdRef = useRef<string | null>(null);
  const { showToast } = useAppStore();

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory, isTyping]);

  useEffect(() => {
    const nextResultId = result?.ai_result_id || null;
    if (!nextResultId || activeResultIdRef.current === nextResultId) {
      return;
    }
    activeResultIdRef.current = nextResultId;
    sessionIdRef.current = null;
    isInitializingRef.current = false;
    setChatHistory([]);
    setMedicalContext(null);
  }, [result?.ai_result_id]);

  // Initialize context and greeting when panel opens
  useEffect(() => {
    if (isOpen && chatHistory.length === 0 && result && !isInitializingRef.current) {
      isInitializingRef.current = true;
      const context = buildMedicalContext(result);
      setMedicalContext(context);

      const greeting = generateInitialGreeting(context);
      setChatHistory([
        {
          id: 'init',
          role: 'ai',
          content: greeting,
          timestamp: new Date(),
        },
      ]);
      createChatSession(result.ai_result_id, greeting)
        .then((session) => {
          sessionIdRef.current = session.id;
        })
        .catch(() => {
          showToast('Không thể khởi tạo lịch sử tư vấn.', 'error');
        })
        .finally(() => {
          isInitializingRef.current = false;
        });
    }
  }, [isOpen, result, chatHistory.length, showToast]);

  const handleChatSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !medicalContext) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: chatInput,
      timestamp: new Date(),
    };
    setChatHistory((prev) => [...prev, userMsg]);
    setChatInput('');
    setIsTyping(true);

    let activeSessionId = sessionIdRef.current;
    try {
      if (!activeSessionId) {
        const session = await createChatSession(
          result.ai_result_id,
          chatHistory[0]?.content,
        );
        activeSessionId = session.id;
        sessionIdRef.current = session.id;
      }
      const response = await generateChatResponse(
        activeSessionId,
        userMsg.content,
        result.ai_result_id,
      );

      const aiMsg: Message = {
        id: response.message_id,
        role: 'ai',
        content: response.answer,
        timestamp: new Date(),
      };

      setChatHistory((prev) => [...prev, aiMsg]);
    } catch {
      showToast('Không thể kết nối với trợ lý y khoa. Vui lòng thử lại.', 'error');
    } finally {
      setIsTyping(false);
    }
  };


  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-foreground/20 backdrop-blur-sm z-40 transition-opacity animate-in fade-in"
          onClick={onClose}
        />
      )}

      {/* Slide Panel */}
      <div
        className={`fixed inset-y-0 right-0 w-full md:w-[480px] bg-card shadow-2xl transform transition-transform duration-300 ease-in-out z-50 flex flex-col border-l border-border ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-border bg-secondary">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 border border-primary/20 rounded-xl flex items-center justify-center text-primary">
                <Stethoscope className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-foreground text-sm">Trợ lý Y khoa AI</h3>
                <p className="text-xs text-muted-foreground">Context-aware Medical Assistant</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 bg-card border border-border rounded-lg text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 bg-background">
          {chatHistory.map((msg) => (
            <div key={msg.id} className={`flex min-w-0 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`min-w-0 max-w-[85%] overflow-hidden rounded-2xl p-4 shadow-sm text-sm ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-br-sm'
                    : 'bg-card text-foreground border border-border rounded-bl-sm'
                }`}
              >
                <div
                  className="leading-relaxed whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word] [&_strong]:font-bold"
                  dangerouslySetInnerHTML={{
                    __html: formatMessageContent(msg.content),
                  }}
                />
                <span
                  className={`text-[10px] mt-2 block font-medium opacity-60 ${
                    msg.role === 'user' ? 'text-right' : ''
                  }`}
                >
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-card border border-border rounded-2xl rounded-bl-sm p-4 shadow-sm">
                <div className="flex gap-1.5 items-center h-4">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} className="h-2" />
        </div>

        {/* Disclaimer */}
        <div className="px-4 py-2 bg-warning/10 border-t border-warning/20">
          <p className="text-[10px] text-warning flex items-center gap-1.5">
            <AlertCircle className="w-3 h-3 shrink-0" />
            Thông tin chỉ mang tính tham khảo. Vui lòng tham vấn bác sĩ để được chẩn đoán chính xác.
          </p>
        </div>

        {/* Input */}
        <form onSubmit={handleChatSend} className="p-4 bg-card border-t border-border">
          <div className="relative flex items-center gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Hỏi về tình trạng của bạn..."
              className="flex-1 bg-secondary border border-border rounded-xl pl-4 pr-4 py-3 focus:ring-2 focus:ring-primary focus:border-transparent text-foreground text-sm outline-none"
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || isTyping}
              className="p-3 bg-primary hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground text-primary-foreground rounded-xl transition-colors shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

