import { forwardRef, type SVGAttributes } from "react";
import { cn } from "@/lib/utils";

const iconPaths: Record<string, React.ReactNode> = {
  "chevron-right": (
    <polyline points="9 18 15 12 9 6" />
  ),
  "chevron-down": (
    <polyline points="6 9 12 15 18 9" />
  ),
  check: (
    <polyline points="20 6 9 17 4 12" />
  ),
  x: (
    <>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </>
  ),
  plus: (
    <>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </>
  ),
  file: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </>
  ),
  folder: (
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  ),
  "git-branch": (
    <>
      <line x1="6" y1="3" x2="6" y2="15" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <path d="M18 9a9 9 0 0 1-9 9" />
    </>
  ),
  "git-commit": (
    <>
      <circle cx="12" cy="12" r="4" />
      <line x1="1.05" y1="12" x2="7" y2="12" />
      <line x1="17.01" y1="12" x2="22.96" y2="12" />
    </>
  ),
  circle: (
    <circle cx="12" cy="12" r="10" />
  ),
  "message-square": (
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  ),
};

type IconName = keyof typeof iconPaths;

const sizeMap = {
  xs: 12,
  sm: 16,
  default: 20,
  lg: 24,
} as const;

type IconSize = keyof typeof sizeMap;

interface IconProps extends Omit<SVGAttributes<SVGSVGElement>, "children"> {
  name: IconName;
  size?: IconSize;
}

const Icon = forwardRef<SVGSVGElement, IconProps>(
  ({ name, size = "default", className, ...props }, ref) => {
    const px = sizeMap[size];
    const paths = iconPaths[name];

    if (!paths) {
      return null;
    }

    return (
      <svg
        ref={ref}
        xmlns="http://www.w3.org/2000/svg"
        width={px}
        height={px}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={cn("inline-block shrink-0", className)}
        {...props}
      >
        {paths}
      </svg>
    );
  }
);

Icon.displayName = "Icon";

export { Icon, iconPaths, sizeMap };
export type { IconName, IconSize, IconProps };
