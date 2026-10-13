// Login - demo-mode sign-in and OIDC redirect
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Card, Button, PageHeader } from '../components/ui';
import { LogIn, Cloud } from 'lucide-react';

export function Login() {
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleDemoLogin = async () => {
    await login();
    // In demo mode the demo user is always available; proceed to dashboard
    navigate('/');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12">
      <div className="w-full max-w-md space-y-6">
        <PageHeader
          title="Sign in"
          description="AI-powered cloud cost optimization"
        />
        <Card>
          <div className="flex items-center justify-center gap-2 mb-6">
            <Cloud className="h-6 w-6 text-blue-600" />
            <span className="text-xl font-bold text-gray-900">CloudCost</span>
          </div>
          <div className="space-y-3">
            <Button
              className="w-full"
              leftIcon={LogIn}
              onClick={handleDemoLogin}
              disabled={isLoading}
            >
              {isLoading ? 'Signing in…' : 'Continue in demo mode (localhost)'}
            </Button>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200 text-center">
            <p className="text-sm text-gray-500 mb-2">Production SSO</p>
            <a
              href="/api/auth/login"
              className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Sign in with Keycloak (OIDC)
            </a>
          </div>

          <p className="mt-4 text-xs text-gray-500">
            Demo mode signs you in as the built-in viewer/operator/admin user for local
            previews only. Configure a real Keycloak issuer for production.
          </p>
        </Card>
      </div>
    </div>
  );
}