"use client";

import * as React from "react";
import { Dialog, Transition } from "@headlessui/react";
import {
  ArrowTrendingUpIcon,
  CalendarDaysIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  CurrencyDollarIcon,
  EnvelopeIcon,
  GlobeAltIcon,
  InformationCircleIcon,
  MagnifyingGlassIcon,
  QuestionMarkCircleIcon,
  XCircleIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { dispatchHelpOnboardingPrompt } from "@/lib/help-onboarding-events";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import {
  HELP_GUIDE_DONTS,
  HELP_GUIDE_DOS,
  HELP_PRESET_SECTIONS,
  VISIBLE_SECTIONS_DEFAULT,
  formatPeriodLong,
  type HelpPreset,
  type HelpPresetIcon,
} from "./help-onboarding-content";
import { PeriodSelector, ReportGenerator } from "./ReportGenerator";

const SUPPORT_EMAIL = "support@saptiva.com";

function normalizeSearchValue(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
}

function PromptIcon({ icon }: { icon: HelpPresetIcon }) {
  const className = "h-3.5 w-3.5";
  if (icon === "bar-h")
    return <ChartBarIcon className={`${className} rotate-90 scale-x-[-1]`} />;
  if (icon === "trend") return <ArrowTrendingUpIcon className={className} />;
  if (icon === "currency") return <CurrencyDollarIcon className={className} />;
  if (icon === "globe") return <GlobeAltIcon className={className} />;
  return <ChartBarIcon className={className} />;
}

export function HelpOnboardingMenu() {
  const [isOpen, setIsOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [isGuideOpen, setIsGuideOpen] = React.useState(false);
  const [isExpanded, setIsExpanded] = React.useState(false);
  const searchInputRef = React.useRef<HTMLInputElement>(null);
  const menuId = React.useId();

  // ── Shared period state (lifted from ReportGenerator) ────────────
  const [targetPeriod, setTargetPeriod] = React.useState("");
  const [latestPeriod, setLatestPeriod] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    apiClient
      .getBenchmarkPresets()
      .then((data) => {
        if (!cancelled && data.latest_period) {
          setLatestPeriod(data.latest_period);
        }
      })
      .catch(() => {
        // API unavailable — use conservative fallback
        if (!cancelled) setLatestPeriod("2025-12");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const effectivePeriod = targetPeriod || latestPeriod || "";

  const periodLabel = React.useMemo(() => {
    if (!effectivePeriod) return null;
    const fl = formatPeriodLong(effectivePeriod);
    // Capitalize first letter for display
    return fl.charAt(0).toUpperCase() + fl.slice(1);
  }, [effectivePeriod]);

  // ── Focus search on open ─────────────────────────────────────────
  React.useEffect(() => {
    if (!isOpen) return;
    const timer = window.setTimeout(() => {
      searchInputRef.current?.focus();
    }, 80);
    return () => {
      window.clearTimeout(timer);
    };
  }, [isOpen]);

  const closeMenu = React.useCallback(() => {
    setIsOpen(false);
    setQuery("");
    setIsGuideOpen(false);
    setIsExpanded(false);
  }, []);

  const handleTriggerClick = React.useCallback(() => {
    setIsOpen((current) => {
      const next = !current;
      if (!next) {
        setQuery("");
        setIsGuideOpen(false);
        setIsExpanded(false);
      }
      return next;
    });
  }, []);

  const normalizedQuery = React.useMemo(
    () => normalizeSearchValue(query),
    [query],
  );

  const filteredSections = React.useMemo(() => {
    if (!normalizedQuery) return HELP_PRESET_SECTIONS;

    return HELP_PRESET_SECTIONS.map((section) => {
      const sectionMatches = normalizeSearchValue(section.title).includes(
        normalizedQuery,
      );
      const presets = section.presets.filter((preset) => {
        if (sectionMatches) return true;
        const searchable = `${preset.label} ${preset.getPrompt(effectivePeriod)}`;
        return normalizeSearchValue(searchable).includes(normalizedQuery);
      });
      return { ...section, presets };
    }).filter((section) => section.presets.length > 0);
  }, [normalizedQuery, effectivePeriod]);

  // ── Collapsible grid logic ───────────────────────────────────────
  const visibleSections = React.useMemo(() => {
    // When searching, show all matching results
    if (normalizedQuery) return filteredSections;
    // When expanded, show all
    if (isExpanded) return filteredSections;
    // Default: show first N sections
    return filteredSections.slice(0, VISIBLE_SECTIONS_DEFAULT);
  }, [filteredSections, isExpanded, normalizedQuery]);

  const hiddenCount = normalizedQuery
    ? 0
    : filteredSections.length - VISIBLE_SECTIONS_DEFAULT;

  const handleUsePrompt = React.useCallback(
    (preset: HelpPreset) => {
      dispatchHelpOnboardingPrompt(preset.getPrompt(effectivePeriod));
      closeMenu();
    },
    [closeMenu, effectivePeriod],
  );

  return (
    <div className="relative">
      <button
        type="button"
        data-testid="help-onboarding-trigger"
        onClick={handleTriggerClick}
        className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface text-sm font-semibold text-muted transition-all hover:border-primary/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
        aria-label="Abrir ayuda y onboarding"
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        aria-controls={menuId}
        title="Ayuda y onboarding"
      >
        <QuestionMarkCircleIcon className="h-5 w-5" />
      </button>

      <Transition.Root show={isOpen} as={React.Fragment}>
        <Dialog as="div" className="relative z-[70]" onClose={closeMenu}>
          <Transition.Child
            as={React.Fragment}
            enter="ease-out duration-200"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div
              className="fixed inset-0 bg-black/50 backdrop-blur-sm"
              data-testid="help-onboarding-overlay"
            />
          </Transition.Child>

          <div className="fixed inset-0 overflow-y-auto p-3 sm:p-5">
            <div className="flex min-h-full items-center justify-center">
              <Transition.Child
                as={React.Fragment}
                enter="ease-out duration-200"
                enterFrom="opacity-0 translate-y-3 sm:translate-y-0 sm:scale-95"
                enterTo="opacity-100 translate-y-0 sm:scale-100"
                leave="ease-in duration-150"
                leaveFrom="opacity-100 translate-y-0 sm:scale-100"
                leaveTo="opacity-0 translate-y-3 sm:translate-y-0 sm:scale-95"
              >
                <Dialog.Panel
                  id={menuId}
                  data-testid="help-onboarding-menu"
                  className="w-full max-w-4xl overflow-hidden rounded-2xl border border-border bg-surface shadow-card"
                >
                  {/* ── Header with PeriodSelector ─────────────── */}
                  <div className="flex items-start justify-between gap-3 border-b border-border/70 px-4 py-4 sm:px-5">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
                      <div>
                        <Dialog.Title className="text-base font-semibold text-foreground sm:text-lg">
                          Vistas predefinidas
                        </Dialog.Title>
                        <p className="mt-1 text-xs text-muted sm:text-sm">
                          Selecciona un prompt para insertarlo en el chat.
                        </p>
                      </div>
                      <PeriodSelector
                        value={targetPeriod}
                        onChange={setTargetPeriod}
                        latestPeriod={latestPeriod}
                      />
                    </div>
                    <button
                      type="button"
                      onClick={closeMenu}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
                      aria-label="Cerrar ayuda"
                    >
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="max-h-[min(82vh,48rem)] overflow-y-auto px-4 py-4 sm:px-5">
                    <div className="mb-4 flex items-center gap-2 rounded-xl border border-border bg-background/60 px-3 py-2.5">
                      <MagnifyingGlassIcon className="h-4 w-4 text-muted" />
                      <input
                        ref={searchInputRef}
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder="Buscar vista..."
                        className="w-full border-0 bg-transparent text-sm text-foreground placeholder:text-muted focus:outline-none"
                        data-testid="help-onboarding-search"
                      />
                    </div>

                    {!normalizedQuery ? (
                      <section className="mb-5 rounded-xl border border-primary/20 bg-primary/5">
                        <button
                          type="button"
                          onClick={() => setIsGuideOpen((current) => !current)}
                          className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
                          data-testid="help-onboarding-guide-toggle"
                        >
                          <span className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                            <InformationCircleIcon className="h-4 w-4 text-primary" />
                            Guía rápida: ¿Qué puedo hacer aquí?
                          </span>
                          <ChevronDownIcon
                            className={cn(
                              "h-4 w-4 text-muted transition-transform",
                              isGuideOpen ? "rotate-180" : "rotate-0",
                            )}
                          />
                        </button>

                        <Transition
                          as={React.Fragment}
                          show={isGuideOpen}
                          enter="transition duration-200 ease-out"
                          enterFrom="opacity-0 -translate-y-1"
                          enterTo="opacity-100 translate-y-0"
                          leave="transition duration-150 ease-in"
                          leaveFrom="opacity-100 translate-y-0"
                          leaveTo="opacity-0 -translate-y-1"
                        >
                          <div className="border-t border-primary/15 px-4 pb-4 pt-3">
                            <div className="grid gap-3 md:grid-cols-2">
                              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3">
                                <h4 className="mb-2 inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-500">
                                  <CheckCircleIcon className="h-4 w-4" />
                                  Lo que puedes hacer
                                </h4>
                                <ul className="space-y-1 text-xs leading-relaxed text-muted">
                                  {HELP_GUIDE_DOS.map((item) => (
                                    <li key={item}>{item}</li>
                                  ))}
                                </ul>
                              </div>

                              <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-3">
                                <h4 className="mb-2 inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-rose-500">
                                  <XCircleIcon className="h-4 w-4" />
                                  Lo que no puede hacer el asistente
                                </h4>
                                <ul className="space-y-1 text-xs leading-relaxed text-muted">
                                  {HELP_GUIDE_DONTS.map((item) => (
                                    <li key={item}>{item}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                            <p className="mt-3 rounded-lg border border-primary/15 bg-primary/10 px-3 py-2 text-xs text-muted">
                              Tip: Haz clic en una vista y el prompt se copia al
                              chat automáticamente.
                            </p>
                          </div>
                        </Transition>
                      </section>
                    ) : null}

                    {/* ── Period label ──────────────────────────── */}
                    {periodLabel && !normalizedQuery && (
                      <p
                        className="mb-3 flex items-center gap-1.5 text-[11px] text-muted"
                        data-testid="help-onboarding-period-label"
                      >
                        <CalendarDaysIcon className="h-3.5 w-3.5" />
                        Mostrando sugerencias para:{" "}
                        <span className="font-semibold text-foreground">
                          {periodLabel}
                        </span>
                      </p>
                    )}

                    {/* ── Preset sections grid ─────────────────── */}
                    <div className="space-y-4">
                      {visibleSections.map((section) => (
                        <section key={section.id}>
                          <h3 className="mx-auto mb-2 max-w-xl text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
                            {section.title}
                          </h3>
                          <div className="mx-auto grid max-w-xl gap-2 sm:grid-cols-2">
                            {section.presets.map((preset) => (
                              <button
                                key={preset.id}
                                type="button"
                                onClick={() => handleUsePrompt(preset)}
                                data-testid={`help-onboarding-prompt-${preset.id}`}
                                className="group flex h-full items-center gap-2 rounded-xl border border-border bg-background/70 px-3 py-2.5 text-left transition-all hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
                              >
                                <span className="inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md border border-primary/20 bg-primary/10 text-primary">
                                  <PromptIcon icon={preset.icon} />
                                </span>
                                <span className="text-xs font-medium leading-tight text-foreground">
                                  {preset.label}
                                </span>
                              </button>
                            ))}
                          </div>
                        </section>
                      ))}

                      {/* ── "Ver más" accordion toggle ─────────── */}
                      {!normalizedQuery && hiddenCount > 0 && (
                        <button
                          type="button"
                          onClick={() => setIsExpanded((v) => !v)}
                          data-testid="help-onboarding-expand-toggle"
                          className="mx-auto flex items-center gap-1.5 rounded-lg border border-border bg-background/60 px-4 py-2 text-xs font-medium text-muted transition-all hover:border-primary/30 hover:text-foreground"
                        >
                          {isExpanded
                            ? "Mostrar menos"
                            : `Ver todas las categorías (+${hiddenCount})`}
                          <ChevronDownIcon
                            className={cn(
                              "h-3.5 w-3.5 transition-transform",
                              isExpanded ? "rotate-180" : "rotate-0",
                            )}
                          />
                        </button>
                      )}

                      {filteredSections.length === 0 ? (
                        <div
                          className="rounded-xl border border-dashed border-border bg-background/50 px-4 py-8 text-center text-sm text-muted"
                          data-testid="help-onboarding-no-results"
                        >
                          No se encontraron vistas para esta búsqueda.
                        </div>
                      ) : null}
                    </div>

                    {/* Report Generator — after preset sections */}
                    {!normalizedQuery && (
                      <ReportGenerator
                        targetPeriod={targetPeriod}
                        onPeriodChange={setTargetPeriod}
                        latestPeriod={latestPeriod}
                      />
                    )}

                    <div className="mt-5 inline-flex flex-wrap items-center gap-2 rounded-lg border border-border bg-background/60 px-3 py-2 text-xs text-muted">
                      <EnvelopeIcon className="h-4 w-4" />
                      <span>¿Necesitas ayuda?</span>
                      <a
                        href={`mailto:${SUPPORT_EMAIL}`}
                        className="font-semibold text-primary hover:underline"
                      >
                        {SUPPORT_EMAIL}
                      </a>
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition.Root>
    </div>
  );
}

export default HelpOnboardingMenu;
