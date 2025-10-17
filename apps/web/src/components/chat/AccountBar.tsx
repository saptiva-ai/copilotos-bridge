"use client";

import * as React from "react";
import { cn } from "../../lib/utils";

interface User {
  username?: string;
  email: string;
}

interface AccountBarProps {
  user: User | null;
  showAccountMenu: boolean;
  accountMenuRef: React.RefObject<HTMLDivElement>;
  onToggleMenu: () => void;
  onLogout: () => void;
  variant?: "legacy" | "grid";
  isCollapsed?: boolean;
}

/**
 * Account bar component with user info and logout functionality.
 *
 * Production design: Always shows user name and email
 *
 * Variants:
 * - legacy: Simple logout button with user info (no dropdown)
 * - grid: Dropdown menu with logout option
 */
export function AccountBar({
  user,
  showAccountMenu,
  accountMenuRef,
  onToggleMenu,
  onLogout,
  variant = "grid",
  isCollapsed = false,
}: AccountBarProps) {
  if (!user) {
    return null;
  }

  const userInitial =
    user.username?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || "U";

  // Collapsed mini-rail version - just avatar icon
  if (isCollapsed) {
    return (
      <div className="border-t border-border p-2">
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center justify-center rounded-full bg-primary/20 p-2 transition-colors hover:bg-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
          aria-label="Cerrar sesión"
          title={`${user.username || user.email} - Cerrar sesión`}
        >
          <span className="text-sm font-bold text-primary">{userInitial}</span>
        </button>
      </div>
    );
  }

  if (variant === "legacy") {
    // Legacy variant: Simple logout button with user info (Production design)
    return (
      <div className="border-t border-border p-4">
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-xl bg-surface-2 p-3 transition-colors hover:bg-surface-2/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
        >
          {/* Avatar */}
          <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
            <span className="text-sm font-bold text-primary">
              {userInitial}
            </span>
          </div>
          {/* User info */}
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm font-bold text-text truncate">
              {user.username || user.email}
            </p>
            <p className="text-xs text-text-muted truncate">{user.email}</p>
          </div>
          {/* Logout icon */}
          <svg
            className="h-4 w-4 text-text-muted flex-shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
          >
            <path
              d="M13 16l4-4-4-4"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path d="M7 12h10" strokeWidth="1.6" strokeLinecap="round" />
            <path
              d="M12 21H7a1 1 0 01-1-1V4a1 1 0 011-1h5"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>
    );
  }

  // Grid variant: Dropdown menu (Production design)
  return (
    <div className="border-t border-border p-4">
      <div className="relative" ref={accountMenuRef}>
        <button
          type="button"
          onClick={onToggleMenu}
          className="flex w-full items-center gap-3 rounded-xl bg-surface-2 p-3 transition-colors hover:bg-surface-2/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
        >
          {/* Avatar */}
          <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
            <span className="text-sm font-bold text-primary">
              {userInitial}
            </span>
          </div>

          {/* User info */}
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm font-bold text-text truncate">
              {user.username}
            </p>
            <p className="text-xs text-text-muted truncate">{user.email}</p>
          </div>

          {/* Menu arrow */}
          <svg
            className={cn(
              "h-4 w-4 text-text-muted transition-transform",
              showAccountMenu && "rotate-180",
            )}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.8"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {/* Account menu */}
        {showAccountMenu && (
          <div className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-border bg-surface shadow-card overflow-hidden">
            <button
              type="button"
              onClick={() => {
                onToggleMenu();
                onLogout();
              }}
              className="w-full px-3 py-2 text-left text-sm text-danger hover:bg-danger/10 transition-colors"
            >
              Cerrar sesión
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
