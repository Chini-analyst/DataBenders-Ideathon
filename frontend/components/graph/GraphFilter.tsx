"use client";

import { useState, useMemo } from "react";
import { GraphStats } from "@/lib/api";
import { Filter, Search, ChevronDown, ChevronRight } from "lucide-react";
import { clsx } from "clsx";

// ── Colour palette — dynamically assigned by index for unknown types ──────
const PALETTE = [
  { dot: "bg-blue-400",     text: "text-blue-400",     bg: "bg-blue-500/10 border-blue-500/20",     check: "accent-blue-400" },
  { dot: "bg-gold-400",     text: "text-gold-400",     bg: "bg-gold-500/10 border-gold-500/20",     check: "accent-yellow-400" },
  { dot: "bg-violet-400",   text: "text-violet-400",   bg: "bg-violet-500/10 border-violet-500/20", check: "accent-violet-400" },
  { dot: "bg-emerald-400",  text: "text-emerald-400",  bg: "bg-emerald-500/10 border-emerald-500/20",check: "accent-emerald-400" },
  { dot: "bg-orange-400",   text: "text-orange-400",   bg: "bg-orange-500/10 border-orange-500/20", check: "accent-orange-400" },
  { dot: "bg-green-400",    text: "text-green-400",    bg: "bg-green-500/10 border-green-500/20",   check: "accent-green-400" },
  { dot: "bg-yellow-400",   text: "text-yellow-400",   bg: "bg-yellow-500/10 border-yellow-500/20", check: "accent-yellow-400" },
  { dot: "bg-cyan-400",     text: "text-cyan-400",     bg: "bg-cyan-500/10 border-cyan-500/20",     check: "accent-cyan-400" },
  { dot: "bg-rose-400",     text: "text-rose-400",     bg: "bg-rose-500/10 border-rose-500/20",     check: "accent-rose-400" },
  { dot: "bg-red-400",      text: "text-red-400",      bg: "bg-red-500/10 border-red-500/20",       check: "accent-red-400" },
  { dot: "bg-teal-400",     text: "text-teal-400",     bg: "bg-teal-500/10 border-teal-500/20",     check: "accent-teal-400" },
  { dot: "bg-lime-400",     text: "text-lime-400",     bg: "bg-lime-500/10 border-lime-500/20",     check: "accent-lime-400" },
  { dot: "bg-pink-400",     text: "text-pink-400",     bg: "bg-pink-500/10 border-pink-500/20",     check: "accent-pink-400" },
  { dot: "bg-amber-400",    text: "text-amber-400",    bg: "bg-amber-500/10 border-amber-500/20",   check: "accent-amber-400" },
  { dot: "bg-indigo-400",   text: "text-indigo-400",   bg: "bg-indigo-500/10 border-indigo-500/20", check: "accent-indigo-400" },
  { dot: "bg-sky-400",      text: "text-sky-400",      bg: "bg-sky-500/10 border-sky-500/20",       check: "accent-sky-400" },
  { dot: "bg-purple-400",   text: "text-purple-400",   bg: "bg-purple-500/10 border-purple-500/20", check: "accent-purple-400" },
  { dot: "bg-fuchsia-400",  text: "text-fuchsia-400",  bg: "bg-fuchsia-500/10 border-fuchsia-500/20",check: "accent-fuchsia-400" },
  { dot: "bg-slate-400",    text: "text-slate-400",    bg: "bg-slate-500/10 border-slate-500/20",   check: "accent-slate-400" },
];

// Map well-known type names to a stable palette index
const TYPE_PALETTE_INDEX: Record<string, number> = {
  Person: 0, Department: 1, JobTitle: 2, Skill: 3, Project: 4,
  Location: 5, SalaryBand: 6, EmploymentType: 7, PerformanceRating: 8,
  Status: 18, Priority: 9, ProficiencyLevel: 10, Certification: 11,
  Client: 12, Budget: 13, Date: 14, Headcount: 15, Category: 16,
  EmployeeID: 17, Entity: 18,
  Organization: 1, Concept: 16, Document: 4,
};

function getStyle(type: string, index: number) {
  const idx = TYPE_PALETTE_INDEX[type] ?? index % PALETTE.length;
  return PALETTE[idx];
}

