export type { FileIconId, IconPackEntry, IconPack } from "./types";
export { resolveFileIcon } from "./resolve";
export { materialPack } from "./packs/material";

import type { IconPack, IconPackEntry } from "./types";
import { resolveFileIcon } from "./resolve";
import { materialPack } from "./packs/material";

// ---------------------------------------------------------------------------
// Active icon pack — swappable at runtime
// ---------------------------------------------------------------------------

let activePack: IconPack = materialPack;

/** Replace the active icon pack (e.g. for theming) */
export function setIconPack(pack: IconPack): void {
  activePack = pack;
}

/** Get the active icon pack */
export function getIconPack(): IconPack {
  return activePack;
}

/**
 * Convenience: resolve a file/folder name and look up its icon in the active pack.
 */
export function getIcon(
  fileName: string,
  type: "file" | "dir",
  isOpen?: boolean,
): IconPackEntry {
  const id = resolveFileIcon(fileName, type, isOpen);
  return activePack[id] ?? activePack.default;
}

/**
 * Get the icon color for a given file name.
 * Drop-in replacement for the old `getExtensionColor` used by PathBar.
 */
export function getFileColor(fileName: string): string {
  const id = resolveFileIcon(fileName, "file");
  const entry = activePack[id] ?? activePack.default;
  return entry.color;
}
