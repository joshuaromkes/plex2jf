import { useEffect, useState } from 'react';
import { RefreshCw, CheckCircle, Clock, AlertCircle, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { dashboardApi } from '../services/api';
import type { ActivityItem } from '../types';

export function Activity() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadActivity();
  }, [page, filter]);

  const loadActivity = async () => {
    try {
      setLoading(true);
      const status = filter === 'all' ? undefined : filter;
      const response = await dashboardApi.getActivity(page, 20, status);
      setItems(response.items);
      setTotalPages(response.pages);
    } catch (error) {
      console.error('Failed to load activity:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async (id: number) => {
    try {
      await dashboardApi.retryItem(id);
      await loadActivity();
    } catch (error) {
      console.error('Failed to retry item:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'synced':
        return <CheckCircle className="w-5 h-5 text-success" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-warning" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-error" />;
      default:
        return <Clock className="w-5 h-5 text-text-muted" />;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  if (loading && items.length === 0) {
    return (
      <PageWrapper title="Activity" description="View sync history and troubleshoot issues">
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card h-20 animate-pulse bg-bg-tertiary" />
          ))}
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper 
      title="Activity" 
      description="View sync history and troubleshoot issues"
      action={
        <button
          onClick={loadActivity}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-bg-tertiary hover:bg-bg-tertiary/80 text-text-primary rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      }
    >
      {/* Filter */}
      <div className="flex items-center gap-2 mb-6">
        <span className="text-text-secondary text-sm">Filter:</span>
        <select
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setPage(1);
          }}
          className="text-sm"
        >
          <option value="all">All</option>
          <option value="synced">Synced</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Activity List */}
      <div className="space-y-3">
        {items.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-text-secondary">No activity to display</p>
          </div>
        ) : (
          items.map((item) => (
            <div key={item.id} className="card">
              <div className="flex items-start gap-4">
                <div className="mt-1">{getStatusIcon(item.status)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-text-primary truncate">
                      {item.title}
                    </h3>
                    <span className="text-xs px-2 py-0.5 bg-bg-tertiary rounded text-text-secondary capitalize">
                      {item.media_type}
                    </span>
                  </div>
                  <p className="text-text-secondary text-sm mt-1">
                    {item.status === 'synced' && 'Favorited in Jellyfin'}
                    {item.status === 'pending' && 'Waiting to be processed'}
                    {item.status === 'failed' && (item.error || 'Failed to process')}
                  </p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-text-muted">
                    <span>User: {item.user}</span>
                    <span>Source: {item.source}</span>
                    <span>{formatDate(item.timestamp)}</span>
                  </div>
                </div>
                {item.status === 'failed' && (
                  <button
                    onClick={() => handleRetry(item.id)}
                    className="flex items-center gap-1 px-3 py-1 bg-bg-tertiary hover:bg-bg-tertiary/80 text-text-primary rounded text-sm transition-colors"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Retry
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-8">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="flex items-center gap-1 px-4 py-2 bg-bg-tertiary hover:bg-bg-tertiary/80 text-text-primary rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </button>
          <span className="text-text-secondary">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="flex items-center gap-1 px-4 py-2 bg-bg-tertiary hover:bg-bg-tertiary/80 text-text-primary rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </PageWrapper>
  );
}

export default Activity;