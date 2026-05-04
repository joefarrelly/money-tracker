const BASE = "/api";
const TTL = 60_000;
const cache = new Map<string, { data: unknown; ts: number }>();

function cacheGet<T>(key: string): T | null {
  const entry = cache.get(key);
  if (!entry || Date.now() - entry.ts > TTL) return null;
  return entry.data as T;
}

export function invalidateCache() {
  cache.clear();
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const isGet = !options?.method || options.method.toUpperCase() === "GET";
  const key = `${BASE}${path}`;

  if (isGet) {
    const cached = cacheGet<T>(key);
    if (cached !== null) return cached;
  } else {
    cache.clear();
  }

  const res = await fetch(key, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!res.ok) {
    try {
      const body = JSON.parse(text);
      throw new Error(body.detail ?? body.error ?? `HTTP ${res.status}`);
    } catch (e) {
      if (e instanceof Error && e.message !== text) throw e;
      throw new Error(`HTTP ${res.status}: ${text.slice(0, 120)}`);
    }
  }
  const data = JSON.parse(text) as T;
  if (isGet) cache.set(key, { data, ts: Date.now() });
  return data;
}

// Transactions
export const getRecentTransactions = (year: number, month: number, limit = 8) =>
  request<import("../types").PaginatedTransactions>(
    `/transactions/?year=${year}&month=${month}&per_page=${limit}&page=1`
  );

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

export const bulkUploadPayslips = (files: File[]) => {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  return fetch(`${BASE}/salaries/bulk-upload-payslips`, { method: "POST", body: fd }).then(
    async (r) => {
      const text = await r.text();
      if (!r.ok) {
        try {
          const e = JSON.parse(text);
          return Promise.reject(new Error(e.detail ?? `HTTP ${r.status}`));
        } catch {
          return Promise.reject(new Error(`HTTP ${r.status}: ${text.slice(0, 120)}`));
        }
      }
      cache.clear();
      return JSON.parse(text) as {
        results: { filename: string; status: string; detail?: string; date?: string; net?: number }[];
        imported: number;
        skipped: number;
        errors: number;
      };
    }
  );
};

export const uploadPayslip = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return fetch(`${BASE}/salaries/upload-payslip`, { method: "POST", body: fd }).then(
    async (r) => {
      const text = await r.text();
      if (!r.ok) {
        try {
          const e = JSON.parse(text);
          return Promise.reject(new Error(e.detail ?? `HTTP ${r.status}`));
        } catch {
          return Promise.reject(new Error(`HTTP ${r.status}: ${text.slice(0, 120)}`));
        }
      }
      cache.clear();
      return JSON.parse(text) as import("../types").Salary;
    }
  );
};

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

// Transfers
export const getTransferCandidates = () =>
  request<import("../types").TransferCandidate[]>("/transfers/candidates");

export const getConfirmedTransfers = () =>
  request<import("../types").ConfirmedTransfer[]>("/transfers/confirmed");

export const confirmTransfer = (txn_out_id: number, txn_in_id: number) =>
  request<{ ok: boolean }>("/transfers/confirm", {
    method: "POST",
    body: JSON.stringify({ txn_out_id, txn_in_id }),
  });

export const ignoreTransfer = (txn_id: number) =>
  request<{ ok: boolean }>("/transfers/ignore", {
    method: "POST",
    body: JSON.stringify({ txn_id }),
  });

export const unlinkTransfer = (txn_id: number) =>
  request<{ ok: boolean }>(`/transfers/unlink/${txn_id}`, { method: "POST" });

// Accounts
export const getAccounts = () =>
  request<import("../types").Account[]>("/accounts/");

export const updateAccount = (id: number, nickname: string) =>
  request<import("../types").Account>(`/accounts/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ nickname }),
  });

// Settings — NI numbers / person identities
export const getNiNumbers = () =>
  request<{ ni_number: string; display_name: string | null; identity_id: number | null }[]>(
    "/settings/ni-numbers"
  );

export const setNiName = (ni_number: string, display_name: string) =>
  request<import("../types").PersonIdentity>(`/settings/ni-numbers/${ni_number}`, {
    method: "PUT",
    body: JSON.stringify({ display_name }),
  });

// kept for Salaries page name resolution
export const getIdentities = () =>
  request<{ ni_number: string; display_name: string | null; identity_id: number | null }[]>(
    "/settings/ni-numbers"
  ).then((rows) =>
    rows
      .filter((r) => r.display_name !== null)
      .map((r) => ({ id: r.identity_id!, ni_number: r.ni_number, display_name: r.display_name!, created_at: "" }))
  );

// Upload
export const uploadStatement = (formData: FormData) =>
  fetch(`${BASE}/upload/`, { method: "POST", body: formData }).then((r) => {
    if (!r.ok) return r.json().then((e) => Promise.reject(new Error(e.error)));
    return r.json();
  });

export const previewUpload = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return fetch(`${BASE}/upload/preview`, { method: "POST", body: fd }).then(async (r) => {
    const text = await r.text();
    if (!r.ok) {
      try {
        const e = JSON.parse(text);
        return Promise.reject(new Error(e.detail ?? e.error ?? `HTTP ${r.status}`));
      } catch {
        return Promise.reject(new Error(`Server error (${r.status}): ${text.slice(0, 120)}`));
      }
    }
    try {
      return JSON.parse(text) as import("../types").PreviewResponse;
    } catch {
      return Promise.reject(new Error(`Unexpected response from server: ${text.slice(0, 120)}`));
    }
  });
};

export const confirmUpload = (body: object) =>
  request<{ added: number; skipped: number; account: import("../types").Account; transactions: import("../types").Transaction[] }>(
    "/upload/confirm",
    { method: "POST", body: JSON.stringify(body) }
  );

export const getFormats = () =>
  request<import("../types").StatementFormat[]>("/upload/formats");

export const detectAccount = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return fetch(`${BASE}/upload/detect-account`, { method: "POST", body: fd }).then(async (r) => {
    const text = await r.text();
    if (!r.ok) return { account_number: null };
    return JSON.parse(text) as { account_number: string | null };
  });
};

// Email imports
export const getEmailImports = (status?: string) =>
  request<import("../types").EmailImport[]>(
    `/email-imports/${status ? `?status=${status}` : ""}`
  );

export const pollEmails = () =>
  request<{ new_imports: number; message: string }>("/email-imports/poll", { method: "POST" });

export const confirmEmailImport = (id: number) =>
  request<import("../types").EmailImport>(`/email-imports/${id}/confirm`, { method: "POST" });

export const skipEmailImport = (id: number) =>
  request<import("../types").EmailImport>(`/email-imports/${id}/skip`, { method: "POST" });

export const deleteEmailImport = (id: number) =>
  request<void>(`/email-imports/${id}`, { method: "DELETE" });

export const bulkUpload = (
  files: File[],
  formatId: number,
  accountNumber: string,
  skipPatterns: string,
  year?: number,
) => {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  fd.append("format_id", String(formatId));
  fd.append("account_number", accountNumber);
  fd.append("skip_patterns", skipPatterns);
  if (year != null) fd.append("year", String(year));
  return fetch(`${BASE}/upload/bulk`, { method: "POST", body: fd }).then(async (r) => {
    const text = await r.text();
    if (!r.ok) {
      try {
        const e = JSON.parse(text);
        return Promise.reject(new Error(e.detail ?? e.error ?? `HTTP ${r.status}`));
      } catch {
        return Promise.reject(new Error(`Server error (${r.status}): ${text.slice(0, 120)}`));
      }
    }
    cache.clear();
    return JSON.parse(text) as import("../types").BulkUploadResult;
  });
};
