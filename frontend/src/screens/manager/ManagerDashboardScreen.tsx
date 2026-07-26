import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  Animated,
  Platform,
  Alert,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../../store/authStore';
import { useUploadReport } from '../../hooks/useReports';
import apiClient from '../../services/api';

// Use document picker from expo-document-picker which is already likely installed
// We guard the import for web compatibility
let DocumentPicker: any = null;
try {
  DocumentPicker = require('expo-document-picker');
} catch (_) {}

const COLORS = {
  background:    '#0B0B0E',
  surface:       '#121217',
  surfaceAlt:    '#1A1A22',
  border:        '#22222E',
  text:          '#F5F5F7',
  textSecondary: '#8E8E93',
  textMuted:     '#5C5C60',
  primary:       '#D4AF37',   // Gold (brand)
  accent:        '#3B82F6',   // Blue (manager accent)
  success:       '#10B981',
  successBg:     'rgba(16, 185, 129, 0.1)',
  error:         '#EF4444',
  errorBg:       'rgba(239, 68, 68, 0.1)',
  warning:       '#F59E0B',
  warningBg:     'rgba(245, 158, 11, 0.1)',
};

interface PickedFile {
  uri: string;
  name: string;
  type: string;
  size?: number;
  rawFile?: File; // raw file reference for web upload
}

interface TodayReport {
  id: string;
  status: 'SUBMITTED' | 'PENDING';
  sales_amount?: number;
  created_at?: string;
  uploaded_at?: string;
}

