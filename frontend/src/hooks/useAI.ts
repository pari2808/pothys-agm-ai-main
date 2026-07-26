import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

export interface AIMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  retrieved_sources: string[] | null;
  created_at: string;
}

export interface AIConversation {
  id: string;
  title: string;
  created_at: string;
}

export interface AIConversationDetail extends AIConversation {
  messages: AIMessage[];
}

export interface AIQueryPayload {
  conversation_id?: string;
  content: string;
}

export interface EmailGeneratePayload {
  template_type: 'MEETING_INVITE' | 'MEETING_FOLLOWUP' | 'TASK_REMINDER' | 'GENERAL_ANNOUNCEMENT';
  context: string;
}

export interface EmailResponse {
  subject: string;
  body: string;
}

export function useAIConversations() {
  return useQuery<AIConversation[]>({
    queryKey: ['ai-conversations'],
    queryFn: async () => {
      const res = await apiClient.get('/ai/conversations');
      return res.data;
    },
  });
}

export function useAIConversationDetails(conversationId: string) {
  return useQuery<AIConversationDetail>({
    queryKey: ['ai-conversation-details', conversationId],
    queryFn: async () => {
      const res = await apiClient.get(`/ai/conversations/${conversationId}`);
      return res.data;
    },
    enabled: !!conversationId,
  });
}

export function useAICopilotQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: AIQueryPayload) => {
      const res = await apiClient.post('/ai/query', payload);
      return res.data;
    },
    onSuccess: () => {
      // Only refresh the sidebar conversation list — do NOT invalidate
      // conversation-details: the screen manages its own local message state
      // to avoid the useEffect(messages) re-render loop that caused the freeze.
      queryClient.invalidateQueries({ queryKey: ['ai-conversations'] });
    },
  });
}

export function useGenerateEmail() {
  return useMutation<EmailResponse, Error, EmailGeneratePayload>({
    mutationFn: async (payload) => {
      const res = await apiClient.post('/emails/generate', payload);
      return res.data;
    },
  });
}
