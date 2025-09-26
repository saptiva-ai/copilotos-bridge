import { TOOL_REGISTRY, ToolId } from "@/types/tools";
import { visibleTools } from "@/lib/feature-flags";

type ToolMenuProps = {
  onSelect: (id: ToolId) => void;
  onClose: () => void;
};

export default function ToolMenu({ onSelect, onClose }: ToolMenuProps) {
  return (
    <div className="w-72 max-h-[60vh] overflow-y-auto rounded-xl border border-zinc-700/60 bg-zinc-900/95 shadow-xl backdrop-blur-sm p-3 pointer-events-auto">
      <div className="px-1 py-1 mb-2">
        <h3 className="text-sm font-semibold text-zinc-300">Tools</h3>
      </div>
      <div className="space-y-1">
        {Object.values(TOOL_REGISTRY).filter((tool) => visibleTools[tool.id]).map((tool) => (
          <button
            key={tool.id}
            type="button"
            className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-zinc-800/70 text-zinc-200 transition-colors border border-transparent hover:border-zinc-700/40 cursor-pointer pointer-events-auto"
            onMouseDown={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onSelect(tool.id);
            }}
            aria-label={`Add ${tool.label}`}
          >
            <span className="grid h-9 w-9 place-items-center rounded-lg border border-zinc-700/60 bg-zinc-800/60 text-zinc-300">
              <tool.Icon className="h-4 w-4" />
            </span>
            <div className="flex-1 text-left">
              <p className="font-medium text-sm">{tool.label}</p>
              <p className="text-xs text-zinc-400 mt-0.5">Click to add</p>
            </div>
            <svg className="h-4 w-4 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        ))}
      </div>
    </div>
  );
}
