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
  const [testing, setTesting] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [saveResult, setSaveResult] = useState(null);

  const load = () => {
    getStoredCredentials().then((r) => setCreds(r.data)).catch(() => {});
    getSchedulerStatus().then((r) => {
      setJobs(r.data.jobs || []);
      setSchedulerRunning(r.data.running);
    }).catch(() => {});
  };

  useEffect(load, []);

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
    await deleteCredential(id);
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
    try {
      await triggerJob(jobId);
      load();
    } catch {}
  };

  const handleSyncAll = async () => {
    setSyncing(true);
    try {
      await syncEverythingNow();
    } catch {}
    setSyncing(false);
    load();
  };

  const typeLabels = {
    amazon: "Amazon",
    bank_direct: "Bank (Direct)",
    email: "Email (Receipts)",
    custom: "Custom",
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Automation</h2>
      <p className="text-gray-400">
        Set up automated bank syncing, Amazon order imports, and scheduled alerts.
        All credentials are encrypted with AES-128 — never stored in plaintext.
      </p>

      {/* Sync Everything Button */}
      <button
        onClick={handleSyncAll}
        disabled={syncing}
        className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg px-6 py-3 text-sm font-semibold transition-colors"
      >
        {syncing ? "Syncing Everything..." : "Sync Everything Now"}
      </button>

      {/* Scheduler Status */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Scheduled Jobs</h3>
          <span className={`text-xs font-bold px-2 py-1 rounded ${schedulerRunning ? "bg-emerald-600" : "bg-red-600"}`}>
            {schedulerRunning ? "RUNNING" : "STOPPED"}
          </span>
        </div>

        {jobs.length > 0 ? (
          <div className="space-y-2">
            {jobs.map((job) => (
              <div key={job.id} className="bg-gray-700 rounded-lg p-4 flex justify-between items-center">
                <div>
                  <p className="font-semibold text-sm">{job.name}</p>
                  <p className="text-xs text-gray-400">
                    Schedule: {job.trigger}
                  </p>
                  {job.next_run && (
                    <p className="text-xs text-gray-500">
                      Next run: {new Date(job.next_run).toLocaleString()}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleTrigger(job.id)}
                  className="bg-blue-600 hover:bg-blue-700 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors"
                >
                  Run Now
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">Scheduler will start when the backend boots.</p>
        )}
      </div>

      {/* Stored Credentials */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="text-lg font-semibold mb-4">Stored Credentials</h3>
        <p className="text-xs text-gray-500 mb-4">
          Encrypted with AES-128 (Fernet). Derived from your SECRET_KEY.
          Change SECRET_KEY = lose access to stored credentials.
        </p>

        {creds.length > 0 ? (
          <div className="space-y-3 mb-6">
            {creds.map((c) => (
              <div key={c.id} className="bg-gray-700 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{c.name}</span>
                      <span className="text-xs bg-gray-600 px-2 py-0.5 rounded">
                        {typeLabels[c.credential_type] || c.credential_type}
                      </span>
                    </div>
                    <div className="text-sm text-gray-400 mt-1">
                      {Object.entries(c.masked_credentials).map(([k, v]) => (
                        <span key={k} className="mr-3">{k}: {v}</span>
                      ))}
                    </div>
                    {c.last_used && (
                      <p className="text-xs text-gray-500 mt-1">Last used: {new Date(c.last_used).toLocaleString()}</p>
                    )}
                    {c.last_error && (
                      <p className="text-xs text-red-400 mt-1">Error: {c.last_error}</p>
                    )}
                    {testResult && testResult.id === c.id && (
                      <p className={`text-xs mt-1 ${testResult.status === "ok" ? "text-emerald-400" : "text-red-400"}`}>
                        Test: {testResult.status} {testResult.detail ? `— ${testResult.detail}` : ""}
                        {testResult.orders_found !== undefined && ` (${testResult.orders_found} orders found)`}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleTest(c.id)}
                      disabled={testing === c.id}
                      className="text-sm text-blue-400 hover:underline"
                    >
                      {testing === c.id ? "Testing..." : "Test"}
                    </button>
                    <button
                      onClick={() => handleDelete(c.id)}
                      className="text-sm text-red-400 hover:underline"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm mb-4">No credentials stored yet.</p>
        )}

        {/* Add Credential Form */}
        <form onSubmit={handleStore} className="border-t border-gray-600 pt-4 space-y-3">
          <h4 className="text-sm font-semibold">Add Credentials</h4>
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Name (e.g. My Amazon)"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="bg-gray-700 rounded-lg px-3 py-2 text-sm"
              required
            />
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
              className="bg-gray-700 rounded-lg px-3 py-2 text-sm"
            >
              <option value="amazon">Amazon</option>
              <option value="bank_direct">Bank (Direct Login)</option>
              <option value="email">Email (Receipt Scanning)</option>
              <option value="custom">Custom</option>
            </select>
            <input
              type="email"
              placeholder="Email / Username"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="bg-gray-700 rounded-lg px-3 py-2 text-sm"
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="bg-gray-700 rounded-lg px-3 py-2 text-sm"
              required
            />
          </div>
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
          >
            Store (Encrypted)
          </button>

          {saveResult && (
            <p className={`text-sm ${saveResult.error ? "text-red-400" : "text-emerald-400"}`}>
              {saveResult.error || saveResult.message}
            </p>
          )}
        </form>
      </div>

      {/* Security Info */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="font-semibold mb-3">Security Model</h3>
        <ul className="text-sm text-gray-400 space-y-2">
          <li><span className="text-emerald-400 font-bold">Plaid</span> — OAuth tokens only. Your bank password never touches our system.</li>
          <li><span className="text-yellow-400 font-bold">Amazon</span> — Credentials encrypted with AES-128 (Fernet). Stored in YOUR PostgreSQL. Headless browser runs locally.</li>
          <li><span className="text-blue-400 font-bold">Encryption Key</span> — Derived from SECRET_KEY in .env. If you change it, stored credentials become unreadable (by design).</li>
          <li><span className="text-gray-400 font-bold">Self-hosted</span> — Everything runs in your Docker containers. No data leaves your machine.</li>
        </ul>
      </div>
    </div>
  );
}
