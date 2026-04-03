export interface Account {
  id: number;
  bank: string;
  account_number: string;
  nickname: string;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  color: string;
  icon: string | null;
}

export interface Transaction {
  id: number;
  account_id: number;
  account: Account | null;
  date: string;
  description: string;
  amount: number;
  balance: number | null;
  category_id: number | null;
  category: Category | null;
  is_recurring: boolean;
  source_file: string | null;
  created_at: string;
}

export interface RecurringExpense {
  id: number;
  merchant_pattern: string;
  category_id: number | null;
  category: Category | null;
  typical_amount: number;
  frequency: "monthly" | "annual";
  day_of_month: number | null;
  is_active: boolean;
  is_confirmed: boolean;
  monthly_cost: number;
  created_at: string;
}

export interface Salary {
  id: number;
  date: string;
  gross_amount: number | null;
  net_amount: number;
  employer: string | null;
  notes: string | null;
  created_at: string;
}

export interface CategoryBreakdown {
  name: string;
  amount: number;
  color: string;
  count: number;
}

export interface MonthlySummary {
  year: number;
  month: number;
  total_in: number;
  total_out: number;
  net: number;
  salary: number;
  recurring_total: number;
  disposable_income: number;
  category_breakdown: CategoryBreakdown[];
  transaction_count: number;
  salary_entries: Salary[];
}

export interface PaginatedTransactions {
  transactions: Transaction[];
  total: number;
  page: number;
  pages: number;
  per_page: number;
}
