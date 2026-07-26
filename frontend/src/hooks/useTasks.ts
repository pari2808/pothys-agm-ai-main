import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

export interface Task {
  id: string;
  title: string;
  description: string | null;
  assigned_to: string;
  assigned_by: string;
  due_date: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED';
  manager_remarks: string | null;
  created_at: string;
}

export interface CreateTaskPayload {
  title: string;
  description?: string;
  assigned_to: string;
  due_date: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface UpdateTaskPayload {
  taskId: string;
  title?: string;
  description?: string;
  assigned_to?: string;
  due_date?: string;
  priority?: 'LOW' | 'MEDIUM' | 'HIGH';
  status?: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED';
  manager_remarks?: string;
}

export function useTasks() {
  return useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: async () => {
      const res = await apiClient.get('/tasks');
      return res.data;
    },
  });
}

export function useTaskDetails(taskId: string) {
  return useQuery<Task>({
    queryKey: ['task-details', taskId],
    queryFn: async () => {
      const res = await apiClient.get(`/tasks/${taskId}`);
      return res.data;
    },
    enabled: !!taskId,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateTaskPayload) => {
      const res = await apiClient.post('/tasks', payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ taskId, ...updateData }: UpdateTaskPayload) => {
      const res = await apiClient.patch(`/tasks/${taskId}`, updateData);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['task-details', data.id] });
    },
  });
}
