import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';

export interface BranchStatus {
  id: string;
  name: string;
  code: string;
  monthly_sales_target: number;
  status: 'SUBMITTED' | 'PENDING';
  report: {
    id: string;
    sales_amount: number;
    attendance_count: number;
    target_achievement: number;
    inventory_status: string | null;
    remarks: string | null;
    issues: string | null;
    original_file_url: string | null;
    // New production template fields
    gold?: number;
    diamond?: number;
    platinum?: number;
    silver?: number;
    silver_mrp?: number;
    total_revenue?: number;
    digigold?: number;
    digisilver?: number;
    employees_present?: number;
    employees_absent?: number;
    customer_complaints?: string | null;
    operational_issues?: string | null;
  } | null;
}

export interface BranchAnalytics {
  branch: {
    id: string;
    name: string;
    code: string;
    monthly_sales_target: number;
  };
  summary: {
    total_sales: number;
    average_attendance: number;
    average_target_achievement: number;
    reports_count: number;
    issues_count: number;
  };
  trends: Array<{
    date: string;
    sales_amount: number;
    attendance_count: number;
    target_achievement: number;
  }>;
  recent_issues: Array<{
    date: string;
    manager: string;
    issues: string;
  }>;
  today_report_details?: {
    employee_performances?: Array<{
      employee_name: string;
      gold: number;
      diamond: number;
      platinum: number;
      silver: number;
      silver_mrp: number;
      subhiksham_count: number;
      subhiksham_value: number;
      viruksham_count: number;
      viruksham_value: number;
      digigold: number;
      digisilver: number;
      sales: number;
    }>;
    top_performer?: string;
    scheme_summary?: {
      subhiksham_count?: number;
      subhiksham_value?: number;
      viruksham_count?: number;
      viruksham_value?: number;
      scheme_items?: Array<{
        scheme_name?: string;
        count?: number;
        value?: number;
      }>;
      overall_remarks?: string;
    };
    report?: any;
  };
}

export interface DashboardSummary {
  total_revenue: number;
  digigold: number;
  digisilver: number;
  employees_present: number;
  employees_absent: number;
  complaints_count: number;
  top_performing_branch: string;
  top_performing_employee: string;
  complaints: string[];
}

export function useBranchesDashboard(reportDate?: string) {
  return useQuery<BranchStatus[]>({
    queryKey: ['branches-dashboard', reportDate],
    queryFn: async () => {
      const url = reportDate ? `/branches?report_date=${reportDate}` : '/branches';
      const res = await apiClient.get(url);
      return res.data;
    },
    refetchInterval: 60000, // auto-refresh dashboard data every 60s
  });
}

export function useDashboardSummary(reportDate?: string) {
  return useQuery<DashboardSummary>({
    queryKey: ['dashboard-summary', reportDate],
    queryFn: async () => {
      const url = reportDate ? `/branches/dashboard-summary?report_date=${reportDate}` : '/branches/dashboard-summary';
      const res = await apiClient.get(url);
      return res.data;
    },
    refetchInterval: 60000,
  });
}

export function useBranchAnalytics(branchId: string, reportDate?: string | null, startDate?: string, endDate?: string) {
  return useQuery<BranchAnalytics>({
    queryKey: ['branch-analytics', branchId, reportDate || 'latest', startDate || '', endDate || ''],
    queryFn: async () => {
      let url = `/branches/${branchId}/analytics`;
      const params = [];
      if (reportDate) params.push(`report_date=${reportDate}`);
      if (startDate) params.push(`start_date=${startDate}`);
      if (endDate) params.push(`end_date=${endDate}`);
      if (params.length) url += `?${params.join('&')}`;
      
      const res = await apiClient.get(url);
      return res.data;
    },
    enabled: !!branchId,
    staleTime: 1000 * 60 * 5, // 5 minutes stale time for smooth in-memory caching
    gcTime: 1000 * 60 * 30,    // 30 minutes session cache
  });
}
