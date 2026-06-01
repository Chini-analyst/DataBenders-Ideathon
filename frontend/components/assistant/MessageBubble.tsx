"use client";

import { ChatMessage } from "@/hooks/useChat";
import { Source } from "@/lib/api";
import { Bot, User, ExternalLink, Clock } from "lucide-react";
import { clsx } from "clsx";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MessageBubbleProps {
  message: ChatMessage;
  onShowSources?: (sources: Source[]) => void;
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function MessageBubble({ message, onShowSources }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={clsx(
        "flex gap-3 animate-fade-in",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1",
          isUser
            ? "bg-navy-700 border border-navy-600"
            : "bg-gold-500/10 border border-gold-500/20"
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-slate-400" />
        ) : (
          <Bot className="w-4 h-4 text-gold-400" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={clsx(
          "max-w-[75%] rounded-2xl px-4 py-3",
          isUser
            ? "bg-navy-700 border border-navy-600 rounded-tr-sm"
            : message.error
            ? "bg-red-900/20 border border-red-800/50 rounded-tl-sm"
            : "bg-navy-800 border border-navy-700 rounded-tl-sm"
        )}
      >
        {isUser ? (
          <p className="text-sm text-slate-200 leading-relaxed">{message.content}</p>
        ) : (
          <div className="markdown-content text-sm text-slate-200">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Footer: sources + timings */}
        {!isUser && (message.sources?.length || message.timings) && (
          <div className="flex items-center justify-between gap-3 mt-3 pt-2 border-t border-navy-700">
            <div className="flex items-center gap-2">
              {message.sources && message.sources.length > 0 && onShowSources && (
                <button
                  onClick={() => onShowSources(message.sources!)}
                  className="flex items-center gap-1 text-xs text-gold-400/70 hover:text-gold-400 transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  {message.sources.length} source{message.sources.length !== 1 ? "s" : ""}
                </button>
              )}
              {message.mode && (
                <span className="text-xs text-slate-600 capitalize">
                  · {message.mode}
                </span>
              )}
            </div>
            {message.timings && (
              <div className="flex items-center gap-1 text-xs text-slate-600">
                <Clock className="w-3 h-3" />
                {formatMs(message.timings.total_ms)}
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        <p
          className={clsx(
            "text-xs mt-1",
            isUser ? "text-slate-600 text-right" : "text-slate-700"
          )}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}
