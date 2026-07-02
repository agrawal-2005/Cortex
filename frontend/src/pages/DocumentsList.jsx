import { useState, useEffect, useCallback } from 'react';
import { getDocuments } from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';

const PAGE_SIZE = 20;

const sourceTypeBadgeColors = {
  slack: 'bg-blue-100 text-blue-800',
  jira: 'bg-green-100 text-green-800',
  notion: 'bg-orange-100 text-orange-800',
  csv: 'bg-gray-100 text-gray-800',
  json: 'bg-gray-100 text-gray-800',
  upload: 'bg-purple-100 text-purple-800',
};

export default function DocumentsList() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const fetchDocuments = useCallback(async (currentSkip) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDocuments({ skip: currentSkip, limit: PAGE_SIZE });
      const data = res.data;
      let items = [];
      if (Array.isArray(data)) {
        items = data;
      } else if (data && Array.isArray(data.items)) {
        items = data.items;
      } else if (data && Array.isArray(data.documents)) {
        items = data.documents;
      }
      setDocuments(items);
      setHasMore(items.length === PAGE_SIZE);
    } catch (err) {
      setError('Failed to load documents.');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments(skip);
  }, [skip, fetchDocuments]);

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const getBadgeColor = (sourceType) => {
    const key = (sourceType || '').toLowerCase();
    return sourceTypeBadgeColors[key] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Documents</h1>

      {error && (
        <div className="mb-6 rounded-lg bg-red-50 p-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center min-h-[40vh]">
          <LoadingSpinner />
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg">No documents found.</p>
        </div>
      ) : (
        <>
          {/* Documents Table */}
          <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Content
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Channel / Project
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Author
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ingested At
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 max-w-xs truncate">
                      {doc.source_label || doc.content?.substring(0, 80) || 'No content'}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getBadgeColor(
                          doc.source_type
                        )}`}
                      >
                        {doc.source_type || 'unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {doc.channel_or_project || 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {doc.author_name || 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDate(doc.ingested_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-gray-200 pt-4 mt-4">
            <button
              onClick={() => setSkip((prev) => Math.max(0, prev - PAGE_SIZE))}
              disabled={skip === 0}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">
              Page {Math.floor(skip / PAGE_SIZE) + 1}
            </span>
            <button
              onClick={() => setSkip((prev) => prev + PAGE_SIZE)}
              disabled={!hasMore}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
