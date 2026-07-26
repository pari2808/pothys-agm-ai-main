import React, { useMemo, useState, useCallback } from 'react';
import {
  StyleSheet,
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
  Modal,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  useNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
  useClearAllNotifications,
  useDeleteNotification,
  NotificationItem,
} from '../../hooks/useNotifications';
import { useBranchesDashboard } from '../../hooks/useDashboard';
import { useThemeStore } from '../../store/themeStore';
import { useRefresh } from '../../hooks/useRefresh';

type FilterCategory = 'All' | 'Updates' | 'Action Required';

function formatExactTimestamp(dateStr: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return dateStr;

  const day = date.getDate().toString().padStart(2, '0');
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = months[date.getMonth()];
  const year = date.getFullYear();

  let hours = date.getHours();
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12;
  hours = hours ? hours : 12;
  const formattedHours = hours.toString().padStart(2, '0');

  return `${day} ${month} ${year}, ${formattedHours}:${minutes} ${ampm}`;
}

export default function NotificationCenterScreen({ navigation }: any) {
  const { colors } = useThemeStore();
  const [activeFilter, setActiveFilter] = useState<FilterCategory>('All');
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [deletingItem, setDeletingItem] = useState<NotificationItem | null>(null);

  const { data: notifications, isLoading, refetch } = useNotifications();
  const { data: branches, refetch: refetchBranches } = useBranchesDashboard();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const clearAllNotifications = useClearAllNotifications();
  const deleteNotification = useDeleteNotification();

  const { refreshing, onRefresh, ToastComponent } = useRefresh([refetch, refetchBranches]);

  // Map type & category to theme color, background color & icon
  const getThemeDetails = (item: NotificationItem) => {
    const t = (item.type || item.title || '').toLowerCase();
    const cat = item.category || 'Updates';

    if (t.includes('pending') || t.includes('report pending')) {
      return {
        color: colors.warning,
        bgColor: 'rgba(245, 158, 11, 0.12)',
        icon: '⏳',
        category: 'Action Required',
      };
    }
    if (t.includes('issue') || t.includes('critical')) {
      return {
        color: colors.error,
        bgColor: 'rgba(239, 68, 68, 0.12)',
        icon: '🚨',
        category: 'Action Required',
      };
    }
    if (t.includes('complaint')) {
      return {
        color: colors.error,
        bgColor: 'rgba(239, 68, 68, 0.12)',
        icon: '👤',
        category: 'Action Required',
      };
    }
    if (t.includes('attendance')) {
      return {
        color: colors.warning,
        bgColor: 'rgba(245, 158, 11, 0.12)',
        icon: '📊',
        category: 'Action Required',
      };
    }
    if (t.includes('target') || t.includes('threshold')) {
      return {
        color: colors.error,
        bgColor: 'rgba(239, 68, 68, 0.12)',
        icon: '📉',
        category: 'Action Required',
      };
    }
    if (t.includes('submitted')) {
      return {
        color: colors.success,
        bgColor: 'rgba(16, 185, 129, 0.12)',
        icon: '✅',
        category: 'Updates',
      };
    }
    if (t.includes('updated')) {
      return {
        color: colors.info,
        bgColor: 'rgba(59, 130, 246, 0.12)',
        icon: '🔄',
        category: 'Updates',
      };
    }
    if (t.includes('highest') || t.includes('top')) {
      return {
        color: colors.success,
        bgColor: 'rgba(16, 185, 129, 0.12)',
        icon: '🏆',
        category: 'Updates',
      };
    }

    return {
      color: cat === 'Action Required' ? colors.warning : colors.info,
      bgColor: cat === 'Action Required' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(59, 130, 246, 0.12)',
      icon: cat === 'Action Required' ? '⚠️' : '🔔',
      category: cat,
    };
  };

  // Filter and sort notifications (newest first)
  const filteredNotifications = useMemo(() => {
    if (!notifications) return [];
    
    // Sort newest first
    const sorted = [...notifications].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
    
    if (activeFilter === 'All') return sorted;
    return sorted.filter(n => {
      const details = getThemeDetails(n);
      return details.category === activeFilter || n.category === activeFilter;
    });
  }, [notifications, activeFilter]);

  const unreadCount = notifications?.filter(n => !n.is_read).length || 0;

  const handleMarkAllRead = useCallback(() => {
    markAllRead.mutate();
  }, [markAllRead]);

  const handleConfirmDelete = useCallback(() => {
    if (deletingItem) {
      deleteNotification.mutate(deletingItem.id);
      setDeletingItem(null);
    } else {
      clearAllNotifications.mutate();
      setShowConfirmModal(false);
    }
  }, [deletingItem, deleteNotification, clearAllNotifications]);

  const handleNotificationPress = useCallback((notification: NotificationItem) => {
    if (!notification.is_read) {
      markRead.mutate(notification.id);
    }

    if (notification.branch_id && branches) {
      const branch = branches.find(b => b.id === notification.branch_id);
      if (branch) {
        navigation.navigate('BranchDetail', { branch });
        return;
      }
    }
    navigation.navigate('BranchOperations');
  }, [markRead, branches, navigation]);

  if (isLoading && !refreshing) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor: colors.background }]}>
        <ActivityIndicator color={colors.primary} size="large" />
        <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Loading notifications...</Text>
      </View>
    );
  }

  const filterTabs: { label: string; value: FilterCategory; color: string }[] = [
    { label: 'All', value: 'All', color: colors.primary },
    { label: 'Updates', value: 'Updates', color: colors.success },
    { label: 'Action Required', value: 'Action Required', color: colors.error },
  ];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['bottom']}>
      {/* Action Header Strip */}
      <View style={[styles.actionHeader, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.unreadStatusText, { color: colors.textSecondary }]}>
          {unreadCount === 0 ? 'No unread notifications' : `${unreadCount} unread notification(s)`}
        </Text>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          {/* Unique Double-Check Logo Button for Mark All As Read */}
          <TouchableOpacity
            style={[
              styles.markAllReadIconBtn,
              {
                borderColor: unreadCount > 0 ? colors.primary + '80' : colors.border,
                backgroundColor: unreadCount > 0 ? colors.primary + '18' : colors.surfaceAlt,
                opacity: unreadCount > 0 ? 1 : 0.45,
              },
            ]}
            onPress={handleMarkAllRead}
            disabled={unreadCount === 0}
            activeOpacity={0.7}
            title="Mark all notifications as read"
          >
            <Text style={[styles.markAllReadIconText, { color: unreadCount > 0 ? colors.primary : colors.textMuted }]}>
              ✓✓
            </Text>
          </TouchableOpacity>

          {/* Delete All Bin Button */}
          {notifications && notifications.length > 0 && (
            <TouchableOpacity
              style={[styles.binBtn, { borderColor: colors.error + '60', backgroundColor: colors.error + '15' }]}
              onPress={() => setShowConfirmModal(true)}
              activeOpacity={0.7}
              title="Delete all notifications history"
            >
              <Text style={{ fontSize: 15 }}>🗑️</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Categories Filter Tabs */}
      <View style={[styles.tabsWrapper, { backgroundColor: colors.surface, borderBottomColor: colors.border }]}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabsScroll}>
          {filterTabs.map(tab => {
            const isActive = activeFilter === tab.value;
            return (
              <TouchableOpacity
                key={tab.value}
                style={[
                  styles.tabButton,
                  { borderColor: colors.border },
                  isActive && {
                    backgroundColor: tab.color + '18',
                    borderColor: tab.color,
                  },
                ]}
                onPress={() => setActiveFilter(tab.value)}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.tabLabel,
                    { color: colors.textSecondary },
                    isActive && { color: tab.color, fontWeight: '700' },
                  ]}
                >
                  {tab.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {/* Notifications List */}
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
      >
        {filteredNotifications.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyIcon}>🔔</Text>
            <Text style={[styles.emptyTitle, { color: colors.text }]}>No Notifications</Text>
            <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
              You're all caught up! Detailed daily updates and operational alerts will appear here.
            </Text>
          </View>
        ) : (
          filteredNotifications.map(item => {
            const isRead = item.is_read;
            const details = getThemeDetails(item);
            return (
              <TouchableOpacity
                key={item.id}
                style={[
                  styles.card,
                  {
                    backgroundColor: isRead ? colors.surface : colors.surfaceAlt,
                    borderColor: colors.border,
                    borderLeftColor: details.color,
                  },
                  !isRead && styles.unreadCard,
                ]}
                onPress={() => handleNotificationPress(item)}
                activeOpacity={0.75}
              >
                <View style={[styles.iconWrapper, { backgroundColor: details.bgColor }]}>
                  <Text style={styles.icon}>{details.icon}</Text>
                </View>
                <View style={styles.cardContent}>
                  <View style={styles.cardHeader}>
                    <Text
                      style={[
                        styles.cardTitle,
                        { color: colors.text },
                        !isRead && styles.unreadTitleText,
                      ]}
                      numberOfLines={1}
                    >
                      {item.title}
                    </Text>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                      {!isRead && <View style={[styles.unreadDot, { backgroundColor: details.color }]} />}
                      <TouchableOpacity
                        style={styles.itemTrashBtn}
                        onPress={(e) => {
                          e.stopPropagation();
                          setDeletingItem(item);
                        }}
                        activeOpacity={0.7}
                      >
                        <Text style={{ fontSize: 13, opacity: 0.7 }}>🗑️</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                  <Text style={[styles.cardMessage, { color: colors.textSecondary }]} numberOfLines={3}>
                    {item.message}
                  </Text>
                  <Text style={[styles.cardTime, { color: colors.textMuted }]}>
                    {formatExactTimestamp(item.created_at)}
                  </Text>
                </View>
              </TouchableOpacity>
            );
          })
        )}
      </ScrollView>

      {/* Confirmation Modal for Deleting History */}
      <Modal
        visible={showConfirmModal || !!deletingItem}
        transparent
        animationType="fade"
        onRequestClose={() => {
          setShowConfirmModal(false);
          setDeletingItem(null);
        }}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <View style={[styles.modalIconBg, { backgroundColor: colors.error + '20' }]}>
              <Text style={{ fontSize: 28 }}>🗑️</Text>
            </View>
            <Text style={[styles.modalTitle, { color: colors.text }]}>
              {deletingItem ? 'Delete Notification' : 'Clear Notification History'}
            </Text>
            <Text style={[styles.modalDescription, { color: colors.textSecondary }]}>
              {deletingItem
                ? 'Are you sure you want to delete this notification? It will be permanently removed from the database.'
                : 'Are you sure you want to completely delete your notification history? This will permanently remove all notifications from the web page and database.'}
            </Text>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={[styles.modalCancelBtn, { borderColor: colors.border, backgroundColor: colors.surfaceAlt }]}
                onPress={() => {
                  setShowConfirmModal(false);
                  setDeletingItem(null);
                }}
                activeOpacity={0.7}
              >
                <Text style={[styles.modalCancelText, { color: colors.text }]}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalDeleteBtn, { backgroundColor: colors.error }]}
                onPress={handleConfirmDelete}
                activeOpacity={0.7}
              >
                <Text style={styles.modalDeleteText}>
                  {deletingItem ? 'Delete' : 'Delete All'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {ToastComponent}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
  },
  actionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  unreadStatusText: {
    fontSize: 13,
    fontWeight: '500',
  },
  markReadBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
  },
  markReadText: {
    fontSize: 12,
    fontWeight: '600',
  },
  markAllReadIconBtn: {
    width: 32,
    height: 32,
    borderRadius: 6,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  markAllReadIconText: {
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: -1,
  },
  binBtn: {
    width: 32,
    height: 32,
    borderRadius: 6,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemTrashBtn: {
    padding: 4,
    borderRadius: 4,
  },
  tabsWrapper: {
    borderBottomWidth: 1,
  },
  tabsScroll: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 8,
  },
  tabButton: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabLabel: {
    fontSize: 13,
    fontWeight: '500',
  },
  scrollContent: {
    padding: 16,
    gap: 12,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 80,
    paddingHorizontal: 32,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },
  card: {
    flexDirection: 'row',
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderLeftWidth: 4,
    marginBottom: 10,
  },
  unreadCard: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  iconWrapper: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  icon: {
    fontSize: 20,
  },
  cardContent: {
    flex: 1,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '600',
    flex: 1,
  },
  unreadTitleText: {
    fontWeight: '700',
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  cardMessage: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 6,
  },
  cardTime: {
    fontSize: 11,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalContent: {
    width: '100%',
    maxWidth: 400,
    borderRadius: 16,
    borderWidth: 1,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 8,
  },
  modalIconBg: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
    textAlign: 'center',
  },
  modalDescription: {
    fontSize: 14,
    lineHeight: 20,
    textAlign: 'center',
    marginBottom: 24,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
  },
  modalCancelBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalCancelText: {
    fontSize: 14,
    fontWeight: '600',
  },
  modalDeleteBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalDeleteText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
});
