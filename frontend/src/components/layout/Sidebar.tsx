import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Server, 
  Users, 
  Settings, 
  Activity,
  Heart
} from 'lucide-react';
import { systemApi } from '../../services/api';

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
}

function NavItem({ to, icon, label }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors duration-200 ${
          isActive
            ? 'bg-accent-primary/10 text-accent-primary border-l-2 border-accent-primary'
            : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
        }`
      }
    >
      {icon}
      <span className="font-medium">{label}</span>
    </NavLink>
  );
}

export function Sidebar() {
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    systemApi.getInfo().then(info => setVersion(info.version)).catch(() => {});
  }, []);

  return (
    <aside className="w-60 bg-bg-secondary border-r border-bg-tertiary flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="p-6 border-b border-bg-tertiary">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-accent-primary rounded-lg flex items-center justify-center">
            <Heart className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-text-primary">plex2jf</h1>
            <p className="text-xs text-text-muted">Media Sync</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <NavItem
          to="/"
          icon={<LayoutDashboard className="w-5 h-5" />}
          label="Dashboard"
        />
        <NavItem
          to="/servers"
          icon={<Server className="w-5 h-5" />}
          label="Servers"
        />
        <NavItem
          to="/users"
          icon={<Users className="w-5 h-5" />}
          label="User Mapping"
        />
        <NavItem
          to="/activity"
          icon={<Activity className="w-5 h-5" />}
          label="Activity"
        />
        <NavItem
          to="/settings"
          icon={<Settings className="w-5 h-5" />}
          label="Settings"
        />
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-bg-tertiary">
        <p className="text-xs text-text-muted text-center">
          plex2jf v{version || '...'}
        </p>
      </div>
    </aside>
  );
}

export default Sidebar;
