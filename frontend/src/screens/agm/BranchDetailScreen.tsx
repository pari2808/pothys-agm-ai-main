import React, { useEffect, useRef, useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  Animated,
  RefreshControl,
  TouchableOpacity,
  Modal,
  Alert,
  Image,
} from 'react-native';
import { getBranchImage } from '../../constants/branchImages';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useBranchAnalytics, useBranchesDashboard } from '../../hooks/useDashboard';
import { useRefresh } from '../../hooks/useRefresh';
import { useThemeStore } from '../../store/themeStore';
import { useAuthStore } from '../../store/authStore';
import { getShortBranchName } from '../../utils/branchHelper';
import { formatIndianCurrency } from '../../utils/currencyFormatter';
import { formatGrams, formatCarats, formatSilverMRP } from '../../utils/unitFormatter';
import { BranchStatus } from '../../hooks/useDashboard';
import { useQueryClient } from '@tanstack/react-query';
import apiClient from '../../services/api';
import { downloadAndShareReport } from '../../utils/pdfDownloadHelper';
import EmployeeLedgerTable from '../../components/EmployeeLedgerTable';
import SchemeLedgerTable from '../../components/SchemeLedgerTable';
import SchemeOverviewCard from '../../components/SchemeOverviewCard';
import ReportDatePicker from '../../components/ReportDatePicker';

interface BranchDetailScreenProps {
  navigation: any;
  route: {
    params: {
      branch: BranchStatus;
    };
  };
}

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


