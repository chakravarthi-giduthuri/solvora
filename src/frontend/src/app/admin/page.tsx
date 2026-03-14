'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api';
import { BackButton } from '@/components/ui/BackButton';

type ScraperInfo = { status: string; note?: string };
type AdminUser = { id: string; name: string; email: string; is_active: boolean; is_admin: boolean };
type Report = { id: string; status: string; reason: string; detail?: string; created_at: string };

export default function AdminPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'scrapers' | 'users' | 'reports'>('scrapers');
  const [scraperStatus, setScraperStatus] = useState<Record<string, ScraperInfo> | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [triggerMsg, setTriggerMsg] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (status === 'authenticated') {
      loadTab(activeTab);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, activeTab]);

  const loadTab = async (tab: string) => {
    setLoading(true);
    setError('');
    try {
      if (tab === 'scrapers') {
        const res = await apiClient.get<Record<string, ScraperInfo>>('/admin/scrapers/status');
        setScraperStatus(res.data);
      } else if (tab === 'users') {
        const res = await apiClient.get<AdminUser[]>('/admin/users');
        setUsers(res.data);
      } else if (tab === 'reports') {
        const res = await apiClient.get<Report[]>('/admin/reports');
        setReports(res.data);
      }
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 403) {
        setError('Access denied — your account does not have admin privileges.');
      } else {
        setError('Failed to load data. Make sure the backend is running.');
      }
    }
    setLoading(false);
  };

  const triggerScraper = async (source: string) => {
    setTriggerMsg('');
    try {
      const res = await apiClient.post<{ task_id: string }>(`/admin/scrapers/${source}/trigger`);
      setTriggerMsg(`${source} scraper triggered (task: ${res.data?.task_id?.slice(0, 8) ?? ''}...)`);
      setTimeout(() => setTriggerMsg(''), 5000);
    } catch {
      setTriggerMsg(`Failed to trigger ${source} scraper.`);
    }
  };

  if (status === 'loading') return <div className="p-8 text-center">Loading...</div>;
  if (!session) { router.push('/dashboard'); return null; }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <BackButton />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Admin Panel</h1>

      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 w-fit mb-6">
        {(['scrapers', 'users', 'reports'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm rounded-md capitalize transition-colors ${
              activeTab === tab
                ? 'bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-white font-medium'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {triggerMsg && (
        <div className={`mb-4 p-3 rounded-lg text-sm ${
          triggerMsg.startsWith('Failed')
            ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
            : 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
        }`}>
          {triggerMsg}
        </div>
      )}

      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
          <p className="font-medium mb-1">Error</p>
          <p>{error}</p>
          {error.includes('admin privileges') && (
            <p className="mt-2 text-xs opacity-80">
              Set <code className="bg-red-100 dark:bg-red-800 px-1 rounded">ADMIN_EMAILS=your@email.com</code> in your Railway backend environment variables, then log out and back in.
            </p>
          )}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />)}
        </div>
      ) : (
        <>
          {activeTab === 'scrapers' && scraperStatus && (
            <div className="grid gap-4 md:grid-cols-3">
              {Object.entries(scraperStatus).map(([source, info]) => (
                <div key={source} className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold capitalize text-gray-900 dark:text-white">{source}</h3>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      info.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                    }`}>{info.status}</span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">{info.note}</p>
                  <button
                    onClick={() => triggerScraper(source)}
                    className="w-full py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Trigger Now
                  </button>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'users' && (
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Name</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Email</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Status</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Admin</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {users.map(user => (
                    <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="px-4 py-3 text-gray-900 dark:text-white">{user.name}</td>
                      <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{user.email}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                        }`}>{user.is_active ? 'Active' : 'Inactive'}</span>
                      </td>
                      <td className="px-4 py-3">
                        {user.is_admin && (
                          <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">Admin</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'reports' && (
            <div className="space-y-3">
              {reports.length === 0 ? (
                <p className="text-center py-8 text-gray-500 dark:text-gray-400">No reports to review.</p>
              ) : (
                reports.map(report => (
                  <div key={report.id} className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className={`px-2 py-0.5 text-xs rounded-full mr-2 ${
                          report.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                          report.status === 'reviewed' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{report.status}</span>
                        <span className="text-xs text-gray-500">{report.reason}</span>
                      </div>
                      <span className="text-xs text-gray-400">{new Date(report.created_at).toLocaleDateString()}</span>
                    </div>
                    {report.detail && <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">{report.detail}</p>}
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
