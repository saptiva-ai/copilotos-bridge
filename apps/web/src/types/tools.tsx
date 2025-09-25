import type { JSX } from 'react'

interface IconProps {
  className?: string
}

const baseIcon = (paths: JSX.Element[], className?: string) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    {paths}
  </svg>
)

const DeepResearchIcon = ({ className }: IconProps) =>
  baseIcon(
    [
      <circle key="c" cx={11} cy={11} r={6} />, 
      <line key="l" x1={16.5} y1={16.5} x2={20} y2={20} />, 
    ],
    className,
  )

const AddFilesIcon = ({ className }: IconProps) =>
  baseIcon(
    [
      <path key="p1" d="M4 3h9l5 5v13H4z" />, 
      <path key="p2" d="M8 12h8" />, 
      <path key="p3" d="M12 8v8" />, 
    ],
    className,
  )

const GoogleDriveIcon = ({ className }: IconProps) =>
  baseIcon(
    [
      <path key="p1" d="M7 3h10l4 7-4 7H7l-4-7 4-7Z" />, 
      <path key="p2" d="M7 17h10" />, 
    ],
    className,
  )

const WebSearchIcon = ({ className }: IconProps) =>
  baseIcon(
    [
      <circle key="c" cx={12} cy={12} r={5} />, 
      <path key="p1" d="M2 12h20" />, 
      <path key="p2" d="M12 2a15 15 0 0 1 5 10 15 15 0 0 1-5 10 15 15 0 0 1-5-10 15 15 0 0 1 5-10Z" />, 
    ],
    className,
  )

const CanvasIcon = ({ className }: IconProps) =>
  baseIcon(
    [
      <rect key="r" x={4} y={4} width={16} height={16} rx={2} />, 
      <path key="p1" d="M9 15h6" />, 
      <path key="p2" d="M9 9h6" />, 
      <path key="p3" d="M9 12h6" />, 
    ],
    className,
  )

const AgentModeIcon = ({ className }: IconProps) =>
  baseIcon(
    [
      <path key="p1" d="M12 2a6 6 0 0 1 6 6v2a6 6 0 0 1-12 0V8a6 6 0 0 1 6-6Z" />, 
      <path key="p2" d="M5 22h14" />, 
    ],
    className,
  )

export type ToolId =
  | 'deep-research'
  | 'add-files'
  | 'google-drive'
  | 'web-search'
  | 'canvas'
  | 'agent-mode'

export type Tool = {
  id: ToolId
  label: string
  Icon: (props: IconProps) => JSX.Element
}

export const TOOL_REGISTRY: Record<ToolId, Tool> = {
  'deep-research': { id: 'deep-research', label: 'Deep research', Icon: DeepResearchIcon },
  'add-files': { id: 'add-files', label: 'Add files', Icon: AddFilesIcon },
  'google-drive': { id: 'google-drive', label: 'Google Drive', Icon: GoogleDriveIcon },
  'web-search': { id: 'web-search', label: 'Web search', Icon: WebSearchIcon },
  canvas: { id: 'canvas', label: 'Canvas', Icon: CanvasIcon },
  'agent-mode': { id: 'agent-mode', label: 'Agent mode', Icon: AgentModeIcon },
}
