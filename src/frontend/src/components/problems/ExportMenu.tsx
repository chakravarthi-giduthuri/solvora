'use client';

interface ExportMenuProps {
  problemId: string;
}

export default function ExportMenu({ problemId }: ExportMenuProps) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const handleExport = (format: 'markdown' | 'pdf') => {
    window.open(`${API_BASE}/problems/${problemId}/export?format=${format}`, '_blank');
  };

  return (
    <div className="relative group inline-block">
      <button className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
        Export &#9660;
      </button>
      <div className="hidden group-hover:block absolute right-0 mt-1 w-40 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-10">
        <button
          onClick={() => handleExport('markdown')}
          className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 rounded-t-lg"
        >
          Download Markdown
        </button>
        <button
          onClick={() => handleExport('pdf')}
          className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 rounded-b-lg"
        >
          Download PDF
        </button>
      </div>
    </div>
  );
}
