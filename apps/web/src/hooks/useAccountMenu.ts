import * as React from "react";

/**
 * Hook for managing account menu state (show/hide dropdown)
 */
export function useAccountMenu() {
  const [showAccountMenu, setShowAccountMenu] = React.useState(false);
  const accountMenuRef = React.useRef<HTMLDivElement>(null);

  const toggleMenu = React.useCallback(() => {
    setShowAccountMenu((prev) => !prev);
  }, []);

  // Close menu when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        accountMenuRef.current &&
        !accountMenuRef.current.contains(event.target as Node)
      ) {
        setShowAccountMenu(false);
      }
    };

    if (showAccountMenu) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showAccountMenu]);

  return {
    showAccountMenu,
    accountMenuRef,
    toggleMenu,
    setShowAccountMenu,
  };
}
