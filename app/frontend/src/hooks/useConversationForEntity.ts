import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";

export interface ConversationSummary {
  id: string;
  reference_number: string | null;
  agent_name: string;
  model: string;
  state: string;
  conversation_type: string;
  error_message: string | null;
  exchange_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  project_id: string | null;
  branched_from_id: string | null;
  branched_at_sequence: number | null;
  created_at: string;
  updated_at: string;
}

export const conversationEntityKeys = {
  all: ["conversation-by-entity"] as const,
  entity: (entityType: string, entityId: string, role: string) =>
    [...conversationEntityKeys.all, entityType, entityId, role] as const,
};

export function useConversationForEntity(
  entityType: string,
  entityId: string | undefined,
  role: string
) {
  const { data = null, isLoading, error } = useQuery({
    queryKey: conversationEntityKeys.entity(
      entityType,
      entityId ?? "",
      role
    ),
    queryFn: () =>
      apiClient.get<ConversationSummary | null>(
        `/api/v1/conversations/by-entity`,
        {
          entity_type: entityType,
          entity_id: entityId!,
          role,
        }
      ),
    enabled: !!entityId,
  });

  return { conversation: data, loading: isLoading, error: error ? String(error) : null };
}
