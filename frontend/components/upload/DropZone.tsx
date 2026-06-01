"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, AlertCircle } from "lucide-react";
import { clsx } from "clsx";

const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "application/vnd.ms-excel": [".xls"],
  "text/csv": [".csv"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
};

interface DropZoneProps {
  onFilesSelected: (files: File[]) => void;
  maxSizeMB?: number;
}

export function DropZone({ onFilesSelected, maxSizeMB = 50 }: DropZoneProps) {
  const [rejectedFiles, setRejectedFiles] = useState<string[]>([]);

  const onDrop = useCallback(
    (accepted: File[], rejected: any[]) => {
      setRejectedFiles(rejected.map((r) => r.file.name));
      if (accepted.length > 0) {
        onFilesSelected(accepted);
      }
    },
    [onFilesSelected]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: maxSizeMB * 1024 * 1024,
    multiple: true,
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={clsx(
          "relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200",
          isDragActive && !isDragReject
            ? "border-gold-400 bg-gold-500/5 scale-[1.01]"
            : isDragReject
            ? "border-red-500 bg-red-900/10"
            : "border-navy-600 bg-navy-900/50 hover:border-gold-500/50 hover:bg-navy-800/50"
        )}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-4">
          <div
            className={clsx(
              "w-16 h-16 rounded-2xl flex items-center justify-center transition-all",
              isDragActive && !isDragReject
                ? "bg-gold-500/20 text-gold-400"
                : "bg-navy-800 text-slate-500"
            )}
          >
            {isDragReject ? (
              <AlertCircle className="w-8 h-8 text-red-400" />
            ) : (
              <Upload className="w-8 h-8" />
            )}
          </div>

          {isDragActive && !isDragReject ? (
            <div>
              <p className="text-lg font-medium text-gold-400">Drop files here</p>
              <p className="text-sm text-slate-400 mt-1">Release to upload</p>
            </div>
          ) : isDragReject ? (
            <div>
              <p className="text-lg font-medium text-red-400">Unsupported file type</p>
              <p className="text-sm text-slate-400 mt-1">
                Please use PDF, DOCX, XLSX, CSV, TXT, or MD files
              </p>
            </div>
          ) : (
            <div>
              <p className="text-lg font-medium text-slate-200">
                Drag & drop files here
              </p>
              <p className="text-sm text-slate-400 mt-1">
                or{" "}
                <span className="text-gold-400 hover:text-gold-300 underline underline-offset-2">
                  browse to select
                </span>
              </p>
              <p className="text-xs text-slate-600 mt-3">
                PDF, DOCX, XLSX, CSV, TXT, MD · Max {maxSizeMB}MB per file
              </p>
            </div>
          )}
        </div>
      </div>

      {rejectedFiles.length > 0 && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-red-900/20 border border-red-800/50 text-sm text-red-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Some files were rejected:</p>
            <ul className="mt-1 space-y-0.5">
              {rejectedFiles.map((name) => (
                <li key={name} className="text-xs text-red-500">
                  {name}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
