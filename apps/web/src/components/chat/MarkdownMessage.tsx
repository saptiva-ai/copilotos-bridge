"use client";

/**
 * MarkdownMessage Component
 *
 * CHANGELOG:
 * - 2025-01-17: Integrado CodeBlock con react-syntax-highlighter (portado de Vercel)
 * - Reemplazado rehype-highlight con CodeBlock custom
 * - Agregado copy button a bloques de código
 */

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeSanitize from "rehype-sanitize"; // FIX ISSUE-008: Prevent XSS attacks
import { cn } from "../../lib/utils";
import type { PluggableList } from "unified";
import "katex/dist/katex.min.css";
import {
  CodeBlock,
  CodeBlockCopyButton,
  getLanguageFromClassName,
} from "./CodeBlock";

interface MarkdownMessageProps {
  content: string;
  className?: string;
  /**
   * Enable syntax highlighting when true. During streaming we can disable
   * this to avoid re-processing the markdown on every token.
   */
  highlightCode?: boolean;
}

const defaultComponents = {
  a: ({ node: _, href, children, ...props }: any) => {
    // Detect audit report download links
    const isAuditReportDownload = href?.match(
      /\/api\/reports\/audit\/([^/]+)\/download/,
    );

    if (isAuditReportDownload) {
      const reportId = isAuditReportDownload[1];

      return (
        <button
          onClick={async (e) => {
            e.preventDefault();
            try {
              // Get auth token from localStorage
              const authData = localStorage.getItem("auth-storage");
              const token = authData
                ? JSON.parse(authData)?.state?.token
                : null;

              if (!token) {
                alert("Debes iniciar sesión para descargar el reporte");
                return;
              }

              // Fetch the PDF with authentication
              const response = await fetch(href, {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              });

              if (!response.ok) {
                throw new Error("Error al descargar el reporte");
              }

              // Create a blob and download
              const blob = await response.blob();
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `reporte-auditoria-${reportId}.pdf`;
              document.body.appendChild(a);
              a.click();
              window.URL.revokeObjectURL(url);
              document.body.removeChild(a);
            } catch (error) {
              console.error("Error downloading audit report:", error);
              alert(
                "Error al descargar el reporte. Por favor intenta nuevamente.",
              );
            }
          }}
          className={cn(
            "inline-flex items-center gap-2 px-4 py-2 rounded-md",
            "bg-primary/10 hover:bg-primary/20",
            "text-primary font-medium",
            "border border-primary/30",
            "transition-colors cursor-pointer",
            props.className,
          )}
        >
          {children}
        </button>
      );
    }

    // Regular links
    return (
      <a
        {...props}
        href={href}
        className={cn(
          "text-primary underline decoration-dotted underline-offset-2 hover:text-primary/80 transition-colors",
          props.className,
        )}
        target="_blank"
        rel="noreferrer"
      />
    );
  },
  pre: ({ children, ...props }: React.HTMLAttributes<HTMLPreElement>) => {
    // Extract code props from the child code element
    // ReactMarkdown wraps block code in <pre><code>...</code></pre>
    const codeElement = React.isValidElement(children) ? children : null;

    if (
      codeElement &&
      (codeElement.type === "code" ||
        codeElement.type === defaultComponents.code)
    ) {
      const { className, children: codeChildren } =
        codeElement.props as React.HTMLAttributes<HTMLElement>;
      const language = getLanguageFromClassName(className);
      const codeString = String(codeChildren).replace(/\n$/, "");

      return (
        <CodeBlock code={codeString} language={language} className="my-4">
          <CodeBlockCopyButton />
        </CodeBlock>
      );
    }

    // Fallback for non-standard pre usage
    return <pre {...props}>{children}</pre>;
  },
  code: ({
    className,
    children,
    ...props
  }: React.HTMLAttributes<HTMLElement>) => {
    // Inline code (not wrapped in pre)
    return (
      <code
        {...props}
        className={cn(
          "rounded-md bg-muted/20 px-1.5 py-0.5 font-mono text-[0.85em] text-primary",
          className,
        )}
      >
        {children}
      </code>
    );
  },
  blockquote: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <blockquote
      {...props}
      className={cn("border-l-2 border-primary/50 pl-4 text-muted", className)}
    />
  ),
  ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul
      {...props}
      className={cn(
        "list-disc space-y-2 pl-5 marker:text-primary/80",
        className,
      )}
    />
  ),
  ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol
      {...props}
      className={cn(
        "list-decimal space-y-2 pl-5 marker:text-primary/80",
        className,
      )}
    />
  ),
  table: ({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="overflow-x-auto">
      <table
        {...props}
        className={cn(
          "w-full border-collapse border border-border text-left text-sm",
          className,
        )}
      />
    </div>
  ),
  th: ({ className, ...props }: React.HTMLAttributes<HTMLTableCellElement>) => (
    <th
      {...props}
      className={cn(
        "border border-border bg-surface-2 px-3 py-2 text-foreground font-medium",
        className,
      )}
    />
  ),
  td: ({ className, ...props }: React.HTMLAttributes<HTMLTableCellElement>) => (
    <td
      {...props}
      className={cn(
        "border border-border px-3 py-2 align-top text-foreground",
        className,
      )}
    />
  ),
};

