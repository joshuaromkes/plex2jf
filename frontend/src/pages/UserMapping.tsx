import { useEffect, useState } from 'react';
import { Plus, RefreshCw, Trash2, Users, AlertCircle } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { usersApi } from '../services/api';
import type { UserMapping, UserMappingCreate, ExternalUser } from '../types';

interface MappingFormData {
  plex_username: string;
  plex_user_id: string;
  jellyfin_user_id: string;
  seerr_user_id: string;
  is_active: boolean;
  notes: string;
}

export function UserMappingPage() {
  const [mappings, setMappings] = useState<UserMapping[]>([]);
  const [externalUsers, setExternalUsers] = useState<{
    plex: ExternalUser[];
    jellyfin: ExternalUser[];
    seerr: ExternalUser[];
  }>({ plex: [], jellyfin: [], seerr: [] });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState<MappingFormData>({
    plex_username: '',
    plex_user_id: '',
    jellyfin_user_id: '',
    seerr_user_id: '',
    is_active: true,
    notes: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [mappingsData, plexUsers, jellyfinUsers, seerrUsers] = await Promise.all([
        usersApi.getMappings(),
        usersApi.getPlexUsers().catch(() => []),
        usersApi.getJellyfinUsers().catch(() => []),
        usersApi.getSeerrUsers().catch(() => []),
      ]);
      setMappings(mappingsData);
      setExternalUsers({
        plex: plexUsers,
        jellyfin: jellyfinUsers,
        seerr: seerrUsers,
      });
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      await usersApi.syncUsers();
      await loadData();
    } catch (error) {
      console.error('Failed to sync users:', error);
      alert('Failed to sync users. Make sure servers are configured.');
    } finally {
      setSyncing(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this mapping?')) return;
    
    try {
      await usersApi.deleteMapping(id);
      await loadData();
    } catch (error) {
      console.error('Failed to delete mapping:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const data: UserMappingCreate = {
        plex_username: formData.plex_username,
        plex_user_id: formData.plex_user_id || undefined,
        jellyfin_user_id: formData.jellyfin_user_id,
        seerr_user_id: formData.seerr_user_id,
        is_active: formData.is_active,
        notes: formData.notes || undefined,
      };

      await usersApi.createMapping(data);
      setShowModal(false);
      resetForm();
      await loadData();
    } catch (error) {
      console.error('Failed to create mapping:', error);
      alert('Failed to create mapping. Please check your inputs.');
    }
  };

  const resetForm = () => {
    setFormData({
      plex_username: '',
      plex_user_id: '',
      jellyfin_user_id: '',
      seerr_user_id: '',
      is_active: true,
      notes: '',
    });
  };

  const openAddModal = () => {
    resetForm();
    setShowModal(true);
  };

  // Get unmapped users
  const mappedPlexUsers = new Set(mappings.map(m => m.plex_username));
  const mappedJellyfinUsers = new Set(mappings.map(m => m.jellyfin_user_id));
  const mappedSeerrUsers = new Set(mappings.map(m => m.seerr_user_id));

  const unmappedPlex = externalUsers.plex.filter(u => !mappedPlexUsers.has(u.username));
  const unmappedJellyfin = externalUsers.jellyfin.filter(u => !mappedJellyfinUsers.has(u.external_id));
  const unmappedSeerr = externalUsers.seerr.filter(u => !mappedSeerrUsers.has(u.external_id));

  if (loading) {
    return (
      <PageWrapper title="User Mapping" description="Map users between Plex, Jellyfin, and Seerr">
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card h-20 animate-pulse bg-bg-tertiary" />
          ))}
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper 
      title="User Mapping" 
      description="Map users between Plex, Jellyfin, and Seerr"
      action={
        <div className="flex gap-2">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 bg-bg-tertiary hover:bg-bg-tertiary/80 text-text-primary rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            Refresh Users
          </button>
          <button
            onClick={openAddModal}
            className="flex items-center gap-2 px-4 py-2 bg-accent-primary hover:bg-accent-hover text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Mapping
          </button>
        </div>
      }
    >
      {/* Help text */}
      {mappings.length === 0 && (
        <div className="card mb-6 bg-info/5 border-info/20">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-info mt-0.5" />
            <div>
              <h3 className="font-semibold text-text-primary">Getting Started</h3>
              <p className="text-text-secondary text-sm mt-1">
                First, click "Refresh Users" to fetch users from your configured servers. 
                Then create mappings to link Plex users with their Jellyfin and Seerr accounts.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Active Mappings */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Users className="w-5 h-5" />
          Active Mappings
          {mappings.length > 0 && (
            <span className="ml-2 text-sm font-normal text-text-muted">
              {mappings.length} user{mappings.length !== 1 ? 's' : ''} mapped
            </span>
          )}
        </h2>
        {mappings.length === 0 ? (
          <p className="text-text-secondary text-center py-8">No user mappings configured yet</p>
        ) : (
          <div className="space-y-3">
            {mappings.map((mapping) => (
              <div key={mapping.id} className="flex items-center justify-between p-4 bg-bg-tertiary rounded-lg">
                <div className="flex items-center gap-4 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="w-8 h-8 bg-yellow-500/20 text-yellow-500 rounded-full flex items-center justify-center text-xs font-bold">P</span>
                    <span className="text-text-primary font-medium">{mapping.plex_username}</span>
                  </div>
                  <span className="text-text-muted">→</span>
                  <div className="flex items-center gap-2">
                    <span className="w-8 h-8 bg-blue-500/20 text-blue-500 rounded-full flex items-center justify-center text-xs font-bold">J</span>
                    <span className="text-text-primary">{externalUsers.jellyfin.find(u => u.external_id === mapping.jellyfin_user_id)?.username || mapping.jellyfin_user_id}</span>
                  </div>
                  <span className="text-text-muted">→</span>
                  <div className="flex items-center gap-2">
                    <span className="w-8 h-8 bg-purple-500/20 text-purple-500 rounded-full flex items-center justify-center text-xs font-bold">S</span>
                    <span className="text-text-primary">{externalUsers.seerr.find(u => u.external_id === mapping.seerr_user_id)?.username || mapping.seerr_user_id}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(mapping.id)}
                  className="p-2 text-text-secondary hover:text-error transition-colors"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Unmapped Users */}
      {(unmappedPlex.length > 0 || unmappedJellyfin.length > 0 || unmappedSeerr.length > 0) && (
        <div className="card">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Unmapped Users</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <h3 className="text-sm font-medium text-text-secondary mb-2">Plex</h3>
              <div className="space-y-1">
                {unmappedPlex.map((user) => (
                  <div key={user.id} className="text-sm text-text-primary p-2 bg-bg-tertiary rounded">
                    {user.username}
                  </div>
                ))}
                {unmappedPlex.length === 0 && (
                  <p className="text-text-muted text-sm">All users mapped</p>
                )}
              </div>
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary mb-2">Jellyfin</h3>
              <div className="space-y-1">
                {unmappedJellyfin.map((user) => (
                  <div key={user.id} className="text-sm text-text-primary p-2 bg-bg-tertiary rounded">
                    {user.username}
                  </div>
                ))}
                {unmappedJellyfin.length === 0 && (
                  <p className="text-text-muted text-sm">All users mapped</p>
                )}
              </div>
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary mb-2">Seerr</h3>
              <div className="space-y-1">
                {unmappedSeerr.map((user) => (
                  <div key={user.id} className="text-sm text-text-primary p-2 bg-bg-tertiary rounded">
                    {user.username}
                  </div>
                ))}
                {unmappedSeerr.length === 0 && (
                  <p className="text-text-muted text-sm">All users mapped</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Mapping Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-bg-secondary rounded-lg p-6 w-full max-w-lg border border-bg-tertiary max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-text-primary mb-4">Add User Mapping</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-text-secondary text-sm mb-1">Plex User</label>
                <select
                  value={formData.plex_username}
                  onChange={(e) => {
                    const user = externalUsers.plex.find(u => u.username === e.target.value);
                    setFormData({ 
                      ...formData, 
                      plex_username: e.target.value,
                      plex_user_id: user?.external_id || ''
                    });
                  }}
                  className="w-full"
                  required
                >
                  <option value="">Select Plex user...</option>
                  {externalUsers.plex.map((user) => (
                    <option key={user.id} value={user.username}>{user.username}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-text-secondary text-sm mb-1">Jellyfin User</label>
                <select
                  value={formData.jellyfin_user_id}
                  onChange={(e) => setFormData({ ...formData, jellyfin_user_id: e.target.value })}
                  className="w-full"
                  required
                >
                  <option value="">Select Jellyfin user...</option>
                  {externalUsers.jellyfin.map((user) => (
                    <option key={user.id} value={user.external_id}>{user.username} (ID: {user.external_id})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-text-secondary text-sm mb-1">Seerr User</label>
                <select
                  value={formData.seerr_user_id}
                  onChange={(e) => setFormData({ ...formData, seerr_user_id: e.target.value })}
                  className="w-full"
                  required
                >
                  <option value="">Select Seerr user...</option>
                  {externalUsers.seerr.map((user) => (
                    <option key={user.id} value={user.external_id}>{user.username} (ID: {user.external_id})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-text-secondary text-sm mb-1">Notes (optional)</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Add any notes about this mapping..."
                  className="w-full"
                  rows={3}
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 bg-bg-tertiary hover:bg-bg-tertiary/80 text-text-primary rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-accent-primary hover:bg-accent-hover text-white rounded-lg transition-colors"
                >
                  Add Mapping
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </PageWrapper>
  );
}

export default UserMappingPage;