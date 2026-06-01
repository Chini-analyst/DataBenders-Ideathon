"use client";

import { useState, useCallback, useRef } from "react";
import { api, QueryResponse, Source } from "@/lib/api";

export type RetrievalMode = "semantic" | "graph" | "hybrid";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  mode?: RetrievalMode;
  timings?: {
    retrieval_ms: number;
    generation_ms: number;
    total_ms: number;
  };
  timestamp: Date;
  error?: boolean;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<RetrievalMode>("hybrid");
  const [topK, setTopK] = useState(5);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || loading) return;

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const response = await api.query({
          question: question.trim(),
          mode,
          top_k: topK,
        });

        const assistantMsg: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          mode: response.mode as RetrievalMode,
          timings: {
            retrieval_ms: response.retrieval_time_ms,
            generation_ms: response.generation_time_ms,
            total_ms: response.total_time_ms,
          },
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errorMsg: ChatMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          content:
            err instanceof Error
              ? `Error: ${err.message}`
              : "An unexpected error occurred. Please try again.",
          timestamp: new Date(),
          error: true,
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setLoading(false);
      }
    },
    [loading, mode, topK]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const changeMode = useCallback((newMode: RetrievalMode) => {
    setMode(newMode);
  }, []);

  return {
    messages,
    loading,
    mode,
    topK,
    sendMessage,
    clearMessages,
    changeMode,
    setTopK,
  };
}
