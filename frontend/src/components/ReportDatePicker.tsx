import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  StyleSheet,
  ScrollView,
  Platform,
} from 'react-native';
import { useThemeStore } from '../store/themeStore';

const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTHS_FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const WEEKDAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

interface ReportDatePickerProps {
  selectedDate: Date;
  onDateChange: (date: Date) => void;
}

function formatDisplayDate(date: Date): string {
  const day = date.getDate();
  const month = MONTHS_SHORT[date.getMonth()];
  const year = date.getFullYear();
  return `${day} ${month} ${year}`;
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}

export default function ReportDatePicker({ selectedDate, onDateChange }: ReportDatePickerProps) {
  const { colors } = useThemeStore();
  const [visible, setVisible] = useState(false);
  const [viewYear, setViewYear] = useState(selectedDate.getFullYear());
  const [viewMonth, setViewMonth] = useState(selectedDate.getMonth());
  const [showYearGrid, setShowYearGrid] = useState(false);

  const openPicker = () => {
    setViewYear(selectedDate.getFullYear());
    setViewMonth(selectedDate.getMonth());
    setShowYearGrid(false);
    setVisible(true);
  };

  const handleDateSelect = (day: number) => {
    const newDate = new Date(viewYear, viewMonth, day);
    onDateChange(newDate);
    setVisible(false);
  };

  const prevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear(viewYear - 1);
    } else {
      setViewMonth(viewMonth - 1);
    }
  };

  const nextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear(viewYear + 1);
    } else {
      setViewMonth(viewMonth + 1);
    }
  };

  const daysInMonth = getDaysInMonth(viewYear, viewMonth);
  const firstDay = getFirstDayOfMonth(viewYear, viewMonth);

  // Build calendar grid
  const calendarDays: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) calendarDays.push(null);
  for (let d = 1; d <= daysInMonth; d++) calendarDays.push(d);
  while (calendarDays.length % 7 !== 0) calendarDays.push(null);

  const isSelected = (day: number) => {
    return (
      day === selectedDate.getDate() &&
      viewMonth === selectedDate.getMonth() &&
      viewYear === selectedDate.getFullYear()
    );
  };

  const isToday = (day: number) => {
    const today = new Date();
    return (
      day === today.getDate() &&
      viewMonth === today.getMonth() &&
      viewYear === today.getFullYear()
    );
  };

  // Generate year list (from current year back to 2020, and forward 1 year)
  const currentYear = new Date().getFullYear();
  const years: number[] = [];
  for (let y = currentYear + 1; y >= 2020; y--) years.push(y);

  return (
    <>
      {/* Compact Date Button */}
      <TouchableOpacity
        style={[
          styles.dateButton,
          {
            backgroundColor: colors.surfaceAlt,
            borderColor: colors.border,
          },
        ]}
        onPress={openPicker}
        activeOpacity={0.7}
      >
        <Text style={styles.dateIcon}>📅</Text>
        <Text style={[styles.dateText, { color: colors.text }]}>
          {formatDisplayDate(selectedDate)}
        </Text>
      </TouchableOpacity>

      {/* Calendar Modal */}
      <Modal
        visible={visible}
        transparent
        animationType="fade"
        onRequestClose={() => setVisible(false)}
      >
        <TouchableOpacity
          style={styles.overlay}
          activeOpacity={1}
          onPress={() => setVisible(false)}
        >
          <View
            style={[
              styles.calendarContainer,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}
            onStartShouldSetResponder={() => true}
          >
            {/* Month/Year Header with Navigation */}
            <View style={styles.calendarHeader}>
              <TouchableOpacity
                onPress={prevMonth}
                style={styles.navButton}
                activeOpacity={0.6}
              >
                <Text style={[styles.navText, { color: colors.primary }]}>‹</Text>
              </TouchableOpacity>

              <TouchableOpacity
                onPress={() => setShowYearGrid(!showYearGrid)}
                activeOpacity={0.7}
                style={styles.monthYearButton}
              >
                <Text style={[styles.monthYearText, { color: colors.text }]}>
                  {MONTHS_FULL[viewMonth]} {viewYear}
                </Text>
                <Text style={[styles.dropdownArrow, { color: colors.textMuted }]}>
                  {showYearGrid ? '▲' : '▼'}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                onPress={nextMonth}
                style={styles.navButton}
                activeOpacity={0.6}
              >
                <Text style={[styles.navText, { color: colors.primary }]}>›</Text>
              </TouchableOpacity>
            </View>

            {showYearGrid ? (
              /* Year Picker Grid */
              <ScrollView
                style={styles.yearScrollContainer}
                contentContainerStyle={styles.yearGrid}
                showsVerticalScrollIndicator={false}
              >
                {years.map((y) => (
                  <TouchableOpacity
                    key={y}
                    style={[
                      styles.yearItem,
                      y === viewYear && {
                        backgroundColor: colors.primary + '20',
                        borderColor: colors.primary,
                        borderWidth: 1,
                      },
                    ]}
                    onPress={() => {
                      setViewYear(y);
                      setShowYearGrid(false);
                    }}
                    activeOpacity={0.6}
                  >
                    <Text
                      style={[
                        styles.yearText,
                        { color: y === viewYear ? colors.primary : colors.text },
                        y === viewYear && { fontWeight: '700' },
                      ]}
                    >
                      {y}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            ) : (
              <>
                {/* Weekday Headers */}
                <View style={styles.weekdayRow}>
                  {WEEKDAYS.map((wd) => (
                    <View key={wd} style={styles.weekdayCell}>
                      <Text style={[styles.weekdayText, { color: colors.textMuted }]}>
                        {wd}
                      </Text>
                    </View>
                  ))}
                </View>

                {/* Calendar Days Grid */}
                <View style={styles.daysGrid}>
                  {calendarDays.map((day, idx) => (
                    <TouchableOpacity
                      key={idx}
                      style={[
                        styles.dayCell,
                        day !== null &&
                          isSelected(day) && {
                            backgroundColor: colors.primary,
                            borderRadius: 20,
                          },
                        day !== null &&
                          isToday(day) &&
                          !isSelected(day) && {
                            borderColor: colors.primary,
                            borderWidth: 1,
                            borderRadius: 20,
                          },
                      ]}
                      onPress={() => day !== null && handleDateSelect(day)}
                      disabled={day === null}
                      activeOpacity={0.6}
                    >
                      <Text
                        style={[
                          styles.dayText,
                          { color: colors.text },
                          day !== null && isSelected(day) && { color: '#0B0B0E', fontWeight: '700' },
                          day === null && { color: 'transparent' },
                        ]}
                      >
                        {day || ''}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </>
            )}

            {/* Quick Month Navigation Row */}
            <View style={[styles.monthGrid, { borderTopColor: colors.border }]}>
              {MONTHS_SHORT.map((m, idx) => (
                <TouchableOpacity
                  key={m}
                  style={[
                    styles.monthItem,
                    idx === viewMonth && {
                      backgroundColor: colors.primary + '20',
                      borderColor: colors.primary,
                      borderWidth: 1,
                    },
                  ]}
                  onPress={() => {
                    setViewMonth(idx);
                    setShowYearGrid(false);
                  }}
                  activeOpacity={0.6}
                >
                  <Text
                    style={[
                      styles.monthItemText,
                      { color: idx === viewMonth ? colors.primary : colors.textSecondary },
                      idx === viewMonth && { fontWeight: '700' },
                    ]}
                  >
                    {m}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Today Button */}
            <TouchableOpacity
              style={[styles.todayButton, { borderColor: colors.primary + '40' }]}
              onPress={() => {
                const now = new Date();
                onDateChange(now);
                setVisible(false);
              }}
              activeOpacity={0.7}
            >
              <Text style={[styles.todayButtonText, { color: colors.primary }]}>
                Today
              </Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  // --- Compact Date Button ---
  dateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    borderWidth: 1,
    gap: 6,
  },
  dateIcon: {
    fontSize: 14,
  },
  dateText: {
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 0.3,
  },

  // --- Modal Overlay ---
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },

  // --- Calendar Container ---
  calendarContainer: {
    width: '100%',
    maxWidth: 340,
    borderRadius: 20,
    borderWidth: 1,
    padding: 16,
    ...(Platform.OS === 'ios'
      ? {
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 12 },
          shadowOpacity: 0.3,
          shadowRadius: 20,
        }
      : { elevation: 12 }),
  },

  // --- Calendar Header ---
  calendarHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  navButton: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 18,
  },
  navText: {
    fontSize: 28,
    fontWeight: '300',
    lineHeight: 32,
  },
  monthYearButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  monthYearText: {
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  dropdownArrow: {
    fontSize: 8,
    marginTop: 1,
  },

  // --- Weekday Row ---
  weekdayRow: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  weekdayCell: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 4,
  },
  weekdayText: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.5,
  },

  // --- Days Grid ---
  daysGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  dayCell: {
    width: '14.28%',
    aspectRatio: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dayText: {
    fontSize: 14,
    fontWeight: '500',
  },

  // --- Year Picker ---
  yearScrollContainer: {
    maxHeight: 200,
  },
  yearGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  yearItem: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    minWidth: 70,
    alignItems: 'center',
  },
  yearText: {
    fontSize: 15,
    fontWeight: '500',
  },

  // --- Month Quick Nav ---
  monthGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 4,
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
  },
  monthItem: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 8,
    minWidth: 40,
    alignItems: 'center',
  },
  monthItemText: {
    fontSize: 11,
    fontWeight: '500',
  },

  // --- Today Button ---
  todayButton: {
    alignSelf: 'center',
    marginTop: 12,
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
  },
  todayButtonText: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});
