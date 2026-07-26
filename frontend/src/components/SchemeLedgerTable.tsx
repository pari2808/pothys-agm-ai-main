import React from 'react';
import {
  StyleSheet,
  View,
  Text,
  ScrollView,
} from 'react-native';
import { useThemeStore } from '../store/themeStore';
import { formatFullIndianCurrency } from '../utils/currencyFormatter';

export interface SchemeRecord {
  scheme_name?: string;
  scheme?: string;
  name?: string;
  enrollments?: number;
  todays_enrollments?: number;
  count?: number;
  revenue?: number;
  amount?: number;
}

interface SchemeLedgerTableProps {
  schemes: SchemeRecord[];
}

export default function SchemeLedgerTable({ schemes }: SchemeLedgerTableProps) {
  const { colors } = useThemeStore();

  const validSchemes = (schemes || []).filter(s => {
    const sName = (s.scheme_name || s.scheme || s.name || '').trim();
    return sName.length > 0;
  });

  if (!validSchemes || validSchemes.length === 0) {
    return (
      <View style={[styles.emptyContainer, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
          No digital scheme performance records available for this branch.
        </Text>
      </View>
    );
  }

  // Calculate Totals
  const totalEnrollments = validSchemes.reduce((sum, s) => {
    const count = s.enrollments ?? s.todays_enrollments ?? s.count ?? 0;
    return sum + count;
  }, 0);

  const totalRevenue = validSchemes.reduce((sum, s) => {
    const rev = s.revenue ?? s.amount ?? 0;
    return sum + rev;
  }, 0);

  return (
    <View style={[styles.container, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      {/* Header Info Banner */}
      <View style={[styles.headerBanner, { borderBottomColor: colors.border }]}>
        <View style={styles.headerTitleContainer}>
          <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
            DIGITAL SCHEMES LEDGER
          </Text>
          <Text style={[styles.subTitle, { color: colors.textMuted }]}>
            Enterprise performance records ({validSchemes.length} Active Schemes)
          </Text>
        </View>
        <View style={[styles.totalBadge, { backgroundColor: colors.primary + '1A', borderColor: colors.primary + '40' }]}>
          <Text style={[styles.totalBadgeText, { color: colors.primary }]}>
            {formatFullIndianCurrency(totalRevenue)}
          </Text>
        </View>
      </View>

      {/* Main Table View with Horizontal & Vertical Scroll Capability */}
      <ScrollView
        horizontal={true}
        showsHorizontalScrollIndicator={true}
        contentContainerStyle={styles.horizontalScrollContent}
      >
        <View style={styles.tableWidthContainer}>
          {/* Sticky Table Header Row */}
          <View style={[styles.tableHeaderRow, { backgroundColor: colors.surfaceAlt, borderBottomColor: colors.border }]}>
            <Text style={[styles.headerCell, styles.colScheme, { color: colors.textSecondary }]}>Scheme</Text>
            <Text style={[styles.headerCell, styles.colEnrollments, styles.textRight, { color: colors.primary }]}>Today's Enrollments</Text>
            <Text style={[styles.headerCell, styles.colRevenue, styles.textRight, { color: colors.textSecondary }]}>Revenue</Text>
          </View>

          {/* Table Data Rows inside Vertical Scroll Container */}
          <View style={styles.tableBodyContainer}>
            <ScrollView style={styles.verticalScrollView} nestedScrollEnabled={true} showsVerticalScrollIndicator={true}>
              {validSchemes.map((item, index) => {
                const schemeName = item.scheme_name || item.scheme || item.name || 'Scheme';
                const enrollments = item.enrollments ?? item.todays_enrollments ?? item.count ?? 0;
                const revenue = item.revenue ?? item.amount ?? 0;

                const isEven = index % 2 === 0;
                return (
                  <View
                    key={index}
                    style={[
                      styles.dataRow,
                      {
                        backgroundColor: isEven ? colors.surface : colors.surfaceAlt + '80',
                        borderBottomColor: colors.border + '60',
                      },
                    ]}
                  >
                    <Text style={[styles.cellText, styles.colScheme, styles.boldText, { color: colors.text }]} numberOfLines={1}>
                      {schemeName}
                    </Text>
                    <Text style={[styles.cellText, styles.colEnrollments, styles.textRight, styles.highlightText, { color: colors.primary }]}>
                      {enrollments}
                    </Text>
                    <Text style={[styles.cellText, styles.colRevenue, styles.textRight, styles.boldText, { color: colors.text }]}>
                      {formatFullIndianCurrency(revenue)}
                    </Text>
                  </View>
                );
              })}
            </ScrollView>
          </View>

          {/* Table Summary Total Row */}
          <View style={[styles.tableTotalRow, { backgroundColor: colors.surfaceAlt, borderTopColor: colors.border }]}>
            <Text style={[styles.totalCell, styles.colScheme, { color: colors.text }]}>Total ({validSchemes.length})</Text>
            <Text style={[styles.totalCell, styles.colEnrollments, styles.textRight, { color: colors.primary }]}>
              {totalEnrollments}
            </Text>
            <Text style={[styles.totalCell, styles.colRevenue, styles.textRight, { color: colors.primary }]}>
              {formatFullIndianCurrency(totalRevenue)}
            </Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 20,
    borderWidth: 1,
    marginBottom: 16,
    overflow: 'hidden',
  },
  emptyContainer: {
    borderRadius: 20,
    borderWidth: 1,
    padding: 24,
    marginBottom: 16,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
    textAlign: 'center',
  },
  headerBanner: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderBottomWidth: 1,
    gap: 8,
  },
  headerTitleContainer: {
    flex: 1,
    paddingRight: 6,
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  subTitle: {
    fontSize: 10,
    marginTop: 2,
  },
  totalBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 10,
    borderWidth: 1,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  totalBadgeText: {
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.2,
  },
  horizontalScrollContent: {
    paddingBottom: 4,
    flexGrow: 1,
  },
  tableWidthContainer: {
    minWidth: 480,
    width: '100%',
  },
  tableHeaderRow: {
    flexDirection: 'row',
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderBottomWidth: 1.5,
    alignItems: 'center',
  },
  headerCell: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  tableBodyContainer: {
    maxHeight: 280,
  },
  verticalScrollView: {
    flexGrow: 0,
  },
  dataRow: {
    flexDirection: 'row',
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderBottomWidth: 0.5,
    alignItems: 'center',
  },
  cellText: {
    fontSize: 13,
  },
  boldText: {
    fontWeight: '700',
  },
  highlightText: {
    fontWeight: '800',
  },
  textRight: {
    textAlign: 'right',
  },
  tableTotalRow: {
    flexDirection: 'row',
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderTopWidth: 1.5,
    alignItems: 'center',
  },
  totalCell: {
    fontSize: 13,
    fontWeight: '800',
  },
  colScheme: {
    flex: 2,
    minWidth: 160,
    paddingRight: 8,
  },
  colEnrollments: {
    flex: 1.5,
    minWidth: 150,
    paddingRight: 8,
  },
  colRevenue: {
    flex: 1.5,
    minWidth: 150,
    paddingRight: 8,
  },
});
