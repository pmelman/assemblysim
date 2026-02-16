import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { UserMenu } from '@/components/auth/UserMenu';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Silicon Citizens\' Assembly',
  description: 'AI-powered deliberative democracy simulation using GSS-derived personas',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthGuard>
          <div className="min-h-screen bg-background">
            <header className="border-b bg-card">
              <div className="container mx-auto px-4 py-4">
                <div className="flex items-center justify-between">
                  <a href="/" className="flex items-center space-x-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-5 w-5"
                      >
                        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                        <circle cx="9" cy="7" r="4" />
                        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                      </svg>
                    </div>
                    <span className="text-lg font-semibold">Silicon Citizens</span>
                  </a>
                  <nav className="flex items-center space-x-4">
                    <a
                      href="/"
                      className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Dashboard
                    </a>
                    <a
                      href="/assemblies/new"
                      className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                    >
                      New Assembly
                    </a>
                    <a
                      href="/citizens/custom"
                      className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Custom Citizens
                    </a>
                    <a
                      href="/settings"
                      className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Settings
                    </a>
                    <UserMenu />
                  </nav>
                </div>
              </div>
            </header>
            <main className="container mx-auto px-4 py-6">{children}</main>
          </div>
        </AuthGuard>
      </body>
    </html>
  );
}
