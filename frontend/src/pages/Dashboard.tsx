import { useEffect, useState } from 'react';
import {
  Server,
  Users,
  CheckCircle,
  Clock,
  AlertCircle,
  RefreshCw,
  ListChecks,
  AlertTriangle
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
      {/* Stats Grid */}
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
          subtext={`${stats?.users_total || 0} total external users`}
        />
        <StatCard
          icon={CheckCircle}
          label="Items Synced"
          value={stats?.items_synced || 0}
          color="green"
        />
        <StatCard
          icon={Clock}
          label="Pending Items"
          value={stats?.items_pending || 0}
          color={stats?.items_pending ? 'yellow' : 'green'}
          subtext={stats?.items_failed ? `${stats.items_failed} failed` : undefined}
        />
      </div>

      {/* Seerr Request Sync Stats */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Seerr Request Sync</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={ListChecks}
            label="Total Requests"
            value={stats?.seerr_request?.total || 0}
            color="blue"
            subtext="Seerr requests tracked"
          />
          <StatCard
            icon={CheckCircle}
            label="Synced to Jellyfin"
            value={stats?.seerr_request?.synced || 0}
            color="green"
            subtext="Favorited in Jellyfin"
          />
          <StatCard
            icon={Clock}
            label="Pending"
            value={stats?.seerr_request?.pending || 0}
            color={stats?.seerr_request?.pending ? 'yellow' : 'green'}
            subtext="Waiting for library item"
          />
          <StatCard
            icon={AlertTriangle}
            label="Failed"
            value={stats?.seerr_request?.failed || 0}
            color={stats?.seerr_request?.failed ? 'red' : 'green'}
            subtext="Exceeded retry limit"
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

export default Dashboard;