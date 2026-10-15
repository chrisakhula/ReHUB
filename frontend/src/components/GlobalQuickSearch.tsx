import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Spinner } from "react-bootstrap";
import { api } from "../api/client";

interface SearchItem {
  id: string;
  code: string;
  title: string;
  subtitle: string;
  type: string;
  url: string;
}

interface SearchResponse {
  results: Record<string, SearchItem[]>;
  total_matches: number;
}

const CATEGORY_META: Record<
  string,
  { label: string; icon: string; badgeColor: string }
> = {
  clients: { label: "Clients", icon: "bi-person-badge-fill", badgeColor: "#0284c7" },
  admissions: { label: "Admissions", icon: "bi-door-open-fill", badgeColor: "#10b981" },
  medications: { label: "Medications", icon: "bi-capsule-pill", badgeColor: "#8b5cf6" },
  invoices: { label: "Invoices", icon: "bi-receipt", badgeColor: "#f59e0b" },
  staff: { label: "Staff", icon: "bi-person-workspace", badgeColor: "#06b6d4" },
  incidents: { label: "Incidents", icon: "bi-shield-exclamation", badgeColor: "#ef4444" },
  inventory: { label: "Inventory", icon: "bi-box-seam", badgeColor: "#ec4899" },
};

export function GlobalQuickSearch() {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Flattened results for keyboard navigation
  const flatResults = React.useMemo(() => {
    if (!data?.results) return [];
    const items: SearchItem[] = [];
    for (const group of Object.values(data.results)) {
      items.push(...group);
    }
    return items;
  }, [data]);

  // Global Ctrl+K / Cmd+K shortcut
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
      if (e.key === "Escape") {
        setIsOpen(false);
        inputRef.current?.blur();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced search query
  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setData(null);
      setLoading(false);
      setActiveIndex(-1);
      return;
    }

    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const res = await api<SearchResponse>(
          `/search/quick?q=${encodeURIComponent(trimmed)}&limit=6`
        );
        setData(res);
        setActiveIndex(-1);
      } catch (err) {
        console.error("Global search error:", err);
      } finally {
        setLoading(false);
      }
    }, 220);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (item: SearchItem) => {
    setIsOpen(false);
    setQuery("");
    navigate(item.url);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || flatResults.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % flatResults.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev <= 0 ? flatResults.length - 1 : prev - 1));
    } else if (e.key === "Enter" && activeIndex >= 0 && flatResults[activeIndex]) {
      e.preventDefault();
      handleSelect(flatResults[activeIndex]);
    }
  };

  return (
    <div className="global-quick-search" ref={containerRef}>
      <div className="search-input-wrapper">
        <i className="bi bi-search search-icon" aria-hidden="true" />
        <input
          ref={inputRef}
          type="search"
          className="search-input"
          placeholder="Quick search records... (Ctrl+K)"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          aria-label="Global quick search across ReHUB records"
          autoComplete="off"
          spellCheck="false"
        />
        {query ? (
          <button
            type="button"
            className="search-clear-btn"
            onClick={() => {
              setQuery("");
              setData(null);
              inputRef.current?.focus();
            }}
            aria-label="Clear search"
          >
            <i className="bi bi-x-circle-fill" />
          </button>
        ) : (
          <kbd className="search-kbd-hint d-none d-md-inline-block">Ctrl K</kbd>
        )}
      </div>

      {isOpen && (query.trim().length > 0 || loading) && (
        <div className="search-dropdown-menu">
          {loading && !data && (
            <div className="search-status-box">
              <Spinner animation="border" size="sm" className="me-2" />
              <span>Searching clinical & operational records...</span>
            </div>
          )}

          {data && data.total_matches === 0 && !loading && (
            <div className="search-empty-box">
              <i className="bi bi-search mb-2" style={{ fontSize: "1.5rem", opacity: 0.5 }} />
              <div>No records found matching &ldquo;<strong>{query}</strong>&rdquo;</div>
              <small className="text-muted mt-1">
                Try searching by client number (ARS-...), Rx, staff, incident, or medicine name
              </small>
            </div>
          )}

          {data && data.total_matches > 0 && (
            <div className="search-results-container">
              <div className="search-results-summary">
                <span>Found {data.total_matches} match{data.total_matches > 1 ? "es" : ""}</span>
                <span className="search-esc-hint">Press ESC to dismiss</span>
              </div>

              {Object.entries(data.results).map(([catKey, items]) => {
                const meta = CATEGORY_META[catKey] ?? {
                  label: catKey.toUpperCase(),
                  icon: "bi-folder",
                  badgeColor: "#64748b",
                };

                return (
                  <div key={catKey} className="search-category-group">
                    <div className="search-category-header">
                      <i className={`bi ${meta.icon} me-1`} />
                      <span>{meta.label}</span>
                      <span className="search-category-count">({items.length})</span>
                    </div>

                    <div className="search-items-list">
                      {items.map((item) => {
                        const globalIndex = flatResults.findIndex(
                          (r) => r.id === item.id && r.type === item.type
                        );
                        const isSelected = globalIndex === activeIndex;

                        return (
                          <div
                            key={`${item.type}-${item.id}`}
                            className={`search-result-item ${isSelected ? "selected" : ""}`}
                            onClick={() => handleSelect(item)}
                            onMouseEnter={() => setActiveIndex(globalIndex)}
                            role="button"
                            tabIndex={0}
                          >
                            <div className="search-item-badge-wrap">
                              <span
                                className="search-item-badge"
                                style={{ backgroundColor: meta.badgeColor }}
                              >
                                {item.code}
                              </span>
                            </div>
                            <div className="search-item-info">
                              <div className="search-item-title">{item.title}</div>
                              <div className="search-item-subtitle">{item.subtitle}</div>
                            </div>
                            <i className="bi bi-arrow-right-short search-item-arrow" />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
