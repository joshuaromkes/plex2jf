import { useEffect, useState } from 'react';
import { Save, CheckCircle } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { settingsApi } from '../services/api';
import type { AppSettings } from '../types';

export function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await settingsApi.getAll();
      setSettings(data);
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!settings) return;
    
    try {
      setSaving(true);
      await settingsApi.update(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const updateSetting = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    if (!settings) return;
    setSettings({ ...settings, [key]: value });
  };

  if (loading) {
    return (
      <PageWrapper title="Settings" description="Configure sync behavior and system settings">
        <div className="card h-64 animate-pulse bg-bg-tertiary" />
      </PageWrapper>
    );
  }

  return (
    <PageWrapper 
      title="Settings" 
      description="Configure sync behavior and system settings"
      action={
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-accent-primary hover:bg-accent-hover text-white rounded-lg transition-colors disabled:opacity-50"
        >
          {saved ? (
            <>
              <CheckCircle className="w-4 h-4" />
              Saved!
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Settings'}
            </>
          )}
        </button>
      }
    >
      <div className="space-y-6">
        {/* Sync Features */}
        <div className="card">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Sync Features</h2>
          <div className="space-y-4">
            <div className="flex items-start justify-between p-4 bg-bg-tertiary rounded-lg">
              <div>
                <h3 className="font-medium text-text-primary">Plex Watchlist → Seerr + Jellyfin</h3>
                <p className="text-text-secondary text-sm mt-1">
                  Automatically create Seerr requests and favorite items in Jellyfin when users add to their Plex watchlist
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings?.sync_plex_watchlist ?? true}
                  onChange={(e) => updateSetting('sync_plex_watchlist', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-bg-primary peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent-primary"></div>
              </label>
            </div>

            <div className="flex items-start justify-between p-4 bg-bg-tertiary rounded-lg">
              <div>
                <h3 className="font-medium text-text-primary">Seerr Requests → Jellyfin Favorites</h3>
                <p className="text-text-secondary text-sm mt-1">
                  Automatically favorite items in Jellyfin when users make requests in Seerr
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings?.sync_seerr_requests ?? true}
                  onChange={(e) => updateSetting('sync_seerr_requests', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-bg-primary peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent-primary"></div>
              </label>
            </div>
          </div>
        </div>

        {/* Polling Settings */}
        <div className="card">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Polling</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-text-secondary text-sm mb-2">
                Polling Interval (seconds)
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="60"
                  max="3600"
                  step="60"
                  value={settings?.polling_interval ?? 300}
                  onChange={(e) => updateSetting('polling_interval', parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="text-text-primary font-medium w-24">
                  {settings?.polling_interval ?? 300}s
                </span>
              </div>
              <p className="text-text-muted text-xs mt-1">
                How often to check Plex watchlists for new items
              </p>
            </div>
          </div>
        </div>

        {/* Webhook Settings */}
        <div className="card">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Webhooks</h2>
          <div className="flex items-start justify-between p-4 bg-bg-tertiary rounded-lg">
            <div>
              <h3 className="font-medium text-text-primary">Enable Webhooks</h3>
              <p className="text-text-secondary text-sm mt-1">
                Receive real-time updates from Seerr via webhooks
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings?.webhook_enabled ?? true}
                onChange={(e) => updateSetting('webhook_enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-bg-primary peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent-primary"></div>
            </label>
          </div>
        </div>

        {/* Logging Settings */}
        <div className="card">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Logging</h2>
          <div>
            <label className="block text-text-secondary text-sm mb-2">Log Level</label>
            <select
              value={settings?.log_level ?? 'INFO'}
              onChange={(e) => updateSetting('log_level', e.target.value)}
              className="w-full max-w-xs"
            >
              <option value="DEBUG">Debug</option>
              <option value="INFO">Info</option>
              <option value="WARNING">Warning</option>
              <option value="ERROR">Error</option>
            </select>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

export default Settings;