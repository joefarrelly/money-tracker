const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Transactions
export const getTransactions = (params: Record<string, string | number>) =>
  request<import("../types").PaginatedTransactions>(
    `/transactions/?${new URLSearchParams(params as Record<string, string>)}`
  );

export const patchTransaction = (id: number, data: object) =>
  request<import("../types").Transaction>(`/transactions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const bulkCategorise = (pattern: string, category_id: number) =>
  request<{ updated: number }>("/transactions/bulk-categorise", {
    method: "PATCH",
    body: JSON.stringify({ pattern, category_id }),
  });

// Categories
export const getCategories = () =>
  request<import("../types").Category[]>("/categories/");

export const createCategory = (data: object) =>
  request<import("../types").Category>("/categories/", {
    method: "POST",
    body: JSON.stringify(data),
  });

// Salaries
export const getSalaries = () =>
  request<import("../types").Salary[]>("/salaries/");

export const createSalary = (data: object) =>
  request<import("../types").Salary>("/salaries/", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const deleteSalary = (id: number) =>
  request<void>(`/salaries/${id}`, { method: "DELETE" });

// Dashboard
export const getMonthlySummary = (year: number, month: number) =>
  request<import("../types").MonthlySummary>(
    `/dashboard/summary?year=${year}&month=${month}`
  );

export const getTrend = (months = 6) =>
  request<import("../types").MonthlySummary[]>(`/dashboard/trend?months=${months}`);

export const getRecurring = () =>
  request<import("../types").RecurringExpense[]>("/dashboard/recurring");

export const syncRecurring = () =>
  request<{ created: number; updated: number; skipped: number }>(
    "/dashboard/recurring/sync",
    { method: "POST" }
  );

export const patchRecurring = (id: number, data: object) =>
  request<import("../types").RecurringExpense>(`/dashboard/recurring/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

// Accounts
export const getAccounts = () =>
  request<import("../types").Account[]>("/accounts/");

// Upload
export const uploadStatement = (formData: FormData) =>
  fetch(`${BASE}/upload/`, { method: "POST", body: formData }).then((r) => {
    if (!r.ok) return r.json().then((e) => Promise.reject(new Error(e.error)));
    return r.json();
  });
