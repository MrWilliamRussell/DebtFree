import { useState, useEffect } from "react";
import { importCSV, importAmazon, getAccounts, getConnectedAccounts, syncConnectedAccount, syncAllAccounts, getPlaidStatus, createPlaidLinkToken, exchangePlaidToken } from "../api";

export default function Import() {
  const [accounts, setAccounts] = useState([]);
  const [connected, setConnected] = useState([]);
  const [plaidConfigured, setPlaidConfigured] = useState(false);
  const [tab, setTab] = useState("bank"); // bank, amazon, plaid
  const [accountId, setAccountId] = useState("");
  const [file, setFile] = useState(null);
  const [useLLM, setUseLLM] = useState(true);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(null);
  const [syncResult, setSyncResult] = useState(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    getAccounts().then((r) => setAccounts(r.data));
    getConnectedAccounts().then((r) => setConnected(r.data)).catch(() => {});
    getPlaidStatus().then((r) => setPlaidConfigured(r.data.configured)).catch(() => {});
  }, []);

  const handleImport = async (e) => {
    e.preventDefault();
    if (!file || !accountId) return;
    setLoading(true);
    setResult(null);
    try {
      const fn = tab === "amazon" ? importAmazon : importCSV;
      const r = await fn(parseInt(accountId), file, useLLM);
      setResult(r.data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail || "Import failed" });
    }
    setLoading(false);
  };

  const handleSync = async (connId) => {
    setSyncing(connId);
    setSyncResult(null);
    try {
      const r = await syncConnectedAccount(connId);
      setSyncResult({ id: connId, ...r.data });
      getConnectedAccounts().then((r2) => setConnected(r2.data));
    } catch (err) {
      setSyncResult({ id: connId, error: err.response?.data?.detail || "Sync failed" });
    }
    setSyncing(null);
  };

  const handleSyncAll = async () => {
    setSyncing("all");
    setSyncResult(null);
    try {
      const r = await syncAllAccounts();
      setSyncResult({ id: "all", ...r.data });
      getConnectedAccounts().then((r2) => setConnected(r2.data));
    } catch (err) {
      setSyncResult({ id: "all", error: err.response?.data?.detail || "Sync failed" });
    }
    setSyncing(null);
  };

  const handleConnectBank = async () => {
    setConnecting(true);
    try {
      const r = await createPlaidLinkToken();
      const linkToken = r.data.link_token;
      // Plaid Link is normally loaded via <script> tag. For now, show the token
      // and instructions. In production, integrate the Plaid Link JS SDK.
      setSyncResult({
        id: "connect",
        message: "Plaid Link token created. Integrate the Plaid Link SDK in production, or use sandbox testing.",
        link_token: linkToken,
      });
    } catch (err) {
      setSyncResult({ id: "connect", error: err.response?.data?.detail || "Failed to create link token" });
    }
    setConnecting(false);
  };

  const tabs = [
    { id: "bank", label: "Bank/Credit Card CSV" },
    { id: "amazon", label: "Amazon Orders" },
    { id: "plaid", label: "Live Bank Sync" },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Import Transactions</h2>

      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-800 rounded-lg p-1 w-fit">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => { setTab(t.id); setResult(null); }}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t.id ? "bg-emerald-600 text-white" : "text-gray-400 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* CSV Import (Bank or Amazon) */}
      {(tab === "bank" || tab === "amazon") && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 max-w-lg">
          <p className="text-gray-400 text-sm mb-4">
            {tab === "amazon"
              ? "Upload your Amazon order history CSV. Download from: Amazon → Account → Download order reports."
              : "Upload a CSV from your bank or credit card. Transactions are auto-categorized using rules + AI."}
          </p>
          <form onSubmit={handleImport} className="space-y-4">
            <div>
              <label className="text-sm text-gray-400 block mb-1">Account</label>
              <select value={accountId} onChange={(e) => setAccountId(e.target.value)} className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-full" required>
                <option value="">Select account...</option>
                {accounts.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.account_type.replace("_", " ")})</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-400 block mb-1">CSV File</label>
              <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0])} className="text-sm text-gray-400" required />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input type="checkbox" checked={useLLM} onChange={(e) => setUseLLM(e.target.checked)} className="rounded" />
              Use AI categorization (slower but more accurate)
            </label>
            <button type="submit" disabled={loading} className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-6 py-2 text-sm font-semibold transition-colors">
              {loading ? "Importing..." : `Import ${tab === "amazon" ? "Amazon" : "CSV"}`}
            </button>
          </form>

          {result && (
            <div className={`mt-4 p-4 rounded-lg ${result.error ? "bg-red-900/30 border border-red-700" : "bg-emerald-900/30 border border-emerald-700"}`}>
              {result.error ? (
                <p className="text-red-400">{result.error}</p>
              ) : (
                <div className="text-emerald-400">
                  <p>Imported {result.imported} of {result.total_rows || result.total_orders} transactions</p>
                  {result.llm_categorized > 0 && (
                    <p className="text-sm text-gray-400 mt-1">AI categorized: {result.llm_categorized} items</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Plaid Live Sync */}
      {tab === "plaid" && (
        <div className="space-y-4 max-w-2xl">
          {!plaidConfigured ? (
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="font-semibold mb-3">Set Up Live Bank Sync</h3>
              <p className="text-gray-400 text-sm mb-4">
                Connect your bank accounts and credit cards securely via Plaid.
                Your login credentials are <strong className="text-white">never</strong> stored — you authenticate directly through your bank's portal.
              </p>
              <div className="bg-gray-700 rounded-lg p-4 text-sm space-y-2">
                <p className="text-gray-300">To enable:</p>
                <ol className="list-decimal list-inside text-gray-400 space-y-1">
                  <li>Sign up at <span className="text-blue-400">dashboard.plaid.com</span> (free dev tier)</li>
                  <li>Get your <code className="bg-gray-600 px-1 rounded">client_id</code> and <code className="bg-gray-600 px-1 rounded">secret</code></li>
                  <li>Add to <code className="bg-gray-600 px-1 rounded">.env</code>: PLAID_CLIENT_ID and PLAID_SECRET</li>
                  <li>Restart: <code className="bg-gray-600 px-1 rounded">docker compose restart backend</code></li>
                </ol>
              </div>
            </div>
          ) : (
            <>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold">Connected Accounts</h3>
                  <div className="flex gap-2">
                    <button
                      onClick={handleConnectBank}
                      disabled={connecting}
                      className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
                    >
                      {connecting ? "Connecting..." : "+ Connect Bank"}
                    </button>
                    <button
                      onClick={handleSyncAll}
                      disabled={syncing || connected.length === 0}
                      className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
                    >
                      {syncing === "all" ? "Syncing All..." : "Sync All"}
                    </button>
                  </div>
                </div>

                {/* Sync / connect result feedback */}
                {syncResult && (
                  <div className={`mb-4 p-4 rounded-lg ${syncResult.error ? "bg-red-900/30 border border-red-700" : "bg-emerald-900/30 border border-emerald-700"}`}>
                    {syncResult.error ? (
                      <p className="text-red-400">{syncResult.error}</p>
                    ) : syncResult.imported !== undefined ? (
                      <div className="text-emerald-400">
                        <p>Synced {syncResult.imported} new transactions</p>
                        {syncResult.llm_categorized > 0 && (
                          <p className="text-sm text-gray-400">AI categorized: {syncResult.llm_categorized}</p>
                        )}
                      </div>
                    ) : syncResult.message ? (
                      <p className="text-emerald-400">{syncResult.message}</p>
                    ) : (
                      <p className="text-emerald-400">Sync complete</p>
                    )}
                  </div>
                )}

                {connected.length > 0 ? (
                  <div className="space-y-3">
                    {connected.map((c) => (
                      <div key={c.id} className="bg-gray-700 rounded-lg p-4 flex justify-between items-center">
                        <div>
                          <p className="font-semibold">{c.institution} — {c.account_name}</p>
                          <p className="text-sm text-gray-400">
                            ****{c.mask} · {c.subtype} ·{" "}
                            <span className={c.status === "active" ? "text-emerald-400" : "text-red-400"}>
                              {c.status}
                            </span>
                          </p>
                          {c.last_synced && (
                            <p className="text-xs text-gray-500">Last synced: {new Date(c.last_synced).toLocaleString()}</p>
                          )}
                          {c.error && <p className="text-xs text-red-400">{c.error}</p>}
                          {syncResult && syncResult.id === c.id && !syncResult.error && (
                            <p className="text-xs text-emerald-400 mt-1">Synced {syncResult.imported || 0} new transactions</p>
                          )}
                        </div>
                        <button
                          onClick={() => handleSync(c.id)}
                          disabled={syncing === c.id}
                          className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg px-3 py-1.5 text-sm transition-colors"
                        >
                          {syncing === c.id ? "Syncing..." : "Sync"}
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm py-4">No accounts connected yet. Click "+ Connect Bank" above to link your bank.</p>
                )}
              </div>

              <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                <h4 className="font-semibold text-sm mb-2">How it works</h4>
                <ul className="text-sm text-gray-400 space-y-1">
                  <li>1. Click "Connect Bank" to open Plaid Link</li>
                  <li>2. Log into your bank through their secure portal</li>
                  <li>3. We receive a secure token (never your password)</li>
                  <li>4. Click "Sync" to pull new transactions</li>
                  <li>5. Each transaction is auto-categorized via rules + AI</li>
                </ul>
              </div>
            </>
          )}
        </div>
      )}

      {/* Format guides */}
      {tab === "bank" && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 max-w-lg">
          <h3 className="font-semibold mb-3">Expected CSV Format</h3>
          <p className="text-sm text-gray-400 mb-2">Needs a <code className="bg-gray-700 px-1 rounded">date</code> and <code className="bg-gray-700 px-1 rounded">amount</code> column minimum.</p>
          <pre className="bg-gray-900 rounded-lg p-3 text-xs text-gray-400 overflow-x-auto">
{`date,description,amount
2026-03-01,Shell Gas Station,-45.20
2026-03-02,Amazon.com,-29.99
2026-03-03,Payroll Direct Deposit,3200.00`}
          </pre>
        </div>
      )}
      {tab === "amazon" && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 max-w-lg">
          <h3 className="font-semibold mb-3">How to Export Amazon Order History</h3>
          <ol className="text-sm text-gray-400 space-y-2 list-decimal list-inside">
            <li>Go to <span className="text-blue-400">amazon.com/gp/b2b/reports</span></li>
            <li>Select "Items" report type</li>
            <li>Set date range (e.g. last 12 months)</li>
            <li>Click "Request Report" then download the CSV</li>
            <li>Upload the CSV above</li>
          </ol>
          <p className="text-xs text-gray-500 mt-3">Alternative: Amazon → Account → Request Your Data → Order History</p>
        </div>
      )}
    </div>
  );
}
