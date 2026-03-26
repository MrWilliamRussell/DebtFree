import axios from "axios";

const api = axios.create({
  baseURL: "/api",
});

// Dashboard
export const getDashboardSummary = () => api.get("/dashboard/summary");
export const getIncomes = () => api.get("/dashboard/incomes");
export const createIncome = (data) => api.post("/dashboard/incomes", data);

// Accounts
export const getAccounts = () => api.get("/accounts/");
export const createAccount = (data) => api.post("/accounts/", data);
export const updateAccount = (id, data) => api.put(`/accounts/${id}`, data);
export const deleteAccount = (id) => api.delete(`/accounts/${id}`);

// Plaid Bank Connections
export const getPlaidStatus = () => api.get("/accounts/plaid/status");
export const createPlaidLinkToken = () => api.post("/accounts/plaid/link-token");
export const exchangePlaidToken = (publicToken, institution) =>
  api.post(`/accounts/plaid/exchange-token?public_token=${publicToken}&institution_name=${encodeURIComponent(institution)}`);
export const getConnectedAccounts = () => api.get("/accounts/plaid/connected");
export const syncConnectedAccount = (id) => api.post(`/accounts/plaid/sync/${id}`);
export const syncAllAccounts = () => api.post("/accounts/plaid/sync-all");
export const disconnectAccount = (id) => api.delete(`/accounts/plaid/connected/${id}`);

// Transactions
export const getTransactions = (params) => api.get("/transactions/", { params });
export const createTransaction = (data) => api.post("/transactions/", data);
export const deleteTransaction = (id) => api.delete(`/transactions/${id}`);

// Debts
export const getDebts = () => api.get("/debts/");
export const createDebt = (data) => api.post("/debts/", data);
export const updateDebt = (id, data) => api.put(`/debts/${id}`, data);
export const getPayoffPlan = (data) => api.post("/debts/payoff-plan", data);

// Budgets
export const getBudgets = () => api.get("/budgets/");
export const createBudget = (data) => api.post("/budgets/", data);
export const updateBudget = (id, data) => api.put(`/budgets/${id}`, data);
export const deleteBudget = (id) => api.delete(`/budgets/${id}`);

// Import
export const importCSV = (accountId, file, useLLM = true) => {
  const form = new FormData();
  form.append("file", file);
  return api.post(`/imports/csv?account_id=${accountId}&use_llm=${useLLM}`, form);
};
export const importAmazon = (accountId, file, useLLM = true) => {
  const form = new FormData();
  form.append("file", file);
  return api.post(`/imports/amazon?account_id=${accountId}&use_llm=${useLLM}`, form);
};

// NLP Entry
export const parseNLP = (data) => api.post("/nlp/parse", data);
export const parseAndSaveNLP = (data) => api.post("/nlp/parse-and-save", data);

// Forecasting
export const getForecast = (data) => api.post("/forecast/spending", data);

// Subscriptions
export const getSubscriptions = (params) => api.get("/subscriptions/", { params });
export const getWasteAnalysis = () => api.get("/subscriptions/waste-analysis");

// Health Score
export const getHealthScore = () => api.get("/health/score");
export const getCoachingNudge = () => api.get("/health/nudge");

// Scenarios
export const runScenarios = (data) => api.post("/scenarios/optimize", data);

// Feedback
export const submitFeedback = (data) => api.post("/feedback/", data);
export const getFeedbackMetrics = () => api.get("/feedback/metrics");

// Reports
export const downloadReport = () =>
  api.get("/reports/monthly", { responseType: "blob" });

// Automation
export const getStoredCredentials = () => api.get("/automation/credentials");
export const storeCredentials = (data) => api.post("/automation/credentials", data);
export const deleteCredential = (id) => api.delete(`/automation/credentials/${id}`);
export const testCredential = (id) => api.post(`/automation/credentials/${id}/test`);
export const getSchedulerStatus = () => api.get("/automation/scheduler/status");
export const triggerJob = (jobId) => api.post(`/automation/scheduler/trigger/${jobId}`);
export const syncEverythingNow = () => api.post("/automation/sync-now");

export default api;