/**
 * Preprocessor to normalize LaTeX syntax to Markdown-compatible format.
 * Converts traditional LaTeX delimiters to remark-math compatible syntax:
 * - \[ ... \] -> $$ ... $$ (display math)
 * - \( ... \) -> $ ... $ (inline math)
 * - [ ... ] -> $$ ... $$ (display math, common LLM output)
 */
function normalizeLatexSyntax(content: string): string {
  let normalized = content;

  // Convert \[ ... \] to $$ ... $$ (display math)
  // Use a function to avoid issues with $ special characters in replacement string
  normalized = normalized.replace(/\\\[([\s\S]*?)\\\]/g, (_match, equation) => {
    return `$$${equation}$$`;
  });

  // Convert \( ... \) to $ ... $ (inline math)
  normalized = normalized.replace(/\\\(([\s\S]*?)\\\)/g, (_match, equation) => {
    return `$${equation}$`;
  });

  // Convert standalone [ ... ] to $$ ... $$ (display math)
  // VERY conservative: only match if at start of line (not after any other content)
  // and equation contains LaTeX commands
  normalized = normalized.replace(
    /^\s*\[([\s\S]*?)\]\s*$/gm,
    (match, equation) => {
      // Must contain LaTeX commands to be considered an equation
      // Look for: backslash commands (\frac, \alpha, etc), subscripts, superscripts, braces
      const hasLatexCommands = /\\[a-zA-Z]{2,}|[_^{]/.test(equation);
      const hasMultipleSymbols =
        (equation.match(/\\[a-zA-Z]+/g) || []).length >= 2;

      // Only convert if it clearly looks like a LaTeX equation
      if (hasLatexCommands && hasMultipleSymbols) {
        return `$$${equation}$$\n`;
      }

      // Otherwise keep original
      return match;
    },
  );

  return normalized;
}

export function MarkdownMessage({
  content,
  className,
  highlightCode = true,
}: MarkdownMessageProps) {
  // Normalize LaTeX syntax before rendering
  const normalizedContent = React.useMemo(() => {
    return normalizeLatexSyntax(content);
  }, [content]);

  const markdownPlugins = React.useMemo(() => {
    const remarkPlugins: PluggableList = [remarkGfm, remarkMath];
    const rehypePlugins: PluggableList = [];

    // FIX ISSUE-008: Sanitize HTML first to prevent XSS
    rehypePlugins.push(rehypeSanitize);

    // NOTE: Removed rehypeHighlight - now using CodeBlock component instead
    // Syntax highlighting is handled by react-syntax-highlighter in CodeBlock

    rehypePlugins.push(rehypeKatex);
    return {
      remark: remarkPlugins,
      rehype: rehypePlugins,
    };
  }, []);

  return (
    <div
      className={cn(
        "prose dark:prose-invert max-w-none text-sm prose-p:text-foreground prose-headings:text-foreground prose-strong:text-foreground prose-li:text-foreground",
        // LAYOUT FIX: Add min-w-0 to allow prose content to shrink below content size in flex layouts
        "min-w-0",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={markdownPlugins.remark}
        rehypePlugins={markdownPlugins.rehype}
        components={defaultComponents}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
}

export default MarkdownMessage;
