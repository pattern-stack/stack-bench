/**
 * Onboarding API hook.
 *
 * Encapsulates all onboarding backend calls using react-query.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";

interface OnboardingStatus {
  needs_onboarding: boolean;
  has_github: boolean;
  has_project: boolean;
}

interface GitHubOrg {
  login: string;
  avatar_url: string;
  description: string | null;
}

interface GitHubRepo {
  full_name: string;
  name: string;
  private: boolean;
  default_branch: string;
  description: string | null;
}

interface OnboardingCompleteResponse {
  project_id: string;
  workspace_id: string;
  project_name: string;
}

export function useOnboarding(selectedOrg: string | null) {
  const queryClient = useQueryClient();

  const status = useQuery<OnboardingStatus>({
    queryKey: ["onboarding", "status"],
    queryFn: () => apiClient.get<OnboardingStatus>("/api/v1/onboarding/status"),
    staleTime: 30_000,
  });

  const orgs = useQuery<GitHubOrg[]>({
    queryKey: ["onboarding", "github", "orgs"],
    queryFn: () => apiClient.get<GitHubOrg[]>("/api/v1/onboarding/github/orgs"),
    enabled: status.data?.has_github === true,
    staleTime: 60_000,
  });

  const repos = useQuery<GitHubRepo[]>({
    queryKey: ["onboarding", "github", "repos", selectedOrg],
    queryFn: () =>
      apiClient.get<GitHubRepo[]>("/api/v1/onboarding/github/repos", {
        org: selectedOrg ?? undefined,
      }),
    enabled: !!selectedOrg,
    staleTime: 60_000,
  });

  const complete = useMutation<
    OnboardingCompleteResponse,
    Error,
    void
  >({
    mutationFn: () =>
      apiClient.post<OnboardingCompleteResponse>(
        "/api/v1/onboarding/complete",
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["onboarding", "status"] });
    },
  });

  const invalidateStatus = () => {
    queryClient.invalidateQueries({ queryKey: ["onboarding", "status"] });
  };

  return {
    status,
    orgs,
    repos,
    complete,
    invalidateStatus,
  };
}