function getTodayDate(): string {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ManagerDashboardScreen() {
  const { user, logout } = useAuthStore();
  const uploadMutation = useUploadReport();

  const [pickedFile, setPickedFile] = useState<PickedFile | null>(null);
  const [todayReport, setTodayReport] = useState<TodayReport | null>(null);
  const [reportLoading, setReportLoading] = useState(true);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const headerOpacity = useRef(new Animated.Value(0)).current;
  const cardY         = useRef(new Animated.Value(30)).current;

  // Fetch today's report status on mount
  useEffect(() => {
    Animated.parallel([
      Animated.timing(headerOpacity, { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.timing(cardY, { toValue: 0, duration: 500, useNativeDriver: true }),
    ]).start();

    fetchTodayReport();
  }, []);

  const fetchTodayReport = async () => {
    setReportLoading(true);
    try {
      if (!user?.branch_id) {
        setTodayReport(null);
        return;
      }
      const today = getTodayDate();
      const res = await apiClient.get(`/reports/branch/${user.branch_id}`);
      const allReports: any[] = res.data || [];
      // Find today's report with robust date string matching
      const todaysEntry = allReports.find((r: any) => {
        const rawDate = r.date || r.report_date;
        if (!rawDate) return false;
        const rDateStr = String(rawDate).split('T')[0];
        return rDateStr === today;
      });
      setTodayReport(todaysEntry || null);
    } catch (_) {
      setTodayReport(null);
    } finally {
      setReportLoading(false);
    }
  };

  const handlePickFile = useCallback(async () => {
    if (Platform.OS === 'web') {
      // Web: use hidden <input type="file">
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.xlsx,.xls,.csv';
      input.onchange = (e: any) => {
        const file: File = e.target.files[0];
        if (file) {
          const uri = URL.createObjectURL(file);
          setPickedFile({ uri, name: file.name, type: file.type, size: file.size, rawFile: file });
        }
      };
      input.click();
      return;
    }

    if (!DocumentPicker) {
      Alert.alert('Not supported', 'File picking is not available on this platform.');
      return;
    }

    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'application/vnd.ms-excel',
          'text/csv',
          '*/*',
        ],
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const asset = result.assets[0];
        setPickedFile({
          uri: asset.uri,
          name: asset.name,
          type: asset.mimeType || 'application/octet-stream',
          size: asset.size,
        });
      }
    } catch (err) {
      console.error('Document pick error:', err);
    }
  }, []);

  const isSubmitted = Boolean(
    todayReport && 
    (todayReport.status?.toUpperCase() === 'SUBMITTED' || !todayReport.status)
  );

  const executeUpload = useCallback(() => {
    if (!pickedFile) return;
    if (uploadMutation.isPending) return;

    setUploadSuccess(false);

    const filePayload = Platform.OS === 'web' && pickedFile.rawFile
      ? pickedFile.rawFile
      : { uri: pickedFile.uri, name: pickedFile.name, type: pickedFile.type };

    uploadMutation.mutate(
      {
        report_date: getTodayDate(),
        file: filePayload,
      },
      {
        onSuccess: (data: any) => {
          setUploadSuccess(true);
          setPickedFile(null);
          if (data) {
            setTodayReport(data);
          }
          fetchTodayReport(); // refresh status
        },
        onError: (err: any) => {
          const msg = err?.response?.data?.detail || 'Upload failed. Please try again.';
          Alert.alert('Upload Failed', msg);
        },
      }
    );
  }, [pickedFile, uploadMutation]);

  const handleUploadPress = useCallback(() => {
    if (!pickedFile) return;
    if (uploadMutation.isPending) return;

    if (isSubmitted) {
      setShowConfirmModal(true);
    } else {
      executeUpload();
    }
  }, [pickedFile, uploadMutation, isSubmitted, executeUpload]);

  const today = formatDate(new Date().toISOString());
  const branchName = user?.branch_name || 'Branch';
  
  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* ── Header ── */}
        <Animated.View style={[styles.header, { opacity: headerOpacity }]}>
          <View style={styles.headerTop}>
            <View>
              <Text style={styles.headerLabel}>Branch Manager Portal</Text>
              <Text style={styles.headerBrand}>POTHYS Swarna Mahal</Text>
            </View>
            <TouchableOpacity style={styles.logoutBtn} onPress={logout} activeOpacity={0.8}>
              <Text style={styles.logoutBtnText}>Sign Out</Text>
            </TouchableOpacity>
          </View>

          {/* Accent divider */}
          <View style={styles.headerDivider} />

          {/* Welcome */}
          <Text style={styles.welcomeGreeting}>Good {getTimeGreeting()}</Text>
          <Text style={styles.welcomeName}>{user?.full_name || 'Manager'}</Text>
          <Text style={styles.welcomeDate}>{today}</Text>
        </Animated.View>

        {/* Success message banner */}
        {uploadSuccess && (
          <View style={styles.successBanner}>
            <Text style={styles.successBannerText}>
              {isSubmitted ? "🔄 Report replaced and updated successfully." : "✅ Daily report uploaded successfully."}
            </Text>
          </View>
        )}

        {/* ── Status Card ── */}
        <Animated.View style={[styles.statusCard, { transform: [{ translateY: cardY }] }]}>
          <View style={[styles.statusAccentBar, isSubmitted && styles.statusAccentBarSubmitted]} />
          <View style={styles.statusCardBody}>
            <View style={styles.statusRow}>
              <View style={styles.statusInfo}>
                <Text style={styles.statusCardLabel}>Today's Report Status</Text>
                {reportLoading ? (
                  <ActivityIndicator color={COLORS.accent} size="small" style={{ marginTop: 8 }} />
                ) : (
                  <>
                    <View style={[styles.statusPill, isSubmitted ? styles.statusPillSubmitted : styles.statusPillPending]}>
                      <View style={[styles.statusDot, isSubmitted ? styles.statusDotSubmitted : styles.statusDotPending]} />
                      <Text style={[styles.statusPillText, isSubmitted ? styles.statusPillTextSubmitted : styles.statusPillTextPending]}>
                        {isSubmitted ? 'Submitted' : 'Pending'}
                      </Text>
                    </View>
                    {isSubmitted && (todayReport?.uploaded_at || todayReport?.created_at) && (
                      <Text style={styles.statusSubmittedAt}>
                        Submitted at {new Date(todayReport.uploaded_at || todayReport.created_at!).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                      </Text>
                    )}
                  </>
                )}
              </View>
              <Text style={styles.statusEmoji}>{isSubmitted ? '✅' : '⏳'}</Text>
            </View>

            {/* Branch Info */}
            <View style={styles.branchRow}>
              <View style={styles.branchChip}>
                <Text style={styles.branchChipLabel}>BRANCH</Text>
                <Text style={styles.branchChipValue}>{branchName}</Text>
              </View>
              <View style={styles.branchChip}>
                <Text style={styles.branchChipLabel}>DATE</Text>
                <Text style={styles.branchChipValue}>{getTodayDate()}</Text>
              </View>
            </View>
          </View>
        </Animated.View>

        {/* ── Upload / Replace Section (Always accessible) ── */}
        <Animated.View style={{ transform: [{ translateY: cardY }] }}>
          <View style={styles.uploadCard}>
            <View style={styles.uploadCardHeader}>
              <Text style={styles.uploadCardTitle}>
                {isSubmitted ? "Replace Today's Report" : "Upload Daily Report"}
              </Text>
              <Text style={styles.uploadCardSub}>
                {isSubmitted
                  ? `Correct or update your branch's operational report for ${getTodayDate()}`
                  : `Submit your branch's Excel operational report for ${getTodayDate()}`}
              </Text>
            </View>

            {/* File picker area */}
            <TouchableOpacity
              style={[styles.filePicker, pickedFile && styles.filePickerSelected]}
              onPress={handlePickFile}
              activeOpacity={0.8}
              disabled={uploadMutation.isPending}
            >
              {pickedFile ? (
                <View style={styles.filePickedContent}>
                  <Text style={styles.filePickedIcon}>📄</Text>
                  <View style={styles.filePickedInfo}>
                    <Text style={styles.filePickedName} numberOfLines={1}>{pickedFile.name}</Text>
                    {pickedFile.size && (
                      <Text style={styles.filePickedSize}>{formatFileSize(pickedFile.size)}</Text>
                    )}
                  </View>
                  <TouchableOpacity
                    style={styles.fileRemoveBtn}
                    onPress={() => setPickedFile(null)}
                  >
                    <Text style={styles.fileRemoveBtnText}>✕</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <View style={styles.fileEmptyContent}>
                  <Text style={styles.fileEmptyIcon}>📁</Text>
                  <Text style={styles.fileEmptyTitle}>Choose Excel File</Text>
                  <Text style={styles.fileEmptyHint}>Tap to browse · .xlsx, .xls, .csv supported</Text>
                </View>
              )}
            </TouchableOpacity>

            {/* Upload / Replace button */}
            <TouchableOpacity
              style={[
                styles.uploadBtn,
                isSubmitted && { backgroundColor: COLORS.primary },
                (!pickedFile || uploadMutation.isPending) && styles.uploadBtnDisabled,
              ]}
              onPress={handleUploadPress}
              disabled={!pickedFile || uploadMutation.isPending}
              activeOpacity={0.85}
            >
              {uploadMutation.isPending ? (
                <View style={styles.uploadBtnInner}>
                  <ActivityIndicator color="#fff" size="small" />
                  <Text style={styles.uploadBtnText}>
                    {isSubmitted ? "Replacing Report..." : "Uploading..."}
                  </Text>
                </View>
              ) : (
                <View style={styles.uploadBtnInner}>
                  <Text style={styles.uploadBtnIcon}>{isSubmitted ? "🔄" : "↑"}</Text>
                  <Text style={[styles.uploadBtnText, isSubmitted && { color: '#000' }]}>
                    {isSubmitted ? "Replace Today's Report" : "Upload Report"}
                  </Text>
                </View>
              )}
            </TouchableOpacity>

            {/* Error from mutation */}
            {uploadMutation.isError && (
              <View style={styles.uploadError}>
                <Text style={styles.uploadErrorText}>
                  ⚠️ {(uploadMutation.error as any)?.response?.data?.detail || 'Upload failed. Please try again.'}
                </Text>
              </View>
            )}
          </View>

          {/* Guidelines */}
          <View style={styles.guidelinesCard}>
            <Text style={styles.guidelinesTitle}>📋  Submission & Correction Guidelines</Text>
            <Text style={styles.guidelineItem}>• Upload the official Pothys daily operations Excel template only.</Text>
            <Text style={styles.guidelineItem}>• Ensure all mandatory fields (sales, attendance, target) are filled.</Text>
            <Text style={styles.guidelineItem}>• Re-uploading for today will safely replace current metrics without creating duplicate entries.</Text>
            <Text style={styles.guidelineItem}>• Historical reports from previous dates remain locked and untouched.</Text>
          </View>
        </Animated.View>

        {/* Bottom padding */}
        <View style={{ height: 40 }} />
      </ScrollView>

      {/* Confirmation Dialog Modal for Report Replacement */}
      <Modal
        visible={showConfirmModal}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setShowConfirmModal(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowConfirmModal(false)}
        >
          <View style={styles.modalCard} onStartShouldSetResponder={() => true}>
            <Text style={styles.modalTitle}>Replace Existing Report?</Text>
            <Text style={styles.modalMessage}>
              A report already exists for this date. Uploading a new report will replace the existing report and update all analytics.
            </Text>
            <View style={styles.modalButtonRow}>
              <TouchableOpacity
                style={styles.modalCancelBtn}
                onPress={() => setShowConfirmModal(false)}
                activeOpacity={0.8}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalConfirmBtn}
                onPress={() => {
                  setShowConfirmModal(false);
                  executeUpload();
                }}
                activeOpacity={0.85}
              >
                <Text style={styles.modalConfirmText}>Replace Report</Text>
              </TouchableOpacity>
            </View>
          </View>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
}

function getTimeGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Morning';
  if (h < 17) return 'Afternoon';
  return 'Evening';
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  scroll: { paddingHorizontal: 20, paddingTop: 8 },

  // Header
  header: { marginBottom: 20, paddingTop: 8 },
  headerTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  headerLabel: { fontSize: 11, fontWeight: '700', color: COLORS.textMuted, letterSpacing: 2, textTransform: 'uppercase', marginBottom: 2 },
  headerBrand: { fontSize: 20, fontWeight: '900', color: COLORS.primary, letterSpacing: 2 },
  headerDivider: { height: 1, backgroundColor: COLORS.border, marginBottom: 20 },
  welcomeGreeting: { fontSize: 14, color: COLORS.textSecondary, marginBottom: 2 },
  welcomeName: { fontSize: 28, fontWeight: '800', color: COLORS.text, marginBottom: 4 },
  welcomeDate: { fontSize: 13, color: COLORS.textSecondary },
  logoutBtn: {
    borderWidth: 1, borderColor: COLORS.border,
    paddingHorizontal: 14, paddingVertical: 7, borderRadius: 8,
  },
  logoutBtnText: { fontSize: 13, color: COLORS.textSecondary, fontWeight: '600' },

  // Status card
  statusCard: {
    backgroundColor: COLORS.surface, borderRadius: 18, borderWidth: 1,
    borderColor: COLORS.border, marginBottom: 16,
    overflow: 'hidden',
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25, shadowRadius: 10, elevation: 8,
  },
  statusAccentBar: { height: 3, backgroundColor: COLORS.warning },
  statusAccentBarSubmitted: { backgroundColor: COLORS.success },
  statusCardBody: { padding: 20 },
  statusRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  statusInfo: { flex: 1 },
  statusCardLabel: { fontSize: 11, fontWeight: '700', color: COLORS.textMuted, letterSpacing: 2, textTransform: 'uppercase', marginBottom: 10 },
  statusPill: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    paddingHorizontal: 12, paddingVertical: 6,
    borderRadius: 20, borderWidth: 1, alignSelf: 'flex-start',
  },
  statusPillPending: { backgroundColor: COLORS.warningBg, borderColor: COLORS.warning + '60' },
  statusPillSubmitted: { backgroundColor: COLORS.successBg, borderColor: COLORS.success + '60' },
  statusDot: { width: 7, height: 7, borderRadius: 3.5 },
  statusDotPending: { backgroundColor: COLORS.warning },
  statusDotSubmitted: { backgroundColor: COLORS.success },
  statusPillText: { fontSize: 13, fontWeight: '700' },
  statusPillTextPending: { color: COLORS.warning },
  statusPillTextSubmitted: { color: COLORS.success },
  statusSubmittedAt: { fontSize: 12, color: COLORS.textMuted, marginTop: 6 },
  statusEmoji: { fontSize: 36, marginLeft: 8 },
  branchRow: { flexDirection: 'row', gap: 10 },
  branchChip: {
    flex: 1, backgroundColor: COLORS.surfaceAlt, borderRadius: 10,
    borderWidth: 1, borderColor: COLORS.border, padding: 12,
  },
  branchChipLabel: { fontSize: 10, fontWeight: '700', color: COLORS.textMuted, letterSpacing: 2, textTransform: 'uppercase', marginBottom: 4 },
  branchChipValue: { fontSize: 13, fontWeight: '700', color: COLORS.text },

  // Upload card
  uploadCard: {
    backgroundColor: COLORS.surface, borderRadius: 18, borderWidth: 1,
    borderColor: COLORS.border, padding: 20, marginBottom: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2, shadowRadius: 10, elevation: 6,
  },
  uploadCardHeader: { marginBottom: 18 },
  uploadCardTitle: { fontSize: 18, fontWeight: '800', color: COLORS.text, marginBottom: 4 },
  uploadCardSub: { fontSize: 13, color: COLORS.textSecondary, lineHeight: 18 },

  // File picker
  filePicker: {
    borderWidth: 2, borderStyle: 'dashed', borderColor: COLORS.border,
    borderRadius: 14, padding: 28, alignItems: 'center', marginBottom: 16,
    backgroundColor: COLORS.surfaceAlt,
  },
  filePickerSelected: { borderColor: COLORS.accent + '80', borderStyle: 'solid', backgroundColor: COLORS.accent + '08' },
  fileEmptyContent: { alignItems: 'center', gap: 8 },
  fileEmptyIcon: { fontSize: 40, marginBottom: 4 },
  fileEmptyTitle: { fontSize: 16, fontWeight: '700', color: COLORS.text },
  fileEmptyHint: { fontSize: 12, color: COLORS.textMuted },
  filePickedContent: { flexDirection: 'row', alignItems: 'center', gap: 12, width: '100%' },
  filePickedIcon: { fontSize: 32, flexShrink: 0 },
  filePickedInfo: { flex: 1 },
  filePickedName: { fontSize: 14, fontWeight: '700', color: COLORS.text },
  filePickedSize: { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  fileRemoveBtn: {
    width: 28, height: 28, borderRadius: 14,
    backgroundColor: COLORS.error + '20', borderWidth: 1, borderColor: COLORS.error + '40',
    alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  fileRemoveBtnText: { fontSize: 12, color: COLORS.error, fontWeight: '700' },

  // Upload button
  uploadBtn: {
    backgroundColor: COLORS.accent, borderRadius: 12,
    paddingVertical: 16, alignItems: 'center',
  },
  uploadBtnDisabled: { opacity: 0.4 },
  uploadBtnInner: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  uploadBtnIcon: { fontSize: 18, color: '#fff', fontWeight: '800' },
  uploadBtnText: { fontSize: 16, fontWeight: '700', color: '#fff' },

  uploadError: {
    backgroundColor: COLORS.errorBg, borderWidth: 1, borderColor: COLORS.error,
    borderRadius: 8, padding: 12, marginTop: 12,
  },
  uploadErrorText: { color: COLORS.error, fontSize: 13, textAlign: 'center', fontWeight: '500' },

  // Guidelines
  guidelinesCard: {
    backgroundColor: COLORS.surfaceAlt, borderRadius: 14, borderWidth: 1,
    borderColor: COLORS.border, padding: 16, marginBottom: 16,
  },
  guidelinesTitle: { fontSize: 13, fontWeight: '700', color: COLORS.textSecondary, marginBottom: 12 },
  guidelineItem: { fontSize: 12, color: COLORS.textMuted, lineHeight: 20 },

  // Submitted banner
  submittedBanner: {
    backgroundColor: COLORS.successBg, borderWidth: 1, borderColor: COLORS.success + '50',
    borderRadius: 18, padding: 28, alignItems: 'center', marginBottom: 16,
  },
  submittedBannerIcon: { fontSize: 48, marginBottom: 12 },
  submittedBannerTitle: { fontSize: 22, fontWeight: '800', color: COLORS.success, marginBottom: 8 },
  submittedBannerSub: { fontSize: 14, color: COLORS.textSecondary, textAlign: 'center', lineHeight: 22 },
  
  // Success banner
  successBanner: {
    backgroundColor: COLORS.successBg,
    borderColor: COLORS.success,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  successBannerText: {
    color: COLORS.success,
    fontSize: 15,
    fontWeight: '700',
    textAlign: 'center',
  },

  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalCard: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: COLORS.surface,
    borderColor: COLORS.border,
    borderWidth: 1,
    borderRadius: 20,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.4,
    shadowRadius: 20,
    elevation: 10,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: COLORS.text,
    marginBottom: 10,
  },
  modalMessage: {
    fontSize: 14,
    color: COLORS.textSecondary,
    lineHeight: 20,
    marginBottom: 24,
  },
  modalButtonRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
  },
  modalCancelBtn: {
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: COLORS.border,
    backgroundColor: COLORS.surfaceAlt,
  },
  modalCancelText: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
  },
  modalConfirmBtn: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
  },
  modalConfirmText: {
    fontSize: 14,
    fontWeight: '800',
    color: '#000',
  },
});
