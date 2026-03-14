'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { getNotificationPrefs, updateNotificationPrefs } from '@/lib/api';
import { BackButton } from '@/components/ui/BackButton';

export default function NotificationSettingsPage() {
  const { data: session, status } = useSession();
  const [prefs, setPrefs] = useState({
    digest_enabled: false,
    digest_day: 1,
    digest_hour_utc: 8,
    category_interests: [] as string[],
    notify_on_comment: true,
    notify_on_vote: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const CATEGORIES = ['technology', 'programming', 'productivity', 'career', 'other'];

  useEffect(() => {
    if (session) {
      getNotificationPrefs()
        .then(setPrefs)
        .catch(() => {})
        .finally(() => setLoading(false));
    } else if (status !== 'loading') {
      setLoading(false);
    }
  }, [session, status]);

  const handleSave = async () => {
    if (!session) return;
    setSaving(true);
    try {
      await updateNotificationPrefs(prefs);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {}
    setSaving(false);
  };

  if (status === 'loading' || loading) return <div className="p-8 text-center">Loading...</div>;
  if (!session) return <div className="p-8 text-center text-gray-600">Please sign in to manage notifications.</div>;

  return (
    <div className="max-w-lg mx-auto p-6">
      <BackButton />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Notification Settings</h1>

      <div className="space-y-6">
        {/* Digest toggle */}
        <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div>
            <p className="font-medium text-gray-900 dark:text-white">Weekly Digest</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Receive a weekly email with top problems</p>
          </div>
          <button
            onClick={() => setPrefs(p => ({ ...p, digest_enabled: !p.digest_enabled }))}
            className={`w-12 h-6 rounded-full transition-colors ${prefs.digest_enabled ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}`}
          >
            <span className={`block w-5 h-5 bg-white rounded-full shadow transform transition-transform mx-0.5 ${prefs.digest_enabled ? 'translate-x-6' : 'translate-x-0'}`} />
          </button>
        </div>

        {prefs.digest_enabled && (
          <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 space-y-3">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Digest Day</label>
              <select
                value={prefs.digest_day}
                onChange={e => setPrefs(p => ({ ...p, digest_day: Number(e.target.value) }))}
                className="mt-1 w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
              >
                {DAYS.map((day, i) => (
                  <option key={i + 1} value={i + 1}>{day}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Send Time (UTC hour: {prefs.digest_hour_utc}:00)
              </label>
              <input
                type="range" min={0} max={23}
                value={prefs.digest_hour_utc}
                onChange={e => setPrefs(p => ({ ...p, digest_hour_utc: Number(e.target.value) }))}
                className="w-full mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Category Interests</label>
              <div className="flex flex-wrap gap-2">
                {CATEGORIES.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setPrefs(p => ({
                      ...p,
                      category_interests: p.category_interests.includes(cat)
                        ? p.category_interests.filter(c => c !== cat)
                        : [...p.category_interests, cat],
                    }))}
                    className={`px-3 py-1 text-sm rounded-full capitalize transition-colors ${
                      prefs.category_interests.includes(cat)
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Comment notifications */}
        <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div>
            <p className="font-medium text-gray-900 dark:text-white">Comment Notifications</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Get notified when someone replies</p>
          </div>
          <button
            onClick={() => setPrefs(p => ({ ...p, notify_on_comment: !p.notify_on_comment }))}
            className={`w-12 h-6 rounded-full transition-colors ${prefs.notify_on_comment ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}`}
          >
            <span className={`block w-5 h-5 bg-white rounded-full shadow transform transition-transform mx-0.5 ${prefs.notify_on_comment ? 'translate-x-6' : 'translate-x-0'}`} />
          </button>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-xl transition-colors"
        >
          {saved ? 'Saved!' : saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
