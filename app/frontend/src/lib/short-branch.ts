/** Extract short branch name from full ref: "dug/frontend-mvp/3-stack-nav" → "3-stack-nav" */
export function shortBranch(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}
