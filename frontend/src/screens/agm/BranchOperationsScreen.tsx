import React, { useEffect, useRef, useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
  RefreshControl,
  Modal,
  Alert,
  Image,
} from 'react-native';

const branchStorefrontImg = require('../../../assets/branch_storefront.png');
import { getBranchImage } from '../../constants/branchImages';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useBranchesDashboard } from '../../hooks/useDashboard';
import { useThemeStore } from '../../store/themeStore';
import { useAuthStore } from '../../store/authStore';
import { useRefresh } from '../../hooks/useRefresh';
import { getShortBranchName } from '../../utils/branchHelper';
import { formatIndianCurrency } from '../../utils/currencyFormatter';
import { useQueryClient } from '@tanstack/react-query';
import apiClient from '../../services/api';
import { downloadAndShareReport } from '../../utils/pdfDownloadHelper';

function formatExactTimestamp(dateStr?: string | null): string {
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

export default function BranchOperationsScreen({ navigation }: any) {
  const { data: branches, isLoading, refetch } = useBranchesDashboard();
  const { colors } = useThemeStore();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const { refreshing, onRefresh, ToastComponent } = useRefresh(refetch);
  
  const [selectedBranch, setSelectedBranch] = useState<any>(null);
  const [menuVisible, setMenuVisible] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fadeAnims = useRef<Animated.Value[]>([]).current;
  const slideAnims = useRef<Animated.Value[]>([]).current;

  useEffect(() => {
    if (branches && branches.length > 0) {
      while (fadeAnims.length < branches.length) {
        fadeAnims.push(new Animated.Value(0));
        slideAnims.push(new Animated.Value(30));
      }

      const animations = branches.map((_, i) =>
        Animated.parallel([
          Animated.timing(fadeAnims[i], {
            toValue: 1,
            duration: 400,
            delay: i * 70,
            useNativeDriver: true,
          }),
          Animated.timing(slideAnims[i], {
            toValue: 0,
            duration: 400,
            delay: i * 70,
            useNativeDriver: true,
          }),
        ])
      );
      Animated.stagger(70, animations).start();
    }
  }, [branches]);

  const confirmDeleteReport = () => {
    if (!selectedBranch?.report?.id) return;
    Alert.alert(
      "Delete Report",
      "Are you sure you want to permanently delete today's report for this branch?",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Delete", 
          style: "destructive", 
          onPress: handleDeleteReport 
        }
      ]
    );
  };

  const handleDeleteReport = async () => {
    if (!selectedBranch?.report?.id) return;
    setDeleting(true);
    try {
      await apiClient.delete(`/reports/${selectedBranch.report.id}`);
      Alert.alert("Success", "Report deleted successfully.");
      
      await refetch();
      queryClient.invalidateQueries({ queryKey: ['branches-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    } catch (err: any) {
      console.error(err);
      const msg = err.response?.data?.detail || "Failed to delete the report.";
      Alert.alert("Error", msg);
    } finally {
      setDeleting(false);
      setSelectedBranch(null);
    }
  };

  const submittedCount = branches?.filter(b => b.status === 'SUBMITTED').length || 0;
  const pendingCount = branches?.filter(b => b.status === 'PENDING').length || 0;

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['bottom']}>
      <View style={[styles.summaryStrip, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: colors.text }]}>{branches?.length || 0}</Text>
          <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>TOTAL</Text>
        </View>
        <View style={[styles.summaryDivider, { backgroundColor: colors.border }]} />
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: colors.success }]}>{submittedCount}</Text>
          <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>SUBMITTED</Text>
        </View>
        <View style={[styles.summaryDivider, { backgroundColor: colors.border }]} />
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: colors.warning }]}>{pendingCount}</Text>
          <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>PENDING</Text>
        </View>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {isLoading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Loading branch data...</Text>
          </View>
        ) : (
          branches?.map((branch, index) => {
            const shortName = getShortBranchName(branch.name);
            const isSubmitted = branch.status === 'SUBMITTED';
            const isFeaturedBranch = true;
            const branchImgSource = getBranchImage(shortName);
            const salesPercent = branch.report
              ? Math.min(100, ((branch.report.target_achievement || 0))).toFixed(0)
              : null;
            const hasIssues = branch.report?.issues && branch.report.issues.trim().length > 0;

            const fadeAnim = fadeAnims[index] || new Animated.Value(1);
            const slideAnim = slideAnims[index] || new Animated.Value(0);

            return (
              <Animated.View
                key={branch.id}
                style={{
                  opacity: fadeAnim,
                  transform: [{ translateY: slideAnim }],
                }}
              >
                <TouchableOpacity
                  style={[
                    styles.cleanNavCard, 
                    isFeaturedBranch && styles.chromepetNavCard,
                    { backgroundColor: colors.surface, borderColor: colors.border },
                    isSubmitted && { borderColor: colors.primary + '35' }
                  ]}
                  onPress={() => navigation.navigate('BranchDetail', { branch })}
                  activeOpacity={0.85}
                >
                  {/* Left Side: Branch Heading & Status Badge */}
                  <View style={styles.cardLeftContent}>
                    <Text style={[
                      styles.cleanBranchTitle, 
                      isFeaturedBranch && styles.chromepetTitle,
                      { color: colors.text }
                    ]}>
                      {shortName}
                    </Text>

                    <View style={[
                      styles.cleanStatusBadge,
                      isSubmitted ? 
                        { backgroundColor: '#052e16', borderColor: '#166534' } : 
                        { backgroundColor: '#451a03', borderColor: '#92400e' }
                    ]}>
                      <Text style={{ fontSize: 10, marginRight: 5 }}>
                        {isSubmitted ? '🟢' : '🟡'}
                      </Text>
                      <Text style={[
                        styles.cleanStatusText,
                        { color: isSubmitted ? colors.success : colors.warning }
                      ]}>
                        {isSubmitted ? 'Submitted' : 'Pending'}
                      </Text>
                    </View>
                  </View>

                  {/* Right Side: Vertically Centered Branch Image */}
                  <View style={[
                    styles.cardRightImageContainer,
                    isFeaturedBranch && styles.chromepetImageContainer
                  ]}>
                    <Image
                      source={branchImgSource}
                      style={styles.cleanBranchImage}
                      resizeMode="cover"
                    />
                  </View>
                </TouchableOpacity>
              </Animated.View>
            );
          })
        )}
      </ScrollView>

      <Modal
        visible={menuVisible}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setMenuVisible(false)}
      >
        <TouchableOpacity 
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setMenuVisible(false)}
        >
          <View style={[styles.menuDropdown, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Text style={[styles.menuHeader, { color: colors.textSecondary }]}>
              {selectedBranch ? getShortBranchName(selectedBranch.name) : 'Branch Options'}
            </Text>
            <View style={[styles.menuDivider, { backgroundColor: colors.border }]} />
            
            {selectedBranch?.status !== 'SUBMITTED' && (
              <Text style={[styles.noReportText, { color: colors.textMuted }]}>
                Awaiting report submission for today.
              </Text>
            )}

            {selectedBranch?.status === 'SUBMITTED' && user?.role === 'AGM' && (
              <TouchableOpacity 
                style={styles.menuItem}
                onPress={async () => {
                  setMenuVisible(false);
                  if (!selectedBranch?.report?.id) return;
                  try {
                    const shortName = getShortBranchName(selectedBranch.name);
                    const todayStr = selectedBranch.report.date || new Date().toISOString().split('T')[0];
                    await downloadAndShareReport(selectedBranch.report.id, shortName, todayStr);
                  } catch (e: any) {
                    Alert.alert("Error", "Failed to download PDF.");
                  }
                }}
              >
                <Text style={styles.menuItemIcon}>📥</Text>
                <Text style={[styles.menuItemText, { color: colors.text }]}>Download Report</Text>
              </TouchableOpacity>
            )}

            {selectedBranch?.status === 'SUBMITTED' && user?.role === 'AGM' && (
              <TouchableOpacity 
                style={[styles.menuItem, styles.deleteMenuItem]}
                onPress={() => {
                  setMenuVisible(false);
                  confirmDeleteReport();
                }}
              >
                <Text style={[styles.menuItemIcon, { color: colors.error }]}>🗑</Text>
                <Text style={[styles.menuItemText, { color: colors.error }]}>Delete Report</Text>
              </TouchableOpacity>
            )}
          </View>
        </TouchableOpacity>
      </Modal>
      <ToastComponent />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  summaryStrip: {
    flexDirection: 'row',
    paddingVertical: 20,
    paddingHorizontal: 28,
    borderBottomWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  summaryItem: {
    alignItems: 'center',
    flex: 1,
  },
  summaryDivider: {
    width: 1,
    height: 32,
  },
  summaryValue: {
    fontSize: 24,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  summaryLabel: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 2,
    marginTop: 4,
  },
  scrollContent: {
    padding: 24,
    paddingBottom: 40,
  },
  loadingContainer: {
    paddingTop: 80,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 15,
  },
  cleanNavCard: {
    borderRadius: 16,
    borderWidth: 1,
    paddingHorizontal: 16,
    paddingVertical: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 3,
  },
  chromepetNavCard: {
    paddingHorizontal: 18,
    paddingVertical: 18,
    borderRadius: 20,
    marginBottom: 16,
  },
  cardLeftContent: {
    flex: 1,
    justifyContent: 'center',
    paddingRight: 12,
  },
  cleanBranchTitle: {
    fontSize: 20,
    fontWeight: '700',
    letterSpacing: -0.3,
    marginBottom: 8,
  },
  chromepetTitle: {
    fontSize: 22,
    fontWeight: '800',
    marginBottom: 10,
  },
  cleanStatusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
    borderWidth: 1,
  },
  cleanStatusText: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  cardRightImageContainer: {
    width: 105,
    height: 64,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  chromepetImageContainer: {
    width: 135,
    height: 82,
    borderRadius: 14,
  },
  cleanBranchImage: {
    width: '100%',
    height: '100%',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  menuDropdown: {
    width: '100%',
    maxWidth: 320,
    borderRadius: 20,
    borderWidth: 1,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.25,
    shadowRadius: 15,
    elevation: 10,
  },
  menuHeader: {
    fontSize: 16,
    fontWeight: '800',
    textAlign: 'center',
    marginBottom: 12,
    letterSpacing: 0.5,
  },
  menuDivider: {
    height: 1,
    width: '100%',
    marginBottom: 8,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderRadius: 12,
  },
  menuItemIcon: {
    fontSize: 18,
    marginRight: 12,
    width: 24,
    textAlign: 'center',
  },
  menuItemText: {
    fontSize: 15,
    fontWeight: '600',
  },
  deleteMenuItem: {
    marginTop: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(239, 68, 68, 0.2)',
  },
  noReportText: {
    paddingVertical: 12,
    fontSize: 14,
    textAlign: 'center',
    fontStyle: 'italic',
  },
});
