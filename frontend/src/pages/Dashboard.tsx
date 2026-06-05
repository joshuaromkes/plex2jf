import { useEffect, useState } from 'react';
import {
  Server,
  Users,
  CheckCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  ListChecks,
  Heart,
  AlertCircle,
} from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { dashboardApi, systemApi } from '../services/api';
import type { DashboardStats, HealthStatus } from '../types';

function StatCard({ 
  icon: Icon, 
  label, 
  value, 
  color = 'blue',
  subtext
}: { 
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  color?: 'blue' | 'green' | 'yellow' | 'red';
  subtext?: string;
}) {
  const colorClasses = {
    blue: 'bg-info/10 text-info',
    green: 'bg-success/10 text-success',
    yellow: 'bg-warning/10 text-warning',
    red: 'bg-error/10 text-error',
  };

  return (
    <div className="card flex items-center gap-4">
      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-text-secondary text-sm">{label}</p>
        <p className="text-2xl font-bold text-text-primary">{value}</p>
        {subtext && <p className="text-text-muted text-xs">{subtext}</p>}
      </div>
    </div>
  );
}

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, healthData] = await Promise.all([
        dashboardApi.getStats(),
        systemApi.getHealth(),
      ]);
      setStats(statsData);
      setHealth(healthData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleManualSync = async () => {
    try {
      setSyncing(true);
      await dashboardApi.triggerSync();
      await loadData();
    } catch (error) {
      console.error('Failed to trigger sync:', error);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <PageWrapper title="Dashboard" description="Overview of your plex2jf instance">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card h-24 animate-pulse bg-bg-tertiary" />
          ))}
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper 
      title="Dashboard" 
      description="Overview of your plex2jf instance"
      action={
        <div className="flex items-center gap-4">
          {stats?.last_sync && (
            <span className="text-xs text-text-muted">
              Last sync: {new Date(stats.last_sync).toLocaleString()}
            </span>
          )}
          <button
            onClick={handleManualSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 bg-accent-primary hover:bg-accent-hover text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing...' : 'Manual Sync'}
          </button>
        </div>
      }
    >
      {/* Top Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Server}
          label="Servers Connected"
          value={`${stats?.servers_connected || 0}/${stats?.servers_total || 0}`}
          color={stats?.servers_connected === stats?.servers_total ? 'green' : 'yellow'}
          subtext={health?.status === 'healthy' ? 'All systems operational' : 'Some issues detected'}
        />
        <StatCard
          icon={Users}
          label="Users Mapped"
          value={stats?.users_mapped || 0}
          color="blue"
          subtext={`${stats?.users_total || 0} total across all services`}
        />
        <StatCard
          icon={Heart}
          label="Favorites Synced"
          value={stats?.favorites?.synced || 0}
          color="green"
          subtext="Items favorited in Jellyfin"
        />
        <StatCard
          icon={Clock}
          label="Awaiting Library"
          value={stats?.favorites?.pending || 0}
          color={stats?.favorites?.pending ? 'yellow' : 'green'}
          subtext={stats?.favorites?.failed ? `${stats.favorites.failed} failed` : 'Not yet in Jellyfin'}
        />
      </div>

      {/* Watchlist → Seerr */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Watchlist → Seerr</h2>
        <p className="text-sm text-text-muted mb-4">
          Plex watchlist items that became Seerr requests. When someone adds to their Plex watchlist, plex2jf creates a matching request in Seerr.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={ListChecks}
            label="Total Created"
            value={stats?.watchlist_to_seerr?.total || 0}
            color="blue"
            subtext="Watchlist → Seerr requests"
          />
          <StatCard
            icon={CheckCircle}
            label="Requested"
            value={stats?.watchlist_to_seerr?.synced || 0}
            color="green"
            subtext="Successfully created in Seerr"
          />
          <StatCard
            icon={Clock}
            label="Pending"
            value={stats?.watchlist_to_seerr?.pending || 0}
            color={stats?.watchlist_to_seerr?.pending ? 'yellow' : 'green'}
            subtext="Waiting to be requested"
          />
          <StatCard
            icon={AlertTriangle}
            label="Failed"
            value={stats?.watchlist_to_seerr?.failed || 0}
            color={stats?.watchlist_to_seerr?.failed ? 'red' : 'green'}
            subtext="Could not create request"
          />
        </div>
      </div>

      {/* Favorites (Seerr → Jellyfin) */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Favorites</h2>
        <p className="text-sm text-text-muted mb-4">
          Seerr requests that have been favorited in Jellyfin. Covers both mapped users (with a Plex profile) and unmapped users (matched by username).
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={ListChecks}
            label="Total Tracked"
            value={stats?.favorites?.total || 0}
            color="blue"
            subtext="All Seerr→Jellyfin items"
          />
          <StatCard
            icon={Heart}
            label="Favorited"
            value={stats?.favorites?.synced || 0}
            color="green"
            subtext="Successfully favorited"
          />
          <StatCard
            icon={Clock}
            label="Awaiting Library"
            value={stats?.favorites?.pending || 0}
            color={stats?.favorites?.pending ? 'yellow' : 'green'}
            subtext="Not yet in Jellyfin library"
          />
          <StatCard
            icon={AlertTriangle}
            label="Failed"
            value={stats?.favorites?.failed || 0}
            color={stats?.favorites?.failed ? 'red' : 'green'}
            subtext="Exceeded retry attempts"
          />
        </div>
      </div>

      {/* Server Status */}
      <div className="card">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Server Status</h2>
        <div className="space-y-3">
          {health?.servers && Object.entries(health.servers).map(([service, status]) => (
            <div key={service} className="flex items-center justify-between p-3 bg-bg-tertiary rounded-lg">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${status.connected ? 'bg-success' : 'bg-error'}`} />
                <span className="capitalize text-text-primary">{service}</span>
              </div>
              <span className={`text-sm ${status.connected ? 'text-success' : 'text-error'}`}>
                {status.connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          ))}
          {(!health?.servers || Object.keys(health.servers).length === 0) && (
            <div className="flex items-center gap-3 p-3 bg-bg-tertiary rounded-lg">
              <AlertCircle className="w-5 h-5 text-warning" />
              <span className="text-text-secondary">No servers configured yet. Go to Servers page to set up.</span>
            </div>
          )}
        </div>
      </div>
    </PageWrapper>
  );
}