// ── Indeterminate checkbox ──────────────────────────────────────────────
interface MasterCheckboxProps {
  checked: boolean;
  indeterminate: boolean;
  onChange: () => void;
  label: string;
}

function MasterCheckbox({ checked, indeterminate, onChange, label }: MasterCheckboxProps) {
  return (
    <label className="flex items-center gap-2 cursor-pointer group select-none">
      <span className="relative flex items-center justify-center w-3.5 h-3.5">
        <input
          type="checkbox"
          checked={checked}
          ref={(el) => { if (el) el.indeterminate = indeterminate; }}
          onChange={onChange}
          className="w-3.5 h-3.5 rounded border border-slate-600 bg-navy-800 cursor-pointer accent-gold-400"
        />
      </span>
      <span className="text-xs font-medium text-slate-400 group-hover:text-slate-200 transition-colors">
        {label}
      </span>
    </label>
  );
}

interface GraphFilterProps {
  stats: GraphStats | null;
  activeTypes: Set<string>;
  onToggleType: (type: string) => void;
  onSelectAllTypes: () => void;
  onDeselectAllTypes: () => void;
  activeRelTypes: Set<string>;
  onToggleRelType: (rel: string) => void;
  onSelectAllRelTypes: () => void;
  onDeselectAllRelTypes: () => void;
}

export function GraphFilter({
  stats,
  activeTypes,
  onToggleType,
  onSelectAllTypes,
  onDeselectAllTypes,
  activeRelTypes,
  onToggleRelType,
  onSelectAllRelTypes,
  onDeselectAllRelTypes,
}: GraphFilterProps) {
  const [typeSearch, setTypeSearch] = useState("");
  const [relSearch, setRelSearch] = useState("");
  const [relOpen, setRelOpen] = useState(true);

  // Derive sorted lists — empty when stats not yet loaded
  const allNodeTypes = useMemo(
    () => stats ? Object.entries(stats.node_types).sort((a, b) => b[1] - a[1]) : [],
    [stats]
  );
  const allRelTypes = useMemo(
    () => stats ? Object.entries(stats.relationship_types).sort((a, b) => b[1] - a[1]) : [],
    [stats]
  );

  // Filtered lists based on search — hooks must be called before any early return
  const visibleNodeTypes = useMemo(
    () => allNodeTypes.filter(([t]) => t.toLowerCase().includes(typeSearch.toLowerCase())),
    [allNodeTypes, typeSearch]
  );
  const visibleRelTypes = useMemo(
    () => allRelTypes.filter(([r]) => r.toLowerCase().includes(relSearch.toLowerCase())),
    [allRelTypes, relSearch]
  );

  if (!stats) return null;

  // Master checkbox state for entity types
  const allTypesCount   = allNodeTypes.length;
  const activeTypeCount = allNodeTypes.filter(([t]) => activeTypes.has(t)).length;
  const allChecked      = activeTypeCount === allTypesCount;
  const noneChecked     = activeTypeCount === 0;
  const typeIndeterminate = !allChecked && !noneChecked;

  // Master checkbox state for relationship types
  const allRelCount    = allRelTypes.length;
  const activeRelCount = allRelTypes.filter(([r]) => activeRelTypes.has(r)).length;
  const allRelChecked  = activeRelCount === allRelCount;
  const noneRelChecked = activeRelCount === 0;
  const relIndeterminate = !allRelChecked && !noneRelChecked;

  const handleTypeMaster = () => {
    if (allChecked || typeIndeterminate) onDeselectAllTypes();
    else onSelectAllTypes();
  };

  const handleRelMaster = () => {
    if (allRelChecked || relIndeterminate) onDeselectAllRelTypes();
    else onSelectAllRelTypes();
  };

  return (
    <div className="w-56 flex-shrink-0 bg-navy-900 border border-navy-700 rounded-xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-navy-700">
        <Filter className="w-3.5 h-3.5 text-gold-400 flex-shrink-0" />
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Filters
        </h3>
        {/* Active count badge */}
        {(noneChecked || noneRelChecked) && (
          <span className="ml-auto text-xs px-1.5 py-0.5 rounded-full bg-gold-500/20 text-gold-400 border border-gold-500/30 font-medium">
            filtered
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* ── Entity Types section ─────────────────────────────────── */}
        <div className="p-3 border-b border-navy-800">
          {/* Section header: label + master checkbox + counter */}
          <div className="flex items-center justify-between mb-2.5">
            <MasterCheckbox
              checked={allChecked}
              indeterminate={typeIndeterminate}
              onChange={handleTypeMaster}
              label="Entity Types"
            />
            <span className="text-xs text-slate-600">
              {activeTypeCount}/{allTypesCount}
            </span>
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-600" />
            <input
              type="text"
              placeholder="Search types..."
              value={typeSearch}
              onChange={(e) => setTypeSearch(e.target.value)}
              className="w-full pl-6 pr-2 py-1 text-xs bg-navy-800 border border-navy-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:border-gold-500/50"
            />
          </div>

          {/* Type list */}
          <div className="space-y-0.5 max-h-64 overflow-y-auto pr-0.5">
            {visibleNodeTypes.length === 0 && (
              <p className="text-xs text-slate-700 py-2 text-center">No match</p>
            )}
            {visibleNodeTypes.map(([type, count], idx) => {
              const style  = getStyle(type, idx);
              const active = activeTypes.has(type);
              return (
                <label
                  key={type}
                  className={clsx(
                    "flex items-center gap-2.5 px-2 py-1.5 rounded-lg cursor-pointer transition-all select-none",
                    active
                      ? `${style.bg} ${style.text}`
                      : "text-slate-600 hover:text-slate-400 hover:bg-navy-800/60"
                  )}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() => onToggleType(type)}
                    className="w-3.5 h-3.5 rounded border border-slate-600 bg-navy-800 cursor-pointer flex-shrink-0 accent-current"
                  />
                  {/* Colour dot */}
                  <span className={clsx("w-2 h-2 rounded-full flex-shrink-0", active ? style.dot : "bg-slate-700")} />
                  <span className="flex-1 text-xs truncate">{type}</span>
                  <span className={clsx("text-xs font-medium flex-shrink-0", active ? "" : "text-slate-700")}>
                    {count}
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        {/* ── Relationship Types section ────────────────────────────── */}
        {allRelTypes.length > 0 && (
          <div className="p-3">
            {/* Collapsible section header */}
            <div className="flex items-center justify-between mb-2.5">
              <div className="flex items-center gap-2">
                <MasterCheckbox
                  checked={allRelChecked}
                  indeterminate={relIndeterminate}
                  onChange={handleRelMaster}
                  label="Relationships"
                />
                <button
                  onClick={() => setRelOpen((o) => !o)}
                  className="text-slate-600 hover:text-slate-400 transition-colors"
                >
                  {relOpen
                    ? <ChevronDown className="w-3 h-3" />
                    : <ChevronRight className="w-3 h-3" />}
                </button>
              </div>
              <span className="text-xs text-slate-600">
                {activeRelCount}/{allRelCount}
              </span>
            </div>

            {relOpen && (
              <>
                {/* Search */}
                <div className="relative mb-2">
                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-600" />
                  <input
                    type="text"
                    placeholder="Search relationships..."
                    value={relSearch}
                    onChange={(e) => setRelSearch(e.target.value)}
                    className="w-full pl-6 pr-2 py-1 text-xs bg-navy-800 border border-navy-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:border-gold-500/50"
                  />
                </div>

                {/* Relationship list */}
                <div className="space-y-0.5 max-h-52 overflow-y-auto pr-0.5">
                  {visibleRelTypes.length === 0 && (
                    <p className="text-xs text-slate-700 py-2 text-center">No match</p>
                  )}
                  {visibleRelTypes.map(([rel, count]) => {
                    const active = activeRelTypes.has(rel);
                    return (
                      <label
                        key={rel}
                        className={clsx(
                          "flex items-center gap-2.5 px-2 py-1.5 rounded-lg cursor-pointer transition-all select-none",
                          active
                            ? "text-gold-400/90 bg-gold-500/5 border border-gold-500/10"
                            : "text-slate-600 hover:text-slate-400 hover:bg-navy-800/60"
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={active}
                          onChange={() => onToggleRelType(rel)}
                          className="w-3.5 h-3.5 rounded border border-slate-600 bg-navy-800 cursor-pointer flex-shrink-0 accent-yellow-400"
                        />
                        <span className="flex-1 text-xs truncate font-mono">{rel}</span>
                        <span className={clsx("text-xs font-medium flex-shrink-0", active ? "" : "text-slate-700")}>
                          {count}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
