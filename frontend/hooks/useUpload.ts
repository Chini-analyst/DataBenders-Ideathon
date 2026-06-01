"use client";

import { useState, useCallback, useEffect } from "react";
import { api, UploadRecord } from "@/lib/api";

interface UploadItem {
  file: File;
  progress: number;
  status: "queued" | "uploading" | "processing" | "completed" | "failed";
  error?: string;
  record?: UploadRecord;
}

export function useUpload() {
  const [queue, setQueue] = useState<UploadItem[]>([]);
  const [history, setHistory] = useState<UploadRecord[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [clearingAll, setClearingAll] = useState(false);

  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const res = await api.listUploads();
      setHistory(res.uploads);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Failed to load uploads");
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const uploadFiles = useCallback(
    async (files: File[]) => {
      const newItems: UploadItem[] = files.map((file) => ({
        file,
        progress: 0,
        status: "queued",
      }));

      setQueue((prev) => [...prev, ...newItems]);

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const queueIndex = queue.length + i;

        setQueue((prev) =>
          prev.map((item, idx) =>
            idx === queueIndex ? { ...item, status: "uploading" } : item
          )
        );

        try {
          const response = await api.uploadFile(file, (pct) => {
            setQueue((prev) =>
              prev.map((item, idx) =>
                idx === queueIndex ? { ...item, progress: pct } : item
              )
            );
          });

          setQueue((prev) =>
            prev.map((item, idx) =>
              idx === queueIndex
                ? {
                    ...item,
                    progress: 100,
                    status: "processing",
                    record: response.record ?? undefined,
                  }
                : item
            )
          );

          // Poll for completion
          if (response.record) {
            pollStatus(response.record.id, queueIndex);
          }
        } catch (err) {
          setQueue((prev) =>
            prev.map((item, idx) =>
              idx === queueIndex
                ? {
                    ...item,
                    status: "failed",
                    error: err instanceof Error ? err.message : "Upload failed",
                  }
                : item
            )
          );
        }
      }
    },
    [queue.length]
  );

  const pollStatus = useCallback(
    async (recordId: string, queueIndex: number) => {
      const maxAttempts = 30;
      let attempts = 0;

      const poll = async () => {
        if (attempts >= maxAttempts) return;
        attempts++;

        try {
          const record = await api.getUpload(recordId);
          if (record.status === "completed" || record.status === "failed") {
            setQueue((prev) =>
              prev.map((item, idx) =>
                idx === queueIndex
                  ? {
                      ...item,
                      status: record.status as UploadItem["status"],
                      record,
                      error: record.error_message ?? undefined,
                    }
                  : item
              )
            );
            fetchHistory();
          } else {
            setTimeout(poll, 2000);
          }
        } catch {
          setTimeout(poll, 3000);
        }
      };

      setTimeout(poll, 2000);
    },
    [fetchHistory]
  );

  const deleteUpload = useCallback(
    async (id: string) => {
      try {
        await api.deleteUpload(id);
        setHistory((prev) => prev.filter((r) => r.id !== id));
      } catch (err) {
        throw err;
      }
    },
    []
  );

  const clearQueue = useCallback(() => {
    setQueue((prev) => prev.filter((item) => item.status === "processing" || item.status === "uploading"));
  }, []);

  const clearAllData = useCallback(async () => {
    setClearingAll(true);
    try {
      const result = await api.clearAllData();
      setHistory([]);
      setQueue([]);
      return result;
    } finally {
      setClearingAll(false);
    }
  }, []);

  return {
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
  };
}
