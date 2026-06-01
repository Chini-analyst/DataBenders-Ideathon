"use client";

import { useState } from "react";
import { DropZone } from "@/components/upload/DropZone";
import { UploadProgress } from "@/components/upload/UploadProgress";
import { UploadHistory } from "@/components/upload/UploadHistory";
import { useUpload } from "@/hooks/useUpload";
import { Upload, Database, Trash2, AlertTriangle, Loader2, X } from "lucide-react";

function ConfirmClearModal({
  onConfirm,
  onCancel,
  loading,
}: {
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={!loading ? onCancel : undefined}
      />
      {/* Dialog */}
      <div className="relative z-10 w-full max-w-md mx-4 bg-navy-900 border border-navy-600 rounded-2xl shadow-2xl p-6 animate-fade-in">
        <div className="flex items-start gap-4">
          <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-semibold text-slate-100">
              Clear all data?
            </h2>
            <p className="text-sm text-slate-400 mt-1.5 leading-relaxed">
              This will permanently delete{" "}
              <span className="text-slate-200 font-medium">all nodes and relationships</span>{" "}
              from Neo4j and{" "}
              <span className="text-slate-200 font-medium">all vector chunks</span>{" "}
              from ChromaDB. This action cannot be undone.
            </p>
          </div>
          {!loading && (
            <button
              onClick={onCancel}
              className="p-1 rounded-md text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-navy-800 border border-navy-600 text-slate-300 hover:text-slate-100 hover:border-navy-500 transition-all disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-red-600 hover:bg-red-500 text-white transition-all disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Clearing…
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                Yes, clear everything
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function UploadPage() {
  const {
    queue,
    history,
    loadingHistory,
    historyError,
    clearingAll,
    uploadFiles,
    deleteUpload,
    fetchHistory,
    clearQueue,
    clearAllData,
  } = useUpload();

  const [showConfirm, setShowConfirm] = useState(false);
  const [clearResult, setClearResult] = useState<string | null>(null);

  const handleClearConfirm = async () => {
    try {
      const result = await clearAllData();
      setClearResult(result.message);
      setShowConfirm(false);
      setTimeout(() => setClearResult(null), 6000);
    } catch (err) {
      setClearResult(
        `Error: ${err instanceof Error ? err.message : "Clear failed"}`
      );
      setShowConfirm(false);
    }
  };

  return (
    <>
      {showConfirm && (
        <ConfirmClearModal
          onConfirm={handleClearConfirm}
          onCancel={() => setShowConfirm(false)}
          loading={clearingAll}
        />
      )}

      <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
        {/* Page header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gold-500/10 border border-gold-500/20">
              <Upload className="w-6 h-6 text-gold-400" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-slate-100">
                Data Upload
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Upload documents to build your knowledge graph
              </p>
            </div>
          </div>

          {/* Clear all data button */}
          <button
            onClick={() => setShowConfirm(true)}
            disabled={clearingAll}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-navy-800 border border-navy-700 text-slate-400 hover:text-red-400 hover:border-red-800/60 hover:bg-red-900/10 transition-all disabled:opacity-50"
            title="Delete all data from Neo4j and ChromaDB"
          >
            {clearingAll ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
            Clear All Data
          </button>
        </div>

        {/* Clear result toast */}
        {clearResult && (
          <div
            className={`flex items-start gap-3 px-4 py-3 rounded-xl text-sm border animate-fade-in ${
              clearResult.startsWith("Error")
                ? "bg-red-900/20 border-red-800/50 text-red-300"
                : "bg-green-900/20 border-green-800/50 text-green-300"
            }`}
          >
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{clearResult}</span>
            <button
              onClick={() => setClearResult(null)}
              className="ml-auto text-current opacity-60 hover:opacity-100"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Supported formats */}
        <div className="flex flex-wrap gap-2">
          {["PDF", "DOCX", "XLSX", "CSV", "TXT", "MD"].map((fmt) => (
            <span
              key={fmt}
              className="px-2.5 py-1 text-xs font-medium rounded-full bg-navy-800 border border-navy-600 text-slate-300"
            >
              {fmt}
            </span>
          ))}
        </div>

        {/* Drop zone */}
        <DropZone onFilesSelected={uploadFiles} />

        {/* Upload queue progress */}
        {queue.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-300">
                Upload Queue ({queue.length})
              </h2>
              <button
                onClick={clearQueue}
                className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                Clear completed
              </button>
            </div>
            <div className="space-y-2">
              {queue.map((item, idx) => (
                <UploadProgress key={idx} item={item} />
              ))}
            </div>
          </div>
        )}

        {/* Upload history */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-gold-400" />
              <h2 className="text-sm font-medium text-slate-300">
                Ingested Documents
              </h2>
            </div>
            <button
              onClick={fetchHistory}
              className="text-xs text-slate-500 hover:text-gold-400 transition-colors"
            >
              Refresh
            </button>
          </div>
          <UploadHistory
            uploads={history}
            loading={loadingHistory}
            error={historyError}
            onDelete={deleteUpload}
          />
        </div>
      </div>
    </>
  );
}
