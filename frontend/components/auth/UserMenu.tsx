'use client';

import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

export function UserMenu() {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuthStore();

  if (!isAuthenticated || !user) {
    return null;
  }

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="flex items-center space-x-3">
      {user.is_admin && (
        <a
          href="/admin/invite-codes"
          className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          Invite Codes
        </a>
      )}
      <a
        href="/account"
        className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        {user.username}
      </a>
      <button
        onClick={handleLogout}
        className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        Sign out
      </button>
    </div>
  );
}
