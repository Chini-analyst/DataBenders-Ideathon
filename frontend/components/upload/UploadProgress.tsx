"use client";

import { FileText, CheckCircle, XCircle, Loader2, Clock } from "lucide-react";
import { clsx } from "clsx";

interface UploadItem {
  file: File;
  progress: number;
  status: "queued" | "uploading" | "processing" | "completed" | "failed";
  error?: string;
}

interface UploadProgressProps {
  item: UploadItem;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const STATUS_CONFIG = {
  queued: {
    icon: Clock,
    color: "text-slate-400",
    label: "Queued",
    barColor: "bg-slate-600",
  },
  uploading: {
    icon: Loader2,
    color: "text-blue-400",
    label: "Uploading",
    barColor: "bg-blue-500",
  },
  processing: {
    icon: Loader2,
    color: "text-gold-400",
    label: "Processing",
    barColor: "bg-gold-500",
  },
  completed: {
    icon: CheckCircle,
    color: "text-green-400",
    label: "Completed",
    barColor: "bg-green-500",
  },
  failed: {
    icon: XCircle,
    color: "text-red-400",
    label: "Failed",
    barColor: "bg-red-500",
  },
};

export function UploadProgress({ item }: UploadProgressProps) {
  const config = STATUS_CONFIG[item.status];
  const Icon = config.icon;
  const isAnimating = item.status === "uploading" || item.status === "processing";
  const progress =
    item.status === "completed"
      ? 100
      : item.status === "processing"
      ? 100
      : item.progress;

  return (
    <div className="p-3 rounded-lg bg-navy-800 border border-navy-600">
      <div className="flex items-center gap-3">
        <div className="p-1.5 rounded-md bg-navy-700">
          <FileText className="w-4 h-4 text-slate-400" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-medium text-slate-200 truncate">
              {item.file.name}
            </p>
            <div className={clsx("flex items-center gap-1.5 flex-shrink-0", config.color)}>
              <Icon
                className={clsx("w-3.5 h-3.5", isAnimating && "animate-spin")}
              />
              <span className="text-xs">{config.label}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 mt-1.5">
            <div className="flex-1 h-1.5 rounded-full bg-navy-700 overflow-hidden">
              <div
                className={clsx(
                  "h-full rounded-full transition-all duration-300",
                  config.barColor,
                  item.status === "processing" && "animate-pulse"
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs text-slate-500 flex-shrink-0">
              {formatBytes(item.file.size)}
            </span>
          </div>

          {item.error && (
            <p className="text-xs text-red-400 mt-1">{item.error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
