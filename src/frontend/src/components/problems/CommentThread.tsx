'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { getComments, createComment } from '@/lib/api';

interface Comment {
  id: string;
  solution_id: string;
  user_id: string;
  parent_id: string | null;
  body: string;
  is_active: boolean;
  created_at: string;
  author_name?: string;
}

interface CommentThreadProps {
  solutionId: string;
}

export default function CommentThread({ solutionId }: CommentThreadProps) {
  const { data: session } = useSession();
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newComment, setNewComment] = useState('');
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    getComments(solutionId)
      .then(setComments)
      .catch(() => setComments([]))
      .finally(() => setLoading(false));
  }, [solutionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim() || !session) return;
    setSubmitting(true);
    try {
      const comment = await createComment(solutionId, newComment, replyTo);
      setComments(prev => [...prev, comment]);
      setNewComment('');
      setReplyTo(null);
      setShowForm(false);
    } catch {}
    setSubmitting(false);
  };

  const topLevel = comments.filter(c => !c.parent_id && c.is_active);
  const replies = (parentId: string) => comments.filter(c => c.parent_id === parentId && c.is_active);

  if (loading) return null;

  return (
    <div className="mt-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400">
          Comments ({comments.filter(c => c.is_active).length})
        </h4>
        {session && (
          <button
            onClick={() => { setShowForm(!showForm); setReplyTo(null); }}
            className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            {showForm ? 'Cancel' : '+ Add comment'}
          </button>
        )}
      </div>

      {showForm && session && (
        <form onSubmit={handleSubmit} className="space-y-2">
          {replyTo && (
            <p className="text-xs text-gray-500">
              Replying to comment{' '}
              <button type="button" onClick={() => setReplyTo(null)} className="text-blue-500">x</button>
            </p>
          )}
          <textarea
            value={newComment}
            onChange={e => setNewComment(e.target.value)}
            placeholder="Share your thoughts..."
            className="w-full p-2 text-sm border rounded-lg dark:bg-gray-800 dark:border-gray-600 resize-none"
            rows={3}
          />
          <button
            type="submit"
            disabled={submitting || !newComment.trim()}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50"
          >
            {submitting ? 'Posting...' : 'Post'}
          </button>
        </form>
      )}

      <div className="space-y-2">
        {topLevel.map(comment => (
          <div key={comment.id} className="space-y-1">
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  {comment.author_name || 'Anonymous'}
                </span>
                <span className="text-xs text-gray-400">
                  {new Date(comment.created_at).toLocaleDateString()}
                </span>
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">{comment.body}</p>
              {session && (
                <button
                  onClick={() => { setReplyTo(comment.id); setShowForm(true); }}
                  className="mt-1 text-xs text-blue-500 hover:text-blue-600"
                >
                  Reply
                </button>
              )}
            </div>
            {replies(comment.id).map(reply => (
              <div key={reply.id} className="ml-6 p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                    {reply.author_name || 'Anonymous'}
                  </span>
                  <span className="text-xs text-gray-400">
                    {new Date(reply.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">{reply.body}</p>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
