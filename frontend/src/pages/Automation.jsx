import { useEffect, useState } from "react";
import {
  getStoredCredentials, storeCredentials, deleteCredential, testCredential,
  getSchedulerStatus, triggerJob, syncEverythingNow,
} from "../api";

export default function Automation() {
  const [creds, setCreds] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [schedulerRunning, setSchedulerRunning] = useState(false);
  const [form, setForm] = useState({ name: "", type: "amazon", email: "", password: "" });
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const [testing, setTesting] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [saveResult, setSaveResult] = useState(null);
  const [triggerResults, setTriggerResults] = useState({});
  const [confirmDelete, setConfirmDelete] = useState(null);

  const load = () => {
    getStoredCredentials().then((r) => setCreds(r.data)).catch(() => {});
    getSchedulerStatus().then((r) => {
      setJobs(r.data.jobs || []);
      setSchedulerRunning(r.data.running);
    }).catch(() => {});
  };

  useEffect(load, []);

  // Auto-clear result banners after 8 seconds
  useEffect(() => {
    if (syncResult) {
      const t = setTimeout(() => setSyncResult(null), 8000);
      return () => clearTimeout(t);
    }
  }, [syncResult]);

  const handleStore = async (e) => {
    e.preventDefault();
    setSaveResult(null);
    try {
      const payload = {
        name: form.name,
        credential_type: form.type,
        credentials: { email: form.email, password: form.password },
      };
      const r = await storeCredentials(payload);
      setSaveResult(r.data);
      setForm({ name: "", type: "amazon", email: "", password: "" });
      load();
    } catch (err) {
      setSaveResult({ error: err.response?.data?.detail || "Failed to store" });
    }
  };

  const handleDelete = async (id) => {
    if (confirmDelete !== id) {
      setConfirmDelete(id);
      return;
    }
    await deleteCredential(id);
    setConfirmDelete(null);
    load();
  };

  const handleTest = async (id) => {
    setTesting(id);
    setTestResult(null);
    try {
      const r = await testCredential(id);
      setTestResult({ id, ...r.data });
    } catch (err) {
      setTestResult({ id, status: "error", detail: err.response?.data?.detail || "Test failed" });
    }
    setTesting(null);
  };

  const handleTrigger = async (jobId) => {
    setTriggerResults((prev) => ({ ...prev, [jobId]: { status: "running" } }));
    try {
      const r = await triggerJob(jobId);
      setTriggerResults((prev) => ({ ...prev, [jobId]: r.data }));
    } catch (err) {
      setTriggerResults((prev) => ({
        ...prev,
        [jobId]: { status: "error", detail: err.response?.data?.detail || "Failed" },
      }));
    }
    load();
  };

  const handleSyncAll = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const r = await syncEverythingNow();
      setSyncResult(r.data);
    } catch (err) {
      setSyncResult({ error: err.response?.data?.detail || "Sync failed" });
    }
    setSyncing(false);
    load();
  };

  const typeLabels = {
    amazon: "Amazon",
    bank_direct: "Bank (Direct)",
    email: "Email (Receipts)",
    custom: "Custom",
  };

  const jobDescriptions = {
    plaid_sync: "Pulls new transactions from all connected bank accounts and credit cards via Plaid.",
    amazon_scrape: "Logs into Amazon with stored credentials and imports new order history.",
    daily_nudge: "Sends a motivational coaching message to Discord based on your financial snapshot.",
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Automation</h2>
      <p className="text-gray-400">
        Automated bank syncing, Amazon order imports, and scheduled alerts.
        All credentials encrypted with AES-128 — never stored in plaintext.
      </p>

      {/* Sync Everything Banner */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold">Manual Sync</h3>
            <p className="text-sm text-gray-400 mt-1">
              Pull new data from all connected banks + Amazon right now.
            </p>
          </div>
          <button
            onClick={handleSyncAll}
            disabled={syncing}
            className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg px-6 py-3 text-sm font-semibold transition-colors flex items-center gap-2"
          >
            {syncing && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {syncing ? "Syncing Everything..." : "Sync Everything Now"}
          </button>
        </div>

        {/* Sync result feedback */}
        {syncResult && (
          <div className={`mt-4 p-4 rounded-lg ${syncResult.error ? "bg-red-900/30 border border-red-700" : "bg-emerald-900/30 border border-emerald-700"}`}>
            {syncResult.error ? (
              <p className="text-red-400">{syncResult.error}</p>
            ) : (
              <div className="space-y-1">
                <p className="text-emerald-400 font-semibold">Sync Complete</p>
                {Object.entries(syncResult.results || {}).map(([key, val]) => (
                  <p key={key} className="text-sm text-gray-300">
                    <span className="capitalize">{key}</span>:{" "}
                    <span className={val === "ok" || val.status === "ok" ? "text-emerald-400" : "text-red-400"}>
                      {typeof val === "string" ? val : val.status || JSON.stringify(val)}
                    </span>
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Scheduler Status */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Scheduled Jobs</h3>
          <span className={`text-xs font-bold px-2 py-1 rounded ${schedulerRunning ? "bg-emerald-600" : "bg-red-600"}`}>
            {schedulerRunning ? "RUNNING" : "STOPPED"}
          </span>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          Jobs run automatically on schedule. Click "Run Now" to trigger manually at any time.
        </p>

        {jobs.length > 0 ? (
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="bg-gray-700 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className="font-semibold text-sm">{job.name}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {jobDescriptions[job.id] || `Schedule: ${job.trigger}`}
                    </p>
                    <div className="flex gap-4 mt-2 text-xs text-gray-500">
                      <span>Schedule: {job.trigger}</span>
                      {job.next_run && (
                        <span>Next: {new Date(job.next_run).toLocaleString()}</span>
                      )}
                    </div>

                    {/* Per-job result feedback */}
                    {triggerResults[job.id] && (
                      <p className={`text-xs mt-2 ${
                        triggerResults[job.id].status === "running" ? "text-blue-400" :
                        triggerResults[job.id].status === "ok" ? "text-emerald-400" : "text-red-400"
                      }`}>
                        {triggerResults[job.id].status === "running" && "Running..."}
                        {triggerResults[job.id].status === "ok" && `Done — ${triggerResults[job.id].message || "Success"}`}
                        {triggerResults[job.id].status === "error" && `Error: ${triggerResults[job.id].detail}`}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleTrigger(job.id)}
                    disabled={triggerResults[job.id]?.status === "running"}
                    className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-4 py-2 text-xs font-semibold transition-colors whitespace-nowrap"
                  >
                    {triggerResults[job.id]?.status === "running" ? (
                      <span className="flex items-center gap-1">
                        <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Running...
                      </span>
                    ) : "Run Now"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-gray-700 rounded-lg p-4 text-sm text-gray-400">
            <p>Scheduler starts automatically when the backend boots. If you see this, the backend may not be running.</p>
            <p className="mt-1 text-xs text-gray-500">Run: <code className="bg-gray-600 px-1 rounded">docker compose up --build</code></p>
          </div>
        )}
      </div>

      {/* Stored Credentials */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="text-lg font-semibold mb-2">Stored Credentials</h3>
        <p className="text-xs text-gray-500 mb-4">
          Encrypted with AES-128 (Fernet) derived from SECRET_KEY. Passwords are never visible — only masked previews shown.
        </p>

        {creds.length > 0 && (
          <div className="space-y-3 mb-6">
            {creds.map((c) => (
              <div key={c.id} className="bg-gray-700 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{c.name}</span>
                      <span className="text-xs bg-gray-600 px-2 py-0.5 rounded">
                        {typeLabels[c.credential_type] || c.credential_type}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded ${c.is_active ? "bg-emerald-900 text-emerald-400" : "bg-red-900 text-red-400"}`}>
                        {c.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                    <div className="text-sm text-gray-400 mt-1 font-mono">
                      {Object.entries(c.masked_credentials).map(([k, v]) => (
                        <span key={k} className="mr-4">{k}: {v}</span>
                      ))}
                    </div>
                    {c.last_used && (
                      <p className="text-xs text-gray-500 mt-1">Last used: {new Date(c.last_used).toLocaleString()}</p>
                    )}
                    {c.last_error && (
                      <p className="text-xs text-red-400 mt-1">Last error: {c.last_error}</p>
                    )}

                    {/* Test result */}
                    {testResult && testResult.id === c.id && (
                      <div className={`text-xs mt-2 p-2 rounded ${testResult.status === "ok" ? "bg-emerald-900/30 text-emerald-400" : "bg-red-900/30 text-red-400"}`}>
                        {testResult.status === "ok"
                          ? `Test passed${testResult.orders_found !== undefined ? ` — ${testResult.orders_found} orders found` : ""}`
                          : `Test failed: ${testResult.detail}`}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => handleTest(c.id)}
                      disabled={testing === c.id}
                      className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors"
                    >
                      {testing === c.id ? (
                        <span className="flex items-center gap-1">
                          <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          Testing...
                        </span>
                      ) : "Test"}
                    </button>
                    <button
                      onClick={() => handleDelete(c.id)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                        confirmDelete === c.id
                          ? "bg-red-600 hover:bg-red-700 text-white"
                          : "bg-gray-600 hover:bg-gray-500 text-gray-300"
                      }`}
                    >
                      {confirmDelete === c.id ? "Confirm Delete" : "Delete"}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {creds.length === 0 && (
          <div className="bg-gray-700 rounded-lg p-4 text-sm text-gray-400 mb-4">
            No credentials stored yet. Add Amazon or other service credentials below to enable automated syncing.
          </div>
        )}

        {/* Add Credential Form */}
        <div className="border-t border-gray-600 pt-4 space-y-3">
          <h4 className="text-sm font-semibold">Add New Credentials</h4>
          <form onSubmit={handleStore} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Name</label>
                <input
                  placeholder="e.g. My Amazon Account"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-full"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Service Type</label>
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                  className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-full"
                >
                  <option value="amazon">Amazon</option>
                  <option value="bank_direct">Bank (Direct Login)</option>
                  <option value="email">Email (Receipt Scanning)</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Email / Username</label>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-full"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Password</label>
                <input
                  type="password"
                  placeholder="Encrypted before storage"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-full"
                  required
                />
              </div>
            </div>
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
            >
              Store (Encrypted)
            </button>

            {saveResult && (
              <div className={`p-3 rounded-lg text-sm ${saveResult.error ? "bg-red-900/30 border border-red-700 text-red-400" : "bg-emerald-900/30 border border-emerald-700 text-emerald-400"}`}>
                {saveResult.error || saveResult.message}
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Quick Guide */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="font-semibold mb-3">How Automation Works</h3>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-emerald-400 font-bold text-sm mb-2">1. Connect</p>
            <p className="text-xs text-gray-400">
              Add bank accounts via Plaid (Import → Live Bank Sync tab).
              Add Amazon credentials here. Both methods are encrypted/OAuth.
            </p>
          </div>
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-blue-400 font-bold text-sm mb-2">2. Auto-Sync</p>
            <p className="text-xs text-gray-400">
              The scheduler syncs banks every 6 hours and Amazon daily at 6 AM.
              Or click "Run Now" / "Sync Everything" anytime.
            </p>
          </div>
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-yellow-400 font-bold text-sm mb-2">3. Categorize</p>
            <p className="text-xs text-gray-400">
              Every transaction is auto-categorized: 60+ keyword rules first, then
              the LLM (Mistral) handles anything rules miss.
            </p>
          </div>
        </div>
      </div>

      {/* Security Info */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="font-semibold mb-3">Security</h3>
        <ul className="text-sm text-gray-400 space-y-2">
          <li><span className="text-emerald-400 font-bold">Plaid</span> — OAuth tokens only. Your bank password never touches this system.</li>
          <li><span className="text-yellow-400 font-bold">Amazon</span> — Credentials encrypted with AES-128 (Fernet). Stored in YOUR PostgreSQL only.</li>
          <li><span className="text-blue-400 font-bold">Encryption</span> — Key derived from SECRET_KEY in .env. Change it = stored credentials become unreadable.</li>
          <li><span className="text-gray-400 font-bold">Self-hosted</span> — All data stays in your Docker containers. Nothing leaves your machine.</li>
        </ul>
      </div>
    </div>
  );
}
