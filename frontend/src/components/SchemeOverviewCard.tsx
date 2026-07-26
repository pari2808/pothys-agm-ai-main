import React from 'react';
import { StyleSheet, View, Text, useWindowDimensions } from 'react-native';
import { useThemeStore } from '../store/themeStore';
import { formatIndianCurrency } from '../utils/currencyFormatter';

export interface SchemeSummaryItem {
  scheme_name?: string;
  scheme?: string;
  name?: string;
  enrollments?: number;
  count?: number;
  members?: number;
  revenue?: number;
  value?: number;
  amount?: number;
}

interface SchemeOverviewCardProps {
  schemeItems?: SchemeSummaryItem[];
  schemeSummary?: {
    scheme_items?: SchemeSummaryItem[];
    [key: string]: any;
  };
  reportData?: any;
}

interface SchemeCardData {
  title: string;
  count: string;
  value: string;
}

export default function SchemeOverviewCard({ schemeItems, schemeSummary, reportData }: SchemeOverviewCardProps) {
  const { colors } = useThemeStore();
  const { width: windowWidth } = useWindowDimensions();

  // Responsive threshold: stack vertically on very narrow screens, side-by-side otherwise
  const isNarrow = windowWidth < 360;

  const extractSchemeData = (targetSchemeName: string): { count: string; value: string } => {
    const searchName = targetSchemeName.toLowerCase();

    // 1. Look through schemeItems list
    const items = schemeItems || schemeSummary?.scheme_items || reportData?.scheme_items || [];
    const matchedItem = items.find((item: any) => {
      const sName = (item.scheme_name || item.scheme || item.name || '').toString().toLowerCase();
      return sName.includes(searchName);
    });

    if (matchedItem) {
      const rawCount = matchedItem.enrollments ?? matchedItem.count ?? matchedItem.members;
      const rawValue = matchedItem.revenue ?? matchedItem.value ?? matchedItem.amount ?? matchedItem.collection;

      const count = (rawCount !== undefined && rawCount !== null && String(rawCount).trim() !== '')
        ? String(rawCount)
        : '--';

      let value = '--';
      if (rawValue !== undefined && rawValue !== null && String(rawValue).trim() !== '') {
        value = typeof rawValue === 'number' ? formatIndianCurrency(rawValue) : String(rawValue);
      }

      return { count, value };
    }

    // 2. Fallback to direct keys on schemeSummary or reportData
    const ss = schemeSummary || {};
    const rep = reportData || {};

    const directCount = ss[`${searchName}_count`] ?? ss[`${searchName}_enrollments`] ?? rep[`${searchName}_count`] ?? rep[`${searchName}_enrollments`];
    const directValue = ss[`${searchName}_value`] ?? ss[`${searchName}_amount`] ?? ss[`${searchName}_revenue`] ?? rep[`${searchName}_value`] ?? rep[`${searchName}_amount`] ?? rep[`${searchName}_revenue`];

    const count = (directCount !== undefined && directCount !== null && String(directCount).trim() !== '') ? String(directCount) : '--';
    let value = '--';
    if (directValue !== undefined && directValue !== null && String(directValue).trim() !== '') {
      value = typeof directValue === 'number' ? formatIndianCurrency(directValue) : String(directValue);
    }

    return { count, value };
  };

  const subhiksham = extractSchemeData('subhiksham');
  const viruksham = extractSchemeData('viruksham');

  const schemes: SchemeCardData[] = [
    {
      title: 'SUBHIKSHAM',
      count: subhiksham.count,
      value: subhiksham.value,
    },
    {
      title: 'VIRUKSHAM',
      count: viruksham.count,
      value: viruksham.value,
    },
  ];

  return (
    <View style={[styles.container, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      {/* Card Header */}
      <View style={[styles.cardHeader, { borderBottomColor: colors.border }]}>
        <Text style={[styles.cardTitle, { color: colors.textSecondary }]}>SCHEME OVERVIEW</Text>
        <Text style={[styles.cardSubtitle, { color: colors.textMuted }]}>Branch scheme performance</Text>
      </View>

      {/* Side-by-side Scheme Cards */}
      <View style={[styles.cardsRow, isNarrow && styles.cardsColumn]}>
        {schemes.map((scheme, idx) => (
          <View
            key={idx}
            style={[
              styles.schemeCard,
              { backgroundColor: colors.surfaceAlt, borderColor: colors.border },
              isNarrow ? styles.schemeCardFullWidth : styles.schemeCardFlex,
              idx > 0 && !isNarrow && { marginLeft: 12 },
              idx > 0 && isNarrow && { marginTop: 12 },
            ]}
          >
            {/* Scheme Title */}
            <Text style={[styles.schemeTitle, { color: colors.primary }]}>{scheme.title}</Text>
            
            <View style={[styles.divider, { backgroundColor: colors.border + '60' }]} />

            {/* Metrics */}
            <View style={styles.metricsContainer}>
              {/* Count Metric */}
              <View style={styles.metricBlock}>
                <Text style={[styles.metricLabel, { color: colors.textMuted }]}>Count</Text>
                <Text style={[styles.metricValue, { color: colors.text }]}>{scheme.count}</Text>
              </View>

              <View style={[styles.verticalDivider, { backgroundColor: colors.border + '40' }]} />

              {/* Value Metric */}
              <View style={styles.metricBlock}>
                <Text style={[styles.metricLabel, { color: colors.textMuted }]}>Value</Text>
                <Text style={[styles.metricValue, { color: colors.text }]}>{scheme.value}</Text>
              </View>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 20,
    borderWidth: 1,
    padding: 16,
    marginBottom: 16,
  },
  cardHeader: {
    paddingBottom: 12,
    marginBottom: 14,
    borderBottomWidth: 1,
  },
  cardTitle: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  cardSubtitle: {
    fontSize: 11,
    marginTop: 2,
  },
  cardsRow: {
    flexDirection: 'row',
    alignItems: 'stretch',
  },
  cardsColumn: {
    flexDirection: 'column',
  },
  schemeCard: {
    borderRadius: 14,
    borderWidth: 1,
    paddingVertical: 14,
    paddingHorizontal: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  schemeCardFlex: {
    flex: 1,
  },
  schemeCardFullWidth: {
    width: '100%',
  },
  schemeTitle: {
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1,
    textAlign: 'center',
    marginBottom: 8,
  },
  divider: {
    height: 1,
    width: '100%',
    marginVertical: 8,
  },
  metricsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    width: '100%',
    paddingTop: 4,
  },
  metricBlock: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  metricLabel: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
    textAlign: 'center',
  },
  metricValue: {
    fontSize: 15,
    fontWeight: '800',
    textAlign: 'center',
  },
  verticalDivider: {
    width: 1,
    height: 28,
  },
});
