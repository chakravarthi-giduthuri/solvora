import { Metadata } from 'next';

interface ProfilePageProps {
  params: { username: string };
}

export async function generateMetadata({ params }: ProfilePageProps): Promise<Metadata> {
  return {
    title: `@${params.username} - Solvora`,
    description: `View ${params.username}'s profile on Solvora`,
  };
}

async function getProfileData(username: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/profiles/${username}`, {
      next: { revalidate: 120 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function ProfilePage({ params }: ProfilePageProps) {
  const profile = await getProfileData(params.username);

  if (!profile) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Profile not found</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">@{params.username} does not exist.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      {/* Profile Header */}
      <div className="flex items-start gap-4 mb-8">
        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold flex-shrink-0">
          {profile.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={profile.avatar_url} alt={profile.name} className="w-16 h-16 rounded-full object-cover" />
          ) : (
            profile.name?.[0]?.toUpperCase() || '?'
          )}
        </div>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{profile.name}</h1>
          <p className="text-gray-500 dark:text-gray-400">@{profile.username}</p>
          {profile.bio && (
            <p className="mt-2 text-gray-700 dark:text-gray-300">{profile.bio}</p>
          )}
          <p className="mt-1 text-xs text-gray-400">
            Joined {new Date(profile.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })}
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Problems Submitted', value: profile.stats?.submitted_count ?? 0 },
          { label: 'Bookmarks', value: profile.stats?.bookmark_count ?? 0 },
          { label: 'Votes Cast', value: profile.stats?.vote_count ?? 0 },
        ].map(stat => (
          <div key={stat.label} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl text-center">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Recent submissions */}
      {profile.recent_submissions?.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Recent Submissions</h2>
          <div className="space-y-2">
            {profile.recent_submissions.map((sub: { id: string; title: string; category?: string }) => (
              <a
                key={sub.id}
                href={`/problems/${sub.id}`}
                className="block p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
              >
                <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-1">{sub.title}</p>
                {sub.category && (
                  <span className="text-xs text-blue-600 dark:text-blue-400">{sub.category}</span>
                )}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
