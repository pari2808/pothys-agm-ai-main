import { useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import { useNotificationStore } from '../store/notificationStore';

export interface NotificationItem {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: string;
  category: string;
  is_read: boolean;
  branch_id: string | null;
  created_at: string;
}

export function useNotifications(category?: string) {
  return useQuery<NotificationItem[]>({
    queryKey: ['notifications', category],
    queryFn: async () => {
      let url = '/notifications';
      if (category && category.toLowerCase() !== 'all') {
        url += `?category=${encodeURIComponent(category)}`;
      }
      const res = await apiClient.get(url);
      return res.data;
    },
    staleTime: 0,
    refetchOnMount: 'always',
    refetchInterval: 10000, // refresh notifications every 10s
  });
}

export function useUnreadCount() {
  const setUnreadCount = useNotificationStore((s) => s.setUnreadCount);

  const query = useQuery<{ count: number; unread_count?: number }>({
    queryKey: ['notifications-unread-count'],
    queryFn: async () => {
      const res = await apiClient.get('/notifications/unread-count');
      return res.data;
    },
    staleTime: 0,
    refetchOnMount: 'always',
    refetchInterval: 10000, // poll every 10s for badge updates
  });

  // Sync into Zustand store whenever data changes
  useEffect(() => {
    if (query.data != null) {
      const countVal = query.data.count ?? query.data.unread_count ?? 0;
      setUnreadCount(countVal);
    }
  }, [query.data, setUnreadCount]);

  return query;
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notificationId: string) => {
      const res = await apiClient.put(`/notifications/${notificationId}/read`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/notifications/mark-all-read');
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
    },
  });
}

export function useClearAllNotifications() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.delete('/notifications/clear-all');
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
    },
  });
}

export function useDeleteNotification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notificationId: string) => {
      const res = await apiClient.delete(`/notifications/${notificationId}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
    },
  });
}
