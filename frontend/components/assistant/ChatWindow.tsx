"use client";

import { useEffect, useRef, useState, KeyboardEvent } from "react";
import { ChatMessage } from "@/hooks/useChat";
import { Source } from "@/lib/api";
import { MessageBubble } from "./MessageBubble";
import { Bot, Send, Loader2 } from "lucide-react";

interface ChatWindowProps {
  messages: ChatMessage[];
  loading: boolean;
  onSendMessage: (question: string) => void;
  onShowSources: (sources: Source[]) => void;
}

export function ChatWindow({
  messages,
  loading,
  onSendMessage,
  onShowSources,
}: ChatWindowProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    onSendMessage(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-navy-900 border border-navy-700 rounded-xl overflow-hidden">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-16 h-16 rounded-2xl bg-gold-500/10 border border-gold-500/20 flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-gold-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-200 mb-1">
              StrategyShifu Assistant
            </h3>
            <p className="text-sm text-slate-500 max-w-sm">
              Upload your documents first, then ask anything about the data —
              people, roles, policies, or relationships across your knowledge graph.
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onShowSources={onShowSources}
              />
            ))}
            {loading && (
              <div className="flex gap-3 animate-fade-in">
                <div className="w-8 h-8 rounded-full bg-gold-500/10 border border-gold-500/20 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-gold-400" />
                </div>
                <div className="bg-navy-800 border border-navy-700 rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex items-center gap-2 text-slate-500">
                    <Loader2 className="w-4 h-4 animate-spin text-gold-400" />
                    <span className="text-sm">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-navy-700 p-4">
        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about employees, open roles, HR policies..."
            rows={1}
            disabled={loading}
            className="flex-1 resize-none bg-navy-800 border border-navy-600 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-gold-500/50 focus:ring-1 focus:ring-gold-500/20 transition-all disabled:opacity-50 max-h-32 overflow-y-auto"
            style={{
              height: "auto",
              minHeight: "44px",
            }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = "auto";
              target.style.height = `${Math.min(target.scrollHeight, 128)}px`;
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-3 rounded-xl bg-gold-500 hover:bg-gold-400 text-navy-950 font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        <p className="text-xs text-slate-700 mt-2 text-center">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
