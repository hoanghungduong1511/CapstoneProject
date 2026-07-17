'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Send, Stethoscope } from 'lucide-react';
import { createChatSession, generateChatResponse } from '@/services/chat';
import { useAppStore } from '@/store/app-store';
import type { Message } from '@/types';

const formatMessageText = (value: string) => {
  const trimmed = value.trim();
  return trimmed
    ? trimmed.charAt(0).toLocaleUpperCase('vi-VN') + trimmed.slice(1)
    : '';
};

export function ChatView() {
  const {
    result,
    chatHistory,
    chatSessionId,
    setChatHistory,
    setChatSessionId,
    setView,
    showToast,
  } = useAppStore();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory, isTyping]);

  const resultLabel = result
    ? result.validation.class_name === 'person_skin'
      ? 'Phân tích vùng da'
      : result.validation.class_name
    : 'Tổng quát';

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };
    setChatHistory((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    if (!result?.ai_result_id) {
      showToast('Vui lòng phân tích ảnh trước khi tư vấn AI.', 'error');
      setIsTyping(false);
      return;
    }

    let activeSessionId = chatSessionId;
    try {
      if (!activeSessionId) {
        const session = await createChatSession(
          result?.ai_result_id,
          chatHistory[0]?.content,
        );
        activeSessionId = session.id;
        setChatSessionId(session.id);
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
    <div className="flex-1 w-full max-w-5xl mx-auto py-8 px-4 h-full flex flex-col">
      <div className="flex-1 flex flex-col bg-card rounded-3xl shadow-md border border-border overflow-hidden min-h-[600px] max-h-[80vh] relative">
        <div
          className="absolute inset-0 z-0 opacity-[0.08] pointer-events-none bg-cover bg-center"
          style={{
            backgroundImage: 'url("https://images.unsplash.com/photo-1551076805-e1869033e561?auto=format&fit=crop&w=1200&q=80")',
          }}
        />

        <div className="p-4 border-b border-border bg-card/80 backdrop-blur-md flex items-center justify-between relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center text-primary-foreground shadow-sm">
              <Stethoscope className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-bold text-foreground text-lg">Trợ lý Da liễu AI</h3>
              <p className="text-xs text-muted-foreground flex items-center mt-0.5">
                <span className="w-2 h-2 rounded-full bg-success mr-1.5" />
                Phân tích nhắm mục tiêu: {resultLabel}
              </p>
            </div>
          </div>
          <button
            onClick={() => (result ? setView('result') : setView('landing'))}
            className="p-2.5 bg-card border border-border rounded-xl text-muted-foreground hover:bg-secondary transition-colors shadow-sm"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 bg-transparent relative z-10">
          {chatHistory.map((msg) => (
            <div key={msg.id} className={`flex min-w-0 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`min-w-0 max-w-[85%] overflow-hidden rounded-2xl p-5 shadow-sm text-[15px] ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-br-sm'
                    : 'bg-card text-foreground border border-border rounded-bl-sm shadow-md'
                }`}
              >
                <p className="leading-relaxed whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word]">
                  {formatMessageText(msg.content)}
                </p>
                <span
                  className={`text-[11px] mt-3 block font-medium opacity-60 ${msg.role === 'user' ? 'text-right' : ''}`}
                >
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-card border border-border rounded-2xl rounded-bl-sm p-4 shadow-md">
                <div className="flex gap-1.5 items-center h-4">
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} className="h-2" />
        </div>

        <div className="p-6 bg-card/80 backdrop-blur-md border-t border-border relative z-10">
          <form onSubmit={handleSend} className="relative flex items-center bg-card rounded-xl shadow-sm border border-border">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Nhập câu hỏi của bạn tại đây..."
              className="flex-1 bg-transparent pl-4 pr-12 py-3.5 text-foreground text-[15px] outline-none placeholder-muted-foreground"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="absolute right-2 p-2 bg-primary text-primary-foreground rounded-lg transition-colors hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
