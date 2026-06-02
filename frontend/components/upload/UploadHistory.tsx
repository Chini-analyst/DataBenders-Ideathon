"use client";

import React, { useState } from "react";
import { UploadRecord } from "@/lib/api";
import {
  FileText,
  CheckCircle,
  XCircle,
  Loader2,
  Clock,
  Trash2,
  ChevronDown,
  ChevronUp,
  Database,
  GitFork,
  Layers,
} from "lucide-react";
import { clsx } from "clsx";

interface UploadHistoryProps {
  uploads: UploadRecord[];
  loading: boolean;
  error: string | null;
  onDelete: (id: string) => Promise<void>;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const STATUS_ICONS = {
  pending: { icon: Clock, color: "text-slate-400" },
  processing: { icon: Loader2, color: "text-gold-400", spin: true },
  completed: { icon: CheckCircle, color: "text-green-400" },
  failed: { icon: XCircle, color: "text-red-400" },
};

export function UploadHistory({
  uploads,
  loading,
  error,
  onDelete,
}: UploadHistoryProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-slate-500">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        Loading uploads...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-4 rounded-lg bg-red-900/20 border border-red-800/50 text-red-400 text-sm">
        <XCircle className="w-4 h-4 flex-shrink-0" />
        {error}
      </div>
    );
  }

  if (uploads.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-600 border border-dashed border-navy-700 rounded-xl">
        <FileText className="w-10 h-10 mb-3 opacity-40" />
        <p className="text-sm">No documents ingested yet</p>
        <p className="text-xs mt-1 text-slate-700">
          Upload files above to get started
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-navy-700 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-navy-800/80 border-b border-navy-700">
            <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
              File
            </th>
            <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
              Status
            </th>
            <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider hidden md:table-cell">
              Size
            </th>
            <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider hidden lg:table-cell">
              Uploaded
            </th>
            <th className="text-right px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-navy-700">
          {uploads.map((record) => {
            const statusConfig = STATUS_ICONS[record.status];
            const StatusIcon = statusConfig.icon;
            const isExpanded = expandedId === record.id;

            return (
              <React.Fragment key={record.id}>
              <tr
                  className="bg-navy-900/50 hover:bg-navy-800/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-500 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="font-medium text-slate-200 truncate max-w-[200px]">
                          {record.original_filename}
                        </p>
                        <p className="text-xs text-slate-600 uppercase">
                          {record.file_type}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div
                      className={clsx(
                        "flex items-center gap-1.5",
                        statusConfig.color
                      )}
                    >
                      <StatusIcon
                        className={clsx(
                          "w-3.5 h-3.5",
                          (statusConfig as any).spin && "animate-spin"
                        )}
                      />
                      <span className="capitalize text-xs">{record.status}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-400 hidden md:table-cell">
                    {formatBytes(record.file_size)}
                  </td>
                  <td className="px-4 py-3 text-slate-400 hidden lg:table-cell">
                    {formatDate(record.uploaded_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {record.status === "completed" && (
                        <button
                          onClick={() =>
                            setExpandedId(isExpanded ? null : record.id)
                          }
                          className="p-1.5 rounded-md text-slate-500 hover:text-slate-300 hover:bg-navy-700 transition-all"
                          title="View details"
                        >
                          {isExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5" />
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(record.id)}
                        disabled={deletingId === record.id}
                        className="p-1.5 rounded-md text-slate-500 hover:text-red-400 hover:bg-red-900/20 transition-all disabled:opacity-50"
                        title="Delete"
                      >
                        {deletingId === record.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
                {isExpanded && (
                  <tr className="bg-navy-800/30">
                    <td colSpan={5} className="px-4 py-3">
                      <div className="flex gap-6 text-xs">
                        <div className="flex items-center gap-1.5 text-slate-400">
                          <Layers className="w-3.5 h-3.5 text-blue-400" />
                          <span className="text-slate-500">Chunks:</span>
                          <span className="text-slate-200 font-medium">
                            {record.chunk_count}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 text-slate-400">
                          <Database className="w-3.5 h-3.5 text-gold-400" />
                          <span className="text-slate-500">Nodes:</span>
                          <span className="text-slate-200 font-medium">
                            {record.node_count}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 text-slate-400">
                          <GitFork className="w-3.5 h-3.5 text-purple-400" />
                          <span className="text-slate-500">Edges:</span>
                          <span className="text-slate-200 font-medium">
                            {record.edge_count}
                          </span>
                        </div>
                        {record.completed_at && (
                          <div className="text-slate-600">
                            Completed: {formatDate(record.completed_at)}
                          </div>
                        )}
                      </div>
                      {record.error_message && (
                        <p className="text-xs text-red-400 mt-2">
                          Error: {record.error_message}
                        </p>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
