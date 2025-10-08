"""
Color contrast auditor for accessibility (WCAG 2.1).
"""

import re
from typing import List, Dict, Tuple
import structlog

logger = structlog.get_logger(__name__)


class ColorAuditor:
    """
    Color contrast auditor for WCAG compliance.

    Checks color pairs for sufficient contrast ratio according to WCAG 2.1:
    - AA Normal: 4.5:1
    - AA Large: 3:1
    - AAA Normal: 7:1
    - AAA Large: 4.5:1
    """

    # WCAG thresholds
    WCAG_AA_NORMAL = 4.5
    WCAG_AA_LARGE = 3.0
    WCAG_AAA_NORMAL = 7.0
    WCAG_AAA_LARGE = 4.5

    def __init__(self):
        self.color_pattern = re.compile(r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})")

    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB"""
        hex_color = hex_color.lstrip("#")

        # Expand shorthand (e.g., #fff -> #ffffff)
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])

        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        return (r, g, b)

    def relative_luminance(self, rgb: Tuple[int, int, int]) -> float:
        """
        Calculate relative luminance according to WCAG.

        Formula: L = 0.2126 * R + 0.7152 * G + 0.0722 * B
        where R, G, B are linearized RGB values
        """
        r, g, b = rgb

        # Convert to 0-1 range
        r_norm = r / 255.0
        g_norm = g / 255.0
        b_norm = b / 255.0

        # Linearize
        def linearize(val):
            if val <= 0.03928:
                return val / 12.92
            else:
                return ((val + 0.055) / 1.055) ** 2.4

        r_linear = linearize(r_norm)
        g_linear = linearize(g_norm)
        b_linear = linearize(b_norm)

        # Calculate luminance
        luminance = 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear

        return luminance

    def contrast_ratio(self, color1: str, color2: str) -> float:
        """
        Calculate contrast ratio between two colors.

        Args:
            color1: Hex color (e.g., "#FFFFFF")
            color2: Hex color (e.g., "#000000")

        Returns:
            Contrast ratio (1:1 to 21:1)
        """
        rgb1 = self.hex_to_rgb(color1)
        rgb2 = self.hex_to_rgb(color2)

        lum1 = self.relative_luminance(rgb1)
        lum2 = self.relative_luminance(rgb2)

        # Lighter color should be L1
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)

        ratio = (lighter + 0.05) / (darker + 0.05)

        return round(ratio, 2)

    def check_wcag_compliance(
        self,
        fg: str,
        bg: str,
        level: str = "AA",
        large_text: bool = False,
    ) -> Dict[str, any]:
        """
        Check if color pair meets WCAG compliance.

        Args:
            fg: Foreground hex color
            bg: Background hex color
            level: WCAG level ("AA" or "AAA")
            large_text: Whether text is large (18pt+ or 14pt+ bold)

        Returns:
            Dictionary with ratio and pass/fail status
        """
        ratio = self.contrast_ratio(fg, bg)

        if level == "AAA":
            threshold = self.WCAG_AAA_LARGE if large_text else self.WCAG_AAA_NORMAL
        else:  # AA
            threshold = self.WCAG_AA_LARGE if large_text else self.WCAG_AA_NORMAL

        passes = ratio >= threshold

        return {
            "fg": fg.upper(),
            "bg": bg.upper(),
            "ratio": ratio,
            "threshold": threshold,
            "wcag": "pass" if passes else "fail",
            "level": level,
            "large_text": large_text,
        }

    def extract_colors_from_text(self, text: str) -> List[str]:
        """Extract hex colors from text (e.g., from HTML/CSS)"""
        matches = self.color_pattern.findall(text)
        colors = [f"#{m}" for m in matches]
        return list(set(colors))  # Remove duplicates

    def audit_color_pairs(
        self,
        color_pairs: List[Tuple[str, str]],
        level: str = "AA",
    ) -> Dict[str, any]:
        """
        Audit multiple color pairs.

        Args:
            color_pairs: List of (fg, bg) tuples
            level: WCAG level

        Returns:
            Audit report with results and stats
        """
        results = []
        pass_count = 0
        fail_count = 0

        for fg, bg in color_pairs:
            try:
                check = self.check_wcag_compliance(fg, bg, level=level)
                results.append(check)

                if check["wcag"] == "pass":
                    pass_count += 1
                else:
                    fail_count += 1

            except Exception as e:
                logger.error("Color check failed", fg=fg, bg=bg, error=str(e))

        logger.info(
            "Color audit completed",
            total=len(results),
            passed=pass_count,
            failed=fail_count,
            level=level,
        )

        return {
            "pairs": results,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total": len(results),
            "level": level,
        }

    def audit_document_colors(
        self,
        text_content: str,
        default_fg: str = "#000000",
        default_bg: str = "#FFFFFF",
    ) -> Dict[str, any]:
        """
        Audit colors found in document text.

        Args:
            text_content: Document text (may contain CSS/HTML)
            default_fg: Default foreground color
            default_bg: Default background color

        Returns:
            Audit report
        """
        colors = self.extract_colors_from_text(text_content)

        if not colors:
            # No colors found, check defaults
            colors = [default_fg, default_bg]

        # Generate pairs (assume first half are foreground, second half are background)
        mid = len(colors) // 2 or 1
        fg_colors = colors[:mid] or [default_fg]
        bg_colors = colors[mid:] or [default_bg]

        # Create all combinations
        pairs = [(fg, bg) for fg in fg_colors for bg in bg_colors if fg != bg]

        # If no pairs, use defaults
        if not pairs:
            pairs = [(default_fg, default_bg)]

        return self.audit_color_pairs(pairs)


# Singleton instance
color_auditor = ColorAuditor()
