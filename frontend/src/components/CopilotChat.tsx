import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Bot, User, AlertTriangle, ChevronDown } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: string[];
  intent?: string;
  districts?: string[];
  mode?: string;
  timestamp: Date;
}

const SUGGESTED_QUESTIONS = [
  "Why is Nalbari red?",
  "Show all red alert districts",
  "What are the blend weights for Kamrup?",
  "LOMO sensitivity for Barpeta",
  "How accurate is the blend?",
  "How many people are exposed in Darrang?",
  "Model disagreement for Baksa",
  "Rainfall forecast for Goalpara",
];

export const CopilotChat: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'system',
      content: 'I am the **ForeBlendCast Copilot** — a grounded forecasting assistant. I only answer with numbers from the actual blend results. I never invent warnings.\n\nTry asking me:\n• "Why is Nalbari red?"\n• "Show all red alert districts"\n• "What are the blend weights for Kamrup?"',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSend = async (questionOverride?: string) => {
    const question = questionOverride || input.trim();
    if (!question) return;

    const userMsg: Message = {
      role: 'user',
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/copilot/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, lead_day: 1 }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const data = await res.json();

      const assistantMsg: Message = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        intent: data.intent_detected,
        districts: data.districts_matched,
        mode: data.mode,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: Message = {
        role: 'assistant',
        content: 'Could not reach the API server. Make sure `uvicorn api.main:app` is running on port 8000.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Simple markdown-ish renderer for bold and bullet points
  const renderContent = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, i) => {
      // Replace **text** with <strong>
      const parts = line.split(/(\*\*.*?\*\*)/g);
      const rendered = parts.map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={j} className="font-semibold text-textMain">{part.slice(2, -2)}</strong>;
        }
        return <span key={j}>{part}</span>;
      });

      // Table rows
      if (line.startsWith('|') && line.endsWith('|')) {
        const cells = line.split('|').filter(Boolean).map((c) => c.trim());
        if (cells.every((c) => /^[-:]+$/.test(c))) return null; // separator row
        return (
          <div key={i} className="flex gap-2 text-[10px] font-mono py-0.5 border-b border-border/40">
            {cells.map((cell, ci) => (
              <span key={ci} className={`flex-1 ${ci === 0 ? 'font-semibold' : ''}`}>{cell}</span>
            ))}
          </div>
        );
      }

      // Bullet points
      if (line.trim().startsWith('•') || line.trim().startsWith('→')) {
        return <p key={i} className="text-[11px] leading-relaxed pl-2 py-0.5">{rendered}</p>;
      }

      // Empty lines
      if (!line.trim()) return <div key={i} className="h-1.5" />;

      return <p key={i} className="text-[11px] leading-relaxed">{rendered}</p>;
    });
  };

  return (
    <>
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-[9999] w-14 h-14 bg-brand-forest hover:bg-brand-darkGreen text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center group hover:scale-105 active:scale-95"
          title="Open Forecaster Copilot"
        >
          <MessageCircle size={24} className="group-hover:scale-110 transition-transform" />
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-tier-red rounded-full animate-pulse" />
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-[9999] w-[420px] h-[600px] bg-surface rounded-2xl shadow-2xl border border-border flex flex-col overflow-hidden animate-in slide-in-from-bottom-4">
          {/* Header */}
          <div className="bg-brand-forest text-white px-4 py-3 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                <Bot size={18} />
              </div>
              <div>
                <h3 className="text-sm font-bold leading-tight">Forecaster Copilot</h3>
                <p className="text-[10px] text-emerald-100 leading-tight">Grounded in results/ data only</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* EXERCISE disclaimer bar */}
          <div className="bg-amber-50 border-b border-amber-200 px-3 py-1.5 flex items-center gap-2 flex-shrink-0">
            <AlertTriangle size={13} className="text-amber-600 flex-shrink-0" />
            <span className="text-[9.5px] text-amber-700 font-medium">
              EXERCISE — Prototype output. Not an official IMD warning.
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-3 space-y-3">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role !== 'user' && (
                  <div className="w-6 h-6 bg-emerald-100 text-brand-forest rounded-md flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Bot size={14} />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-xl px-3 py-2.5 ${
                    msg.role === 'user'
                      ? 'bg-brand-forest text-white rounded-br-sm'
                      : msg.role === 'system'
                      ? 'bg-emerald-50 border border-emerald-200 rounded-bl-sm'
                      : 'bg-surfaceHighlight border border-border rounded-bl-sm'
                  }`}
                >
                  <div className={msg.role === 'user' ? 'text-[11.5px] leading-relaxed' : ''}>
                    {msg.role === 'user' ? msg.content : renderContent(msg.content)}
                  </div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-1.5 border-t border-border/50">
                      <span className="text-[9px] text-textLight font-semibold uppercase tracking-wider">
                        Sources: {msg.sources.join(', ')}
                      </span>
                    </div>
                  )}
                  {(msg.intent || msg.mode) && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {msg.intent && (
                        <span className="text-[9px] bg-emerald-100 text-brand-forest px-1.5 py-0.5 rounded font-mono">
                          tool:{msg.intent}
                        </span>
                      )}
                      {msg.districts && msg.districts.length > 0 && (
                        <span className="text-[9px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-mono">
                          match:{msg.districts.join(',')}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="w-6 h-6 bg-brand-forest text-white rounded-md flex items-center justify-center flex-shrink-0 mt-0.5">
                    <User size={14} />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-2">
                <div className="w-6 h-6 bg-emerald-100 text-brand-forest rounded-md flex items-center justify-center flex-shrink-0">
                  <Bot size={14} />
                </div>
                <div className="bg-surfaceHighlight border border-border rounded-xl px-3 py-2.5 rounded-bl-sm">
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 bg-brand-forest rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 bg-brand-forest rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 bg-brand-forest rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    <span className="text-[10px] text-textMuted ml-1.5">Querying results/...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggested questions */}
          {messages.length <= 2 && (
            <div className="px-3 pb-2 flex-shrink-0">
              <div className="flex items-center gap-1.5 mb-1.5">
                <ChevronDown size={12} className="text-textLight" />
                <span className="text-[9px] text-textLight font-semibold uppercase tracking-wider">Suggested questions</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {SUGGESTED_QUESTIONS.slice(0, 4).map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="text-[10px] px-2.5 py-1.5 bg-emerald-50 text-brand-forest border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors font-medium"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="border-t border-border px-3 py-2.5 flex-shrink-0 bg-surface">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about any district forecast..."
                className="flex-1 text-xs bg-surfaceHighlight border border-border rounded-lg px-3 py-2.5 outline-none focus:ring-2 focus:ring-brand-forest/30 focus:border-brand-forest/40 transition-all placeholder:text-textLight"
                disabled={isLoading}
              />
              <button
                onClick={() => handleSend()}
                disabled={isLoading || !input.trim()}
                className="p-2.5 bg-brand-forest text-white rounded-lg hover:bg-brand-darkGreen transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
              >
                <Send size={15} />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
