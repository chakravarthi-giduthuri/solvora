'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { signOut, useSession } from 'next-auth/react';
import { Brain, Sun, Moon, LogOut, User, Bookmark, BarChart2, LayoutDashboard, Trophy, PlusCircle, Bell, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { SearchBar } from '@/components/ui/SearchBar';
import { useTheme } from './ThemeProvider';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/lib/utils';

const NAV_LINKS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/leaderboard', label: 'Leaderboard', icon: Trophy },
  { href: '/analytics', label: 'Analytics', icon: BarChart2 },
  { href: '/bookmarks', label: 'Bookmarks', icon: Bookmark },
] as const;

export function Navbar() {
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const { data: session } = useSession();
  const { user, isAuthenticated, clearAuth } = useAuthStore();

  const displayUser = session?.user ?? user;

  const handleLogout = async () => {
    clearAuth();
    await signOut({ callbackUrl: '/auth/login' });
  };

  const initials = displayUser?.name
    ? displayUser.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'U';

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center gap-4 px-4 sm:px-6">
        {/* Logo */}
        <Link
          href="/dashboard"
          className="flex items-center gap-2 font-bold text-lg shrink-0"
        >
          <Brain className="h-6 w-6 text-primary" aria-hidden="true" />
          <span className="hidden sm:inline">Solvora</span>
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-1 ml-2">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                pathname.startsWith(href)
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>

        {/* Global search */}
        <div className="flex-1 max-w-md mx-auto">
          <SearchBar />
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-2 ml-auto shrink-0">
          {/* Submit Problem button — visible when logged in */}
          {(displayUser || isAuthenticated) && (
            <Button asChild size="sm" variant="default" className="hidden sm:flex gap-1.5">
              <Link href="/problems/submit">
                <PlusCircle className="h-4 w-4" />
                Submit
              </Link>
            </Button>
          )}
          {/* Dark mode toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() =>
              setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
            }
            aria-label="Toggle theme"
          >
            {resolvedTheme === 'dark' ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </Button>

          {/* User menu or login */}
          {displayUser || isAuthenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="relative h-9 w-9 rounded-full"
                  aria-label="User menu"
                >
                  <Avatar className="h-9 w-9">
                    <AvatarImage
                      src={
                        (session?.user?.image ??
                          user?.avatarUrl) ||
                        undefined
                      }
                      alt={displayUser?.name ?? 'User'}
                    />
                    <AvatarFallback>{initials}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <p className="font-medium truncate">
                    {displayUser?.name ?? 'User'}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {displayUser?.email ?? ''}
                  </p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/problems/submit">
                    <PlusCircle className="mr-2 h-4 w-4" />
                    Submit Problem
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/bookmarks">
                    <Bookmark className="mr-2 h-4 w-4" />
                    Bookmarks
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/settings/notifications">
                    <Bell className="mr-2 h-4 w-4" />
                    Notifications
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/admin" className="text-purple-600 dark:text-purple-400">
                    <Shield className="mr-2 h-4 w-4" />
                    Admin Panel
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleLogout}
                  className="text-destructive focus:text-destructive"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button asChild size="sm">
              <Link href="/auth/login">
                <User className="mr-2 h-4 w-4" />
                Login
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* Mobile nav */}
      <nav className="flex md:hidden border-t px-4 py-2 gap-1 overflow-x-auto">
        {NAV_LINKS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0',
              pathname.startsWith(href)
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </Link>
        ))}
        {(displayUser || isAuthenticated) && (
          <Link
            href="/problems/submit"
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0',
              pathname === '/problems/submit'
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <PlusCircle className="h-4 w-4" aria-hidden="true" />
            Submit
          </Link>
        )}
      </nav>
    </header>
  );
}
