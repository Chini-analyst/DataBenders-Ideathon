"use client";

import { ChatWindow } from "@/components/assistant/ChatWindow";
import { SourcePanel } from "@/components/assistant/SourcePanel";
import { RetrievalModeToggle } from "@/components/assistant/RetrievalModeToggle";
import { useChat } from "@/hooks/useChat";
import { Bot, Trash2 } from "lucide-react";
import { useState } from "react";
import { Source } from "@/lib/api";

export default function AssistantPage() {
  const { messages, loading, mode, sendMessage, clearMessages, changeMode } =
    useChat();
  const [activeSources, setActiveSources] = useState<Source[]>([]);
  const [showSources, setShowSources] = useState(false);

  const handleShowSources = (sources: Source[]) => {
    setActiveSources(sources);
    setShowSources(true);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gold-500/10 border border-gold-500/20">
            <Bot className="w-6 h-6 text-gold-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-100">
              AI Assistant
            </h1>
            <p className="text-sm text-slate-400 mt-0.5">
              Query your knowledge base with natural language
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <RetrievalModeToggle mode={mode} onChange={changeMode} />
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-navy-800 border border-navy-600 text-slate-400 hover:text-red-400 hover:border-red-800/50 transition-all"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Chat + sources layout */}
      <div className="flex gap-4 flex-1 min-h-0">
        <div className={`flex flex-col ${showSources ? "flex-1" : "w-full"} min-w-0`}>
          <ChatWindow
            messages={messages}
            loading={loading}
            onSendMessage={sendMessage}
            onShowSources={handleShowSources}
          />
        </div>

        {showSources && (
          <SourcePanel
            sources={activeSources}
            onClose={() => setShowSources(false)}
          />
        )}
      </div>
    </div>
  );
}
