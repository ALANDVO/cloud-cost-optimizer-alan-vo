// Settings - account and configuration
import { useAuth } from '../hooks/useAuth';
import { Card, Button, PageHeader } from '../components/ui';
import { User, LogOut, Shield, Info } from 'lucide-react';
import { formatDate } from '../utils/helpers';

export function Settings() {
  const { user, logout, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Settings" description="Loading account settings…" />
        <Card>Loading…</Card>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <div className="space-y-6">
        <PageHeader title="Settings" description="Authentication required" />
        <Card>
          <p className="text-sm text-gray-600">You must be signed in to view settings.</p>
        </Card>
      </div>
    );
  }

  const roles = user.roles ?? [];

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Account and application configuration" />

      <Card>
        <div className="flex items-center gap-4 mb-4">
          <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center">
            <User className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{user.name || user.email}</h3>
            <p className="text-sm text-gray-500">{user.email}</p>
          </div>
        </div>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          <div>
            <dt className="text-gray-500">Subject</dt>
            <dd className="text-gray-900 font-mono break-all">{user.sub}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Roles</dt>
            <dd className="text-gray-900">{roles.join(', ')}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Member since</dt>
            <dd className="text-gray-900">{user.created_at ? formatDate(user.created_at) : '—'}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Active</dt>
            <dd className="text-gray-900">{user.is_active ? 'Yes' : 'No'}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <Shield className="h-5 w-5" /> Authentication
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          This instance uses the configured OIDC / Keycloak provider. Session cookies are
          HttpOnly, SameSite, and require a CSRF token on state-changing requests.
        </p>
        <Button variant="secondary" leftIcon={LogOut} onClick={logout}>
          Sign out
        </Button>
      </Card>

      <Card>
        <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <Info className="h-5 w-5" /> About
        </h3>
        <p className="text-sm text-gray-500">
          Cloud Cost Optimizer analyzes AWS, GCP, and Azure spend for waste and right-sizing
          opportunities using deterministic offline heuristics, with optional LLM insights.
        </p>
      </Card>
    </div>
  );
}