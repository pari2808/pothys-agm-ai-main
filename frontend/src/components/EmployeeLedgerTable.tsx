import React from 'react';
import {
  StyleSheet,
  View,
  Text,
  ScrollView,
} from 'react-native';
import { useThemeStore } from '../store/themeStore';
import { formatIndianCurrency } from '../utils/currencyFormatter';
import { formatGrams, formatCarats, formatSilverMRP } from '../utils/unitFormatter';

export interface EmployeeRecord {
  employee_name?: string;
  name?: string;
  department?: string;
  designation?: string;
  sales?: number;
  gold?: number;
  gold_amount?: number;
  gold_grams?: number;
  gold_grams_sold?: number;
  silver?: number;
  silver_amount?: number;
  silver_grams?: number;
  silver_grams_sold?: number;
  platinum?: number;
  platinum_amount?: number;
  platinum_grams?: number;
  diamond?: number;
  diamond_amount?: number;
  diamond_grams?: number;
  silver_mrp?: number;
  digigold?: number;
  digigold_enrollments?: number;
  digisilver?: number;
  digisilver_enrollments?: number;
}

interface EmployeeLedgerTableProps {
  employees: EmployeeRecord[];
}

export default function EmployeeLedgerTable({ employees }: EmployeeLedgerTableProps) {
  const { colors } = useThemeStore();

  if (!employees || employees.length === 0) {
    return (
      <View style={[styles.emptyContainer, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
          No employee performance data available for this branch.
        </Text>
      </View>
    );
  }

  // Calculate Column Totals according to official production template metrics
  const totalGoldGrams = employees.reduce((sum, emp) => sum + (emp.gold ?? emp.gold_grams ?? emp.gold_grams_sold ?? 0), 0);
  const totalSilverGrams = employees.reduce((sum, emp) => sum + (emp.silver ?? emp.silver_grams ?? emp.silver_grams_sold ?? 0), 0);
  const totalSilverMRP = employees.reduce((sum, emp) => sum + (emp.silver_mrp ?? emp.silver_amount ?? 0), 0);
  const totalDiamondGrams = employees.reduce((sum, emp) => sum + (emp.diamond ?? emp.diamond_grams ?? emp.diamond_amount ?? 0), 0);
  const totalPlatinumGrams = employees.reduce((sum, emp) => sum + (emp.platinum ?? emp.platinum_grams ?? emp.platinum_amount ?? 0), 0);
  const totalDigiGold = employees.reduce((sum, emp) => sum + (emp.digigold ?? emp.digigold_enrollments ?? 0), 0);
  const totalDigiSilver = employees.reduce((sum, emp) => sum + (emp.digisilver ?? emp.digisilver_enrollments ?? 0), 0);

  const dividerStyle = { borderColor: colors.border + '35' };

  return (
    <View style={[styles.container, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      {/* Header Info Banner */}
      <View style={[styles.headerBanner, { borderBottomColor: colors.border }]}>
        <View style={styles.headerTitleContainer}>
          <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
            EMPLOYEE PERFORMANCE LEDGER
          </Text>
          <Text style={[styles.subTitle, { color: colors.textMuted }]}>
            Enterprise detailed records ({employees.length} Staff Members)
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
            <View style={[styles.headerCell, styles.colName, styles.borderRight, dividerStyle]}>
              <Text style={[styles.headerCellText, { color: colors.textSecondary }]}>Employee Name</Text>
            </View>
            <View style={[styles.headerCell, styles.colGold, styles.borderRight, dividerStyle]}>
              <Text style={[styles.headerCellText, styles.textRight, { color: colors.textSecondary }]}>Gold</Text>
            </View>
            <View style={[styles.headerCell, styles.colSilver, styles.borderRight, dividerStyle]}>
              <Text style={[styles.headerCellText, styles.textRight, { color: colors.textSecondary }]}>Silver</Text>
            </View>
            <View style={[styles.headerCell, styles.colSilverMRP, styles.borderRight, dividerStyle]}>
              <Text style={[styles.headerCellText, styles.textRight, { color: colors.textSecondary }]}>Silver MRP</Text>
            </View>
            <View style={[styles.headerCell, styles.colDiamond, styles.borderRight, dividerStyle]}>
              <Text style={[styles.headerCellText, styles.textRight, { color: colors.textSecondary }]}>Diamond</Text>
            </View>
            <View style={[styles.headerCell, styles.colPlatinum, styles.borderRight, dividerStyle]}>
              <Text style={[styles.headerCellText, styles.textRight, { color: colors.textSecondary }]}>Platinum</Text>
            </View>
            <View style={[styles.headerCell, styles.colDigiGold, styles.borderRight, dividerStyle]}>
              <Text style={[styles.headerCellText, styles.textRight, { color: colors.primary }]}>DigiGold</Text>
            </View>
            <View style={[styles.headerCell, styles.colDigiSilver]}>
              <Text style={[styles.headerCellText, styles.textRight, { color: colors.textSecondary }]}>DigiSilver</Text>
            </View>
          </View>

          {/* Table Data Rows inside Vertical Scroll Container */}
          <View style={styles.tableBodyContainer}>
            <ScrollView style={styles.verticalScrollView} nestedScrollEnabled={true} showsVerticalScrollIndicator={true}>
              {employees.map((emp, index) => {
                const empName = emp.employee_name || emp.name || 'Staff Member';
                const goldGrams = emp.gold ?? emp.gold_grams ?? emp.gold_grams_sold ?? 0;
                const silverGrams = emp.silver ?? emp.silver_grams ?? emp.silver_grams_sold ?? 0;
                const silverMrp = emp.silver_mrp ?? emp.silver_amount ?? 0;
                const diamondGrams = emp.diamond ?? emp.diamond_grams ?? emp.diamond_amount ?? 0;
                const platinumGrams = emp.platinum ?? emp.platinum_grams ?? emp.platinum_amount ?? 0;
                const digiGold = emp.digigold ?? emp.digigold_enrollments ?? 0;
                const digiSilver = emp.digisilver ?? emp.digisilver_enrollments ?? 0;

                const isEven = index % 2 === 0;
                return (
                  <View
                    key={index}
                    style={[
                      styles.dataRow,
                      {
                        backgroundColor: isEven ? colors.surface : colors.surfaceAlt + '80',
                        borderBottomColor: colors.border + '50',
                      },
                    ]}
                  >
                    <View style={[styles.cell, styles.colName, styles.borderRight, dividerStyle]}>
                      <Text style={[styles.cellText, styles.boldText, { color: colors.text }]} numberOfLines={1}>
                        {empName}
                      </Text>
                    </View>
                    <View style={[styles.cell, styles.colGold, styles.borderRight, dividerStyle]}>
                      <Text style={[styles.cellText, styles.textRight, { color: colors.textSecondary }]}>
                        {formatGrams(goldGrams)}
                      </Text>
                    </View>
                    <View style={[styles.cell, styles.colSilver, styles.borderRight, dividerStyle]}>
                      <Text style={[styles.cellText, styles.textRight, { color: colors.textSecondary }]}>
                        {formatGrams(silverGrams)}
                      </Text>
                    </View>
                    <View style={[styles.cell, styles.colSilverMRP, styles.borderRight, dividerStyle]}>
                      <Text style={[styles.cellText, styles.textRight, { color: colors.text }]}>
                        {formatSilverMRP(silverMrp)}
                      </Text>
                    </View>
                    <View style={[styles.cell, styles.colDiamond, styles.borderRight, dividerStyle]}>
                      <Text style={[styles.cellText, styles.textRight, { color: colors.textSecondary }]}>
                        {formatCarats(diamondGrams)}
                      </Text>
                    </View>
                    <View style={[styles.cell, styles.colPlatinum, styles.borderRight, dividerStyle]}>
                      <Text style={[styles.cellText, styles.textRight, { color: colors.textSecondary }]}>
                        {formatGrams(platinumGrams)}
                      </Text>
                    </View>
                    <View style={[styles.cell, styles.colDigiGold, styles.borderRight, dividerStyle]}>
                      <Text style={[styles.cellText, styles.textRight, styles.boldText, { color: colors.primary }]}>
                        {digiGold}
                      </Text>
                    </View>
                    <View style={[styles.cell, styles.colDigiSilver]}>
                      <Text style={[styles.cellText, styles.textRight, styles.boldText, { color: colors.textSecondary }]}>
                        {digiSilver}
                      </Text>
                    </View>
                  </View>
                );
              })}
            </ScrollView>
          </View>

          {/* Table Summary Total Row */}
          <View style={[styles.tableTotalRow, { backgroundColor: colors.surfaceAlt, borderTopColor: colors.border }]}>
            <View style={[styles.totalCell, styles.colName, styles.borderRight, dividerStyle]}>
              <Text style={[styles.totalCellText, { color: colors.text }]}>Total ({employees.length})</Text>
            </View>
            <View style={[styles.totalCell, styles.colGold, styles.borderRight, dividerStyle]}>
              <Text style={[styles.totalCellText, styles.textRight, { color: colors.textSecondary }]}>
                {formatGrams(totalGoldGrams)}
              </Text>
            </View>
            <View style={[styles.totalCell, styles.colSilver, styles.borderRight, dividerStyle]}>
              <Text style={[styles.totalCellText, styles.textRight, { color: colors.textSecondary }]}>
                {formatGrams(totalSilverGrams)}
              </Text>
            </View>
            <View style={[styles.totalCell, styles.colSilverMRP, styles.borderRight, dividerStyle]}>
              <Text style={[styles.totalCellText, styles.textRight, { color: colors.text }]}>
                {formatSilverMRP(totalSilverMRP)}
              </Text>
            </View>
            <View style={[styles.totalCell, styles.colDiamond, styles.borderRight, dividerStyle]}>
              <Text style={[styles.totalCellText, styles.textRight, { color: colors.textSecondary }]}>
                {formatCarats(totalDiamondGrams)}
              </Text>
            </View>
            <View style={[styles.totalCell, styles.colPlatinum, styles.borderRight, dividerStyle]}>
              <Text style={[styles.totalCellText, styles.textRight, { color: colors.textSecondary }]}>
                {formatGrams(totalPlatinumGrams)}
              </Text>
            </View>
            <View style={[styles.totalCell, styles.colDigiGold, styles.borderRight, dividerStyle]}>
              <Text style={[styles.totalCellText, styles.textRight, { color: colors.primary }]}>
                {totalDigiGold}
              </Text>
            </View>
            <View style={[styles.totalCell, styles.colDigiSilver]}>
              <Text style={[styles.totalCellText, styles.textRight, { color: colors.textSecondary }]}>
                {totalDigiSilver}
              </Text>
            </View>
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
  horizontalScrollContent: {
    paddingBottom: 4,
  },
  tableWidthContainer: {
    width: 725,
  },
  tableHeaderRow: {
    flexDirection: 'row',
    borderBottomWidth: 1.5,
    alignItems: 'center',
  },
  headerCell: {
    paddingHorizontal: 8,
    paddingVertical: 10,
    justifyContent: 'center',
  },
  headerCellText: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  tableBodyContainer: {
    maxHeight: 380,
  },
  verticalScrollView: {
    flexGrow: 0,
  },
  dataRow: {
    flexDirection: 'row',
    borderBottomWidth: 0.5,
    alignItems: 'center',
  },
  cell: {
    paddingHorizontal: 8,
    paddingVertical: 10,
    justifyContent: 'center',
  },
  cellText: {
    fontSize: 12,
  },
  boldText: {
    fontWeight: '700',
  },
  textRight: {
    textAlign: 'right',
  },
  tableTotalRow: {
    flexDirection: 'row',
    borderTopWidth: 1.5,
    alignItems: 'center',
  },
  totalCell: {
    paddingHorizontal: 8,
    paddingVertical: 10,
    justifyContent: 'center',
  },
  totalCellText: {
    fontSize: 12,
    fontWeight: '800',
  },
  borderRight: {
    borderRightWidth: 1,
  },
  colName: {
    width: 150,
  },
  colGold: {
    width: 75,
  },
  colSilver: {
    width: 75,
  },
  colSilverMRP: {
    width: 105,
  },
  colDiamond: {
    width: 80,
  },
  colPlatinum: {
    width: 80,
  },
  colDigiGold: {
    width: 80,
  },
  colDigiSilver: {
    width: 80,
  },
});
