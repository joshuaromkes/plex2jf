import { useEffect, useState } from 'react';
import { Plus, Edit2, Trash2, TestTube, CheckCircle, XCircle } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { serversApi } from '../services/api';
import type { ServerConfig, ServerConfigCreate } from '../types';

interface ServerFormData {
  service_type: 'plex' | 'jellyfin' | 'seerr';
  name: string;
  url: string;
  api_key: string;
  token: string;
}

export function Servers() {
  const [servers, setServers] = useState<ServerConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingServer, setEditingServer] = useState<ServerConfig | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<ServerFormData>({
    service_type: 'plex',
    name: 'My Plex Server',
    url: 'http://localhost:32400',
    api_key: '',
    token: '',
  });

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const data = await serversApi.getAll();
      setServers(data);
    } catch (error) {
      console.error('Failed to load servers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async (id: number) => {
    try {
      setTestingId(id);
      await serversApi.test(id);
      await loadServers();
    } catch (error) {
      console.error('Test failed:', error);
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this server?')) return;
    
    try {
      await serversApi.delete(id);
      await loadServers();
    } catch (error) {
      console.error('Failed to delete server:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      // Auto-generate name if not provided
      const serverName = formData.name || `${formData.service_type.charAt(0).toUpperCase() + formData.service_type.slice(1)} Server (${formData.url})`;
      
      const data: ServerConfigCreate = {
        service_type: formData.service_type,
        name: serverName,
        url: formData.url,
        ...(formData.service_type === 'plex'
          ? { token: formData.token }
          : { api_key: formData.api_key }
        ),
      };

      let result;
      if (editingServer) {
        result = await serversApi.update(editingServer.id, data);
      } else {
        result = await serversApi.create(data);
      }
      
      // Check if we got a response with success: false, which means there was a handled error
      if (result && typeof result === 'object' && 'success' in result && result.success === false) {
        // Properly type the error response to avoid TypeScript errors
        const errorResponse = result as { success: false, error?: { message?: string } };
        console.error('Server operation failed:', errorResponse.error?.message);
        alert(errorResponse.error?.message || 'Failed to save server. Please check your inputs.');
        return;
      }
      
      setShowModal(false);
      setEditingServer(null);
      resetForm();
      await loadServers();
    } catch (error) {
      console.error('Failed to save server:', error);
      alert('Failed to save server. Check your inputs and try again.');
    }
  };

  const resetForm = () => {
    // Set proper defaults based on current service type
    const serviceType = formData.service_type || 'plex';
    
    const defaults: Record<'plex' | 'jellyfin' | 'seerr', {
      name: string;
      url: string;
      token: string;
      api_key: string;
    }> = {
      plex: {
        name: 'My Plex Server',
        url: 'http://localhost:32400',
        token: '',
        api_key: '',
      },
      jellyfin: {
        name: 'My Jellyfin Server',
        url: 'http://localhost:8096',
        token: '',
        api_key: '',
      },
      seerr: {
        name: 'My Seerr Server',
        url: 'http://localhost:5055',
        token: '',
        api_key: '',
      }
    };
    
    setFormData({
      service_type: serviceType as 'plex' | 'jellyfin' | 'seerr',
      ...defaults[serviceType as 'plex' | 'jellyfin' | 'seerr']
    });
  };

  const openEditModal = (server: ServerConfig) => {
    setEditingServer(server);
    setFormData({
      service_type: server.service_type,
      name: server.name,
      url: server.url,
      api_key: server.api_key || '',
      token: server.token || '',
    });
    setShowModal(true);
  };

  const openAddModal = () => {
    setEditingServer(null);
    resetForm();
    setShowModal(true);
  };

  const getServiceIcon = (type: string) => {
    switch (type) {
      case 'plex':
        return <span className="text-yellow-500 font-bold">P</span>;
      case 'jellyfin':
        return <span className="text-blue-500 font-bold">J</span>;
      case 'seerr':
        return <span className="text-purple-500 font-bold">S</span>;
      default:
        return <span className="text-gray-500 font-bold">?</span>;
    }
  };

  if (loading) {
    return (
      <PageWrapper title="Servers" description="Manage your media server connections">
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card h-32 animate-pulse bg-bg-tertiary" />
          ))}
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper 
      title="Servers" 
      description="Manage your media server connections"
      action={
        <button
          onClick={openAddModal}
          className="flex items-center gap-2 px-4 py-2 bg-accent-primary hover:bg-accent-hover text-white rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Server
        </button>
      }
    >
      {/* Server List */}
      <div className="space-y-6">
        {servers.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-text-secondary mb-4">No servers configured yet</p>
            <button
              onClick={openAddModal}
              className="px-4 py-2 bg-accent-primary hover:bg-accent-hover text-white rounded-lg transition-colors"
            >
              Add Your First Server
            </button>
          </div>
        ) : (
          servers.map((server) => (
            <div key={server.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-5">
                  <div className="w-12 h-12 bg-bg-tertiary rounded-lg flex items-center justify-center text-xl">
                    {getServiceIcon(server.service_type)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-text-primary capitalize">
                        {server.name}
                      </h3>
                      {server.last_test_status === 'success' ? (
                        <CheckCircle className="w-4 h-4 text-success" />
                      ) : server.last_test_status === 'failed' ? (
                        <XCircle className="w-4 h-4 text-error" />
                      ) : null}
                    </div>
                    <p className="text-text-secondary text-sm">{server.url}</p>
                    <p className="text-text-muted text-xs mt-1">
                      {server.api_key ? `API Key: ••••${server.api_key.slice(-4)}` :
                       server.token ? `Token: ••••${server.token.slice(-4)}` : 'No credentials'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTest(server.id)}
                    disabled={testingId === server.id}
                    className="p-2 text-text-secondary hover:text-info transition-colors"
                    title="Test Connection"
                  >
                    <TestTube className={`w-4 h-4 ${testingId === server.id ? 'animate-pulse' : ''}`} />
                  </button>
                  <button
                    onClick={() => openEditModal(server)}
                    className="p-2 text-text-secondary hover:text-text-primary transition-colors"
                    title="Edit"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(server.id)}
                    className="p-2 text-text-secondary hover:text-error transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-bg-secondary rounded-lg p-8 w-full max-w-md border border-bg-tertiary">
            <h2 className="text-xl font-bold text-text-primary mb-6">
              {editingServer ? 'Edit Server' : 'Add Server'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-text-secondary text-sm mb-1">Service Type</label>
                <select
                  value={formData.service_type}
                  onChange={(e) => {
                    const newType = e.target.value as 'plex' | 'jellyfin' | 'seerr';
                    
                    // Set proper defaults for the selected service
                    const defaults: Record<'plex' | 'jellyfin' | 'seerr', {
                      name: string;
                      url: string;
                      token: string;
                      api_key: string;
                    }> = {
                      plex: {
                        name: 'My Plex Server',
                        url: 'http://localhost:32400',
                        token: '',
                        api_key: '',
                      },
                      jellyfin: {
                        name: 'My Jellyfin Server',
                        url: 'http://localhost:8096',
                        token: '',
                        api_key: '',
                      },
                      seerr: {
                        name: 'My Seerr Server',
                        url: 'http://localhost:5055',
                        token: '',
                        api_key: '',
                      }
                    };
                    
                    setFormData({
                      service_type: newType,
                      ...defaults[newType]
                    });
                  }}
                  className="w-full"
                  disabled={!!editingServer}
                >
                  <option value="plex">Plex</option>
                  <option value="jellyfin">Jellyfin</option>
                  <option value="seerr">Seerr</option>
                </select>
              </div>
              <div>
                <label className="block text-text-secondary text-sm mb-1">
                  Name <span className="text-text-muted">(optional, auto-generated if empty)</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={`My ${formData.service_type.charAt(0).toUpperCase() + formData.service_type.slice(1)} Server`}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-text-secondary text-sm mb-1">URL</label>
                <input
                  type="url"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  placeholder={formData.service_type === 'plex' ? 'http://localhost:32400' : formData.service_type === 'jellyfin' ? 'http://localhost:8096' : 'http://localhost:5055'}
                  className="w-full"
                  required
                />
              </div>
              {formData.service_type === 'plex' ? (
                <div>
                  <label className="block text-text-secondary text-sm mb-1">Token</label>
                  <input
                    type="password"
                    value={formData.token}
                    onChange={(e) => setFormData({ ...formData, token: e.target.value })}
                    placeholder="Your Plex token"
                    className="w-full"
                    required
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-text-secondary text-sm mb-1">API Key</label>
                  <input
                    type="password"
                    value={formData.api_key}
                    onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                    placeholder="Your API key"
                    className="w-full"
                    required
                  />
                </div>
              )}
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
                  {editingServer ? 'Update' : 'Add'} Server
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </PageWrapper>
  );
}

export default Servers;