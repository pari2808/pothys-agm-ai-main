import React, { useState, useRef, useCallback } from 'react';
import Toast from '../components/Toast';

type RefetchTask = (() => Promise<any>) | null | undefined;

export interface UseRefreshOptions {
  onSuccess?: () => void;
  onError?: (error: any) => void;
  successMessage?: string;
  errorMessage?: string;
  showSuccessToast?: boolean;
}

export function useRefresh(
  refetchTasks?: RefetchTask | RefetchTask[],
  options?: UseRefreshOptions
) {
  const [refreshing, setRefreshing] = useState(false);
  const [toastVisible, setToastVisible] = useState(false);
  const [toastType, setToastType] = useState<'success' | 'error'>('success');
  const [toastMessage, setToastMessage] = useState('');

  // Single refresh state guard to prevent duplicate API requests
  const isRefreshingRef = useRef(false);

  const triggerRefresh = useCallback(async () => {
    if (isRefreshingRef.current) {
      return;
    }

    isRefreshingRef.current = true;
    setRefreshing(true);
    setToastVisible(false);

    try {
      if (refetchTasks) {
        const tasks = Array.isArray(refetchTasks) ? refetchTasks : [refetchTasks];
        const validTasks = tasks.filter((t): t is () => Promise<any> => typeof t === 'function');

        await Promise.all(validTasks.map((fn) => fn()));
      }

      options?.onSuccess?.();

      if (options?.showSuccessToast !== false) {
        setToastType('success');
        setToastMessage(options?.successMessage || 'Dashboard updated successfully.');
        setToastVisible(true);
      }
    } catch (error) {
      console.error('Refresh error:', error);
      setToastType('error');
      setToastMessage(options?.errorMessage || 'Unable to refresh. Please try again.');
      setToastVisible(true);
      options?.onError?.(error);
    } finally {
      setRefreshing(false);
      isRefreshingRef.current = false;
    }
  }, [refetchTasks, options]);

  const hideToast = useCallback(() => {
    setToastVisible(false);
  }, []);

  const ToastComponent = useCallback(() => {
    return (
      <Toast
        visible={toastVisible}
        message={toastMessage}
        type={toastType}
        onDismiss={hideToast}
      />
    );
  }, [toastVisible, toastMessage, toastType, hideToast]);

  return {
    refreshing,
    triggerRefresh,
    onRefresh: triggerRefresh,
    toastVisible,
    toastMessage,
    toastType,
    hideToast,
    ToastComponent,
  };
}