function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  const { colors } = useThemeStore();
  return (
    <View style={[styles.sectionCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>{title}</Text>
      {children}
    </View>
  );
}

function MetricRow({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  const { colors } = useThemeStore();
  return (
    <View style={[styles.metricRow, { borderColor: colors.border }]}>
      <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>{label}</Text>
      <Text style={[styles.metricValue, { color: colors.text }, valueColor ? { color: valueColor } : {}]}>{value}</Text>
    </View>
  );
}

function ProgressBar({ percent, color }: { percent: number; color?: string }) {
  const { colors } = useThemeStore();
  const animWidth = useRef(new Animated.Value(0)).current;
  const activeColor = color || colors.primary;

  useEffect(() => {
    Animated.timing(animWidth, {
      toValue: Math.min(100, percent),
      duration: 800,
      delay: 300,
      useNativeDriver: false,
    }).start();
  }, [percent]);

  return (
    <View style={[styles.progressTrack, { backgroundColor: colors.border }]}>
      <Animated.View
        style={[
          styles.progressFill,
          {
            backgroundColor: activeColor,
            width: animWidth.interpolate({
              inputRange: [0, 100],
              outputRange: ['0%', '100%'],
            }),
          },
        ]}
      />
    </View>
  );
}

export default function BranchDetailScreen({ navigation, route }: any) {
  const initialBranch = route.params.branch;
  const { data: branches, refetch: refetchBranches } = useBranchesDashboard();
  const branch = branches?.find(b => b.id === initialBranch.id) || initialBranch;
  
  // Report Date state: null = load latest, string = specific date
  const [reportDate, setReportDate] = useState<string | null>(null);
  
  const { data: analyticsData, isLoading, refetch: refetchAnalytics } = useBranchAnalytics(branch.id, reportDate);
  const analytics = analyticsData as any;
  const { colors, theme } = useThemeStore();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  
  const { refreshing, triggerRefresh, ToastComponent } = useRefresh([refetchAnalytics, refetchBranches]);
  
  const [menuVisible, setMenuVisible] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Derive the effective display date from the analytics response or selected date
  const effectiveDateStr: string | null = reportDate || analytics?.report_date || null;
  const pickerDate = effectiveDateStr
    ? new Date(effectiveDateStr + 'T00:00:00')
    : new Date();

  // Handle date change from the calendar picker
  const handleReportDateChange = (date: Date) => {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    setReportDate(`${yyyy}-${mm}-${dd}`);
  };

  useEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <View style={{ flexDirection: 'row', alignItems: 'center', marginRight: 12 }}>
          <TouchableOpacity 
            style={{ 
              width: 32,
              height: 32,
              borderRadius: 16,
              alignItems: 'center', 
              justifyContent: 'center', 
              backgroundColor: colors.surfaceAlt, 
              borderColor: colors.primary + '60', 
              borderWidth: 1, 
              opacity: refreshing ? 0.7 : 1,
            }}
            onPress={triggerRefresh}
            disabled={refreshing}
            activeOpacity={0.7}
          >
            {refreshing ? (
              <ActivityIndicator size="small" color={colors.primary} />
            ) : (
              <Text style={{ fontSize: 16, fontWeight: 'bold', color: colors.primary }}>↻</Text>
            )}
          </TouchableOpacity>
        </View>
      ),
    });
  }, [navigation, colors, refreshing, triggerRefresh]);

  const confirmDeleteReport = () => {
    if (!branch?.report?.id) return;
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
    if (!branch?.report?.id) return;
    setDeleting(true);
    try {
      await apiClient.delete(`/reports/${branch.report.id}`);
      Alert.alert("Success", "Report deleted successfully.");
      
      // Update state and navigate back
      queryClient.invalidateQueries({ queryKey: ['branches-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      navigation.goBack();
    } catch (err: any) {
      console.error(err);
      const msg = err.response?.data?.detail || "Failed to delete the report.";
      Alert.alert("Error", msg);
    } finally {
      setDeleting(false);
    }
  };

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 500,
      useNativeDriver: true,
    }).start();
  }, []);

  const safeToFixed = (val: any, precision: number = 1): string => {
    const num = Number(val);
    return isNaN(num) ? '0.0' : num.toFixed(precision);
  };

  const shortName = getShortBranchName(branch.name);
  
  // Derive report data from analytics response (date-aware)
  const report = analytics?.today_report_details?.report as any;
  const hasReport = !!report;
  const targetAchievement = Number(report?.target_achievement || 0);
  const hasIssues = report?.issues && report.issues.trim().length > 0;

  // Production template weight & MRP metrics (currency formatted)
  const goldVal = report?.gold;
  const diamondVal = report?.diamond;
  const platinumVal = report?.platinum;
  const silverVal = report?.silver;
  const silverMrpVal = report?.silver_mrp;
  const totalRevenue = report?.total_revenue || report?.sales_amount || 0;

  const formatMetricValue = (val: any): string => {
    if (val === null || val === undefined) return '--';
    const num = Number(val);
    if (isNaN(num) || num === 0) return '--';
    return formatIndianCurrency(num);
  };
  
  const digiGoldCount = report?.digigold || 0;
  const digiSilverCount = report?.digisilver || 0;

  const parseListItems = (rawText?: string | null): string[] => {
    if (!rawText || rawText.trim().length === 0 || rawText.trim().toLowerCase() === 'none') {
      return [];
    }
    return rawText
      .split(/\r?\n|;|•|▪|▫/)
      .map(line => line.replace(/^[\s\u2022\u25E6\u2023\u2043\-\*\d+\.\)]+\s*/, '').trim())
      .filter(line => line.length > 0 && line.toLowerCase() !== 'none');
  };

  const parseMultiLineRemarks = (rawText?: string | null): string[] => {
    if (!rawText || rawText.trim().length === 0 || rawText.trim().toLowerCase() === 'none') {
      return [];
    }
    return rawText
      .split(/\r?\n/)
      .map(line => line.trim())
      .filter(line => line.length > 0 && line.toLowerCase() !== 'none');
  };

  const complaintItems = parseListItems(report?.customer_complaints);
  const opsIssuesRaw = (report?.operational_issues && report.operational_issues.trim().toLowerCase() !== 'none')
    ? report.operational_issues
    : report?.issues;
  const opsItems = parseListItems(opsIssuesRaw);
  const remarkLines = parseMultiLineRemarks(report?.remarks);

  // Extracted employee & scheme details from analytics payload
  const empPerformances = analytics?.today_report_details?.employee_performances || [];
  const topPerformer = analytics?.today_report_details?.top_performer || "N/A";
  const schemeSummary = analytics?.today_report_details?.scheme_summary;
  const schemeItems = schemeSummary?.scheme_items || [];

  // State 1: Loading State — display professional loader while API fetches for the first time
  if (isLoading && !analyticsData) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['bottom']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator color={colors.primary} size="large" />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            Loading {shortName} details...
          </Text>
        </View>
        <ToastComponent />
      </SafeAreaView>
    );
  }

  // State 3: Empty State — API completed but no report submitted for selected date
  if (!hasReport) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['bottom']}>
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          <Animated.View style={{ opacity: fadeAnim }}>
            {/* Report Date Picker */}
            <View style={styles.datePickerRow}>
              <ReportDatePicker
                selectedDate={pickerDate}
                onDateChange={handleReportDateChange}
              />
            </View>

            {/* Branch Hero Header */}
            <View style={styles.heroSection}>
              <View style={[styles.heroImageContainer, { borderColor: colors.primary + '50' }]}>
                <Image
                  source={getBranchImage(shortName)}
                  style={styles.heroBranchImage}
                  resizeMode="cover"
                />
              </View>
              <Text style={[styles.heroName, { color: colors.text }]}>{shortName}</Text>
              <Text style={[styles.heroCode, { color: colors.textSecondary }]}>{branch.code} · Swarna Mahal</Text>
              
              <View style={[
                styles.heroBadge,
                { backgroundColor: colors.warning + '18', borderColor: colors.warning + '40', borderWidth: 1 }
              ]}>
                <View style={[styles.heroBadgeDot, { backgroundColor: colors.warning }]} />
                <Text style={[styles.heroBadgeText, { color: colors.warning }]}>
                  Report Not Submitted
                </Text>
              </View>
            </View>

            {/* Clean Empty State Card */}
            <View style={[styles.emptyContainerCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
              <Text style={{ fontSize: 36, marginBottom: 12 }}>📋</Text>
              <Text style={[styles.emptyTitle, { color: colors.text }]}>No Report Submitted</Text>
              <Text style={[styles.emptySub, { color: colors.textSecondary }]}>
                No operational report has been submitted for {shortName} on {effectiveDateStr ? effectiveDateStr : 'the selected date'}.
              </Text>
            </View>
          </Animated.View>
        </ScrollView>
        <ToastComponent />
      </SafeAreaView>
    );
  }

  // State 2: Success State — Full populated report page
  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['bottom']}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Animated.View style={{ opacity: fadeAnim }}>
          {/* Report Date Picker */}
          <View style={styles.datePickerRow}>
            <ReportDatePicker
              selectedDate={pickerDate}
              onDateChange={handleReportDateChange}
            />
          </View>

          {/* Branch Hero Header */}
          <View style={styles.heroSection}>
            <View style={[styles.heroImageContainer, { borderColor: colors.primary + '50' }]}>
              <Image
                source={getBranchImage(shortName)}
                style={styles.heroBranchImage}
                resizeMode="cover"
              />
            </View>
            <Text style={[styles.heroName, { color: colors.text }]}>{shortName}</Text>
            <Text style={[styles.heroCode, { color: colors.textSecondary }]}>{branch.code} · Swarna Mahal</Text>
            <View style={[
              styles.heroBadge,
              { backgroundColor: colors.success + '18', borderColor: colors.success + '40', borderWidth: 1 }
            ]}>
              <View style={[styles.heroBadgeDot, { backgroundColor: colors.success }]} />
              <Text style={[styles.heroBadgeText, { color: colors.success }]}>
                Report Submitted
              </Text>
            </View>
            {(report?.uploaded_at || report?.created_at) && (
              <Text style={[{ fontSize: 12, marginTop: 6, fontWeight: '500' }, { color: colors.textSecondary }]}>
                Submitted at: {formatExactTimestamp(report.uploaded_at || report.created_at)}
              </Text>
            )}
          </View>

          {/* Business Summary */}
          <SectionCard title="BUSINESS SUMMARY">
            <MetricRow label="Gold" value={formatGrams(goldVal)} />
            <MetricRow label="Diamond" value={formatCarats(diamondVal)} />
            <MetricRow label="Platinum" value={formatGrams(platinumVal)} />
            <MetricRow label="Silver" value={formatGrams(silverVal)} />
            <MetricRow label="Silver MRP" value={formatSilverMRP(silverMrpVal)} />
          </SectionCard>

          {/* Top Performer Banner */}
          <View style={[styles.topPerformerCard, { backgroundColor: colors.surfaceAlt, borderColor: colors.primary + '60', borderWidth: 1.5 }]}>
            <Text style={styles.topPerformerIcon}>👑</Text>
            <View style={{ flex: 1 }}>
              <Text style={[styles.topPerformerLabel, { color: colors.primary }]}>TOP PERFORMING EXECUTIVE</Text>
              <Text style={[styles.topPerformerValue, { color: colors.text }]}>{topPerformer}</Text>
            </View>
          </View>

          {/* Employee Performance Ledger */}
          <EmployeeLedgerTable employees={empPerformances} />

          {/* Scheme Overview */}
          <SchemeOverviewCard
            schemeItems={schemeItems}
            schemeSummary={schemeSummary}
            reportData={report}
          />

          {/* Operations Summary */}
          <SectionCard title="OPERATIONS SUMMARY">
            {/* 🔴 CUSTOMER COMPLAINTS */}
            <View style={styles.opsSection}>
              <Text style={[styles.opsSectionHeader, { color: colors.text }]}>
                🔴 CUSTOMER COMPLAINTS
              </Text>
              <View style={[styles.opsDivider, { backgroundColor: colors.border }]} />
              {complaintItems.length > 0 ? (
                complaintItems.map((item, idx) => (
                  <Text key={`complaint-${idx}`} style={[styles.opsItemText, { color: colors.text }]}>
                    • {item}
                  </Text>
                ))
              ) : (
                <Text style={[styles.opsEmptyText, { color: colors.textMuted }]}>
                  No customer complaints reported.
                </Text>
              )}
            </View>

            {/* 🟠 OPERATIONAL ISSUES */}
            <View style={[styles.opsSection, { marginTop: 18 }]}>
              <Text style={[styles.opsSectionHeader, { color: colors.text }]}>
                🟠 OPERATIONAL ISSUES
              </Text>
              <View style={[styles.opsDivider, { backgroundColor: colors.border }]} />
              {opsItems.length > 0 ? (
                opsItems.map((item, idx) => (
                  <Text key={`ops-${idx}`} style={[styles.opsItemText, { color: colors.text }]}>
                    • {item}
                  </Text>
                ))
              ) : (
                <Text style={[styles.opsEmptyText, { color: colors.textMuted }]}>
                  No operational issues reported.
                </Text>
              )}
            </View>

            {/* 📝 MANAGER REMARKS */}
            <View style={[styles.opsSection, { marginTop: 18 }]}>
              <Text style={[styles.opsSectionHeader, { color: colors.text }]}>
                📝 MANAGER REMARKS
              </Text>
              <View style={[styles.opsDivider, { backgroundColor: colors.border }]} />
              {remarkLines.length > 0 ? (
                remarkLines.map((line, idx) => (
                  <Text key={`remark-${idx}`} style={[styles.opsRemarkText, { color: colors.text }]}>
                    {line}
                  </Text>
                ))
              ) : (
                <Text style={[styles.opsEmptyText, { color: colors.textMuted }]}>
                  No manager remarks available.
                </Text>
              )}
            </View>
          </SectionCard>

          {/* AI Copilot Drilldown Button */}
          <TouchableOpacity
            style={[styles.aiCard, { backgroundColor: colors.surfaceAlt, borderColor: colors.primary + '33', borderWidth: 1 }]}
            onPress={() => navigation.navigate('AICopilot')}
            activeOpacity={0.8}
          >
            <View style={styles.aiHeaderRow}>
              <Text style={[styles.aiCardTitle, { color: colors.primary }]}>✨ Ask Branch AI Assistant</Text>
              <Text style={styles.aiArrow}>→</Text>
            </View>
            <Text style={[styles.aiCardDesc, { color: colors.textSecondary }]}>
              Analyze performance gaps, target achievements, or employee sales trends for {shortName} using the copilot.
            </Text>
          </TouchableOpacity>
        </Animated.View>
      </ScrollView>

      {/* Popup Menu Modal */}
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
              {getShortBranchName(branch.name)} Options
            </Text>
            <View style={[styles.menuDivider, { backgroundColor: colors.border }]} />

            {/* Download Report */}
            {user?.role === 'AGM' && (
              <TouchableOpacity 
                style={styles.menuItem}
                onPress={async () => {
                  setMenuVisible(false);
                  if (!report?.id) return;
                  try {
                    const sName = getShortBranchName(branch.name);
                    const todayStr = report.date || new Date().toISOString().split('T')[0];
                    await downloadAndShareReport(report.id, sName, todayStr);
                  } catch (e: any) {
                    Alert.alert("Error", "Failed to download PDF.");
                  }
                }}
              >
                <Text style={styles.menuItemIcon}>📥</Text>
                <Text style={[styles.menuItemText, { color: colors.text }]}>Download Report</Text>
              </TouchableOpacity>
            )}

            {/* Delete Report */}
            {user?.role === 'AGM' && (
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

  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  loadingText: {
    marginTop: 14,
    fontSize: 15,
    fontWeight: '600',
  },
  emptyContainerCard: {
    borderRadius: 20,
    borderWidth: 1,
    padding: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
    marginBottom: 24,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '800',
    marginBottom: 6,
  },
  emptySub: {
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 18,
  },

  scrollContent: {
    padding: 20,
    paddingBottom: 48,
  },
  heroSection: {
    alignItems: 'center',
    paddingVertical: 16,
    marginBottom: 8,
  },
  heroIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  heroImageContainer: {
    width: 84,
    height: 84,
    borderRadius: 42,
    borderWidth: 2,
    overflow: 'hidden',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 4,
  },
  heroBranchImage: {
    width: '100%',
    height: '100%',
  },
  heroIconText: {
    fontSize: 28,
  },
  heroName: {
    fontSize: 26,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  heroCode: {
    fontSize: 12,
    marginTop: 2,
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
  heroBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    marginTop: 10,
    gap: 8,
  },
  heroBadgeDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  heroBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  sectionCard: {
    borderRadius: 20,
    borderWidth: 1,
    padding: 18,
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 2,
    marginBottom: 12,
  },
  summaryTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  summaryLabel: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 1.5,
    marginBottom: 2,
  },
  targetStatusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  targetPercentText: {
    fontSize: 12,
    fontWeight: '700',
  },
  progressRow: {
    marginTop: 10,
    marginBottom: 10,
  },
  subSectionTitle: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1.5,
    marginBottom: 6,
  },
  bigSalesNumber: {
    fontSize: 36,
    fontWeight: '900',
    letterSpacing: -0.5,
  },
  bigSalesUnit: {
    fontSize: 20,
    fontWeight: '400',
  },
  sectionNote: {
    fontSize: 14,
    marginTop: 6,
  },
  targetRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginBottom: 14,
  },
  targetPercent: {
    fontSize: 36,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  targetLabel: {
    fontSize: 14,
    flexShrink: 1,
    lineHeight: 20,
  },
  progressTrack: {
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: 6,
    borderRadius: 3,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  metricLabel: {
    fontSize: 13,
  },
  metricValue: {
    fontSize: 15,
    fontWeight: '700',
  },
  auditColumn: {
    flexDirection: 'column',
    gap: 4,
  },
  auditLabel: {
    fontSize: 11,
    fontWeight: '600',
  },
  auditText: {
    fontSize: 13,
    fontWeight: '500',
    lineHeight: 18,
  },
  opsSection: {
    flexDirection: 'column',
  },
  opsSectionHeader: {
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  opsDivider: {
    height: 1,
    width: '100%',
    marginBottom: 10,
    opacity: 0.8,
  },
  opsItemText: {
    fontSize: 14,
    lineHeight: 22,
    fontWeight: '500',
    marginBottom: 4,
  },
  opsRemarkText: {
    fontSize: 14,
    lineHeight: 22,
    fontWeight: '400',
    marginBottom: 6,
  },
  opsEmptyText: {
    fontSize: 13,
    fontStyle: 'italic',
    lineHeight: 20,
  },
  alertBox: {
    borderRadius: 12,
    padding: 16,
  },
  alertText: {
    fontSize: 15,
    lineHeight: 22,
  },
  remarksText: {
    fontSize: 15,
    lineHeight: 24,
    fontStyle: 'italic',
  },
  topPerformerCard: {
    borderRadius: 20,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginBottom: 12,
  },
  topPerformerIcon: {
    fontSize: 28,
  },
  topPerformerLabel: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1.5,
    marginBottom: 2,
  },
  topPerformerValue: {
    fontSize: 15,
    fontWeight: '700',
  },
  tableHeader: {
    flexDirection: 'row',
    paddingBottom: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#cbd5e1',
    marginBottom: 6,
  },
  tableColName: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  tableRow: {
    flexDirection: 'row',
    paddingVertical: 8,
    borderBottomWidth: 0.5,
    alignItems: 'center',
  },
  empTableName: {
    fontSize: 13,
    fontWeight: '700',
  },
  empTableDesc: {
    fontSize: 12,
  },
  empTableSales: {
    fontSize: 13,
    fontWeight: '600',
  },
  empTableSchemes: {
    fontSize: 13,
    fontWeight: '700',
  },
  analyticsLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 20,
    justifyContent: 'center',
  },
  analyticsLoadingText: {
    fontSize: 14,
  },
  pendingState: {
    alignItems: 'center',
    paddingVertical: 40,
    paddingHorizontal: 24,
  },
  pendingStateIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  pendingStateTitle: {
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 8,
  },
  pendingStateDesc: {
    fontSize: 15,
    textAlign: 'center',
    lineHeight: 22,
  },
  aiCard: {
    borderRadius: 20,
    padding: 18,
    marginTop: 4,
    marginBottom: 8,
  },
  aiHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  aiArrow: {
    fontSize: 18,
    fontWeight: '700',
  },
  aiCardTitle: {
    fontSize: 15,
    fontWeight: '700',
  },
  aiCardDesc: {
    fontSize: 14,
    lineHeight: 22,
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
  datePickerRow: {
    alignItems: 'flex-end',
    marginBottom: 4,
  },
  noReportMessage: {
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 20,
    marginTop: 8,
    paddingHorizontal: 24,
  },
  emptyCardText: {
    fontSize: 14,
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: 16,
    lineHeight: 20,
  },
});
