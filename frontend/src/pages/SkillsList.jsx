import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSkills, searchSkills } from '../api/client';
import ConfidenceBadge from '../components/ConfidenceBadge';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';

const PAGE_SIZE = 20;

export default function SkillsList() {
  const navigate = useNavigate();
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const fetchSkills = useCallback(async (currentSkip) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSkills({ skip: currentSkip, limit: PAGE_SIZE });
      const data = res.data;
      let items = [];
      if (Array.isArray(data)) {
        items = data;
      } else if (data && Array.isArray(data.items)) {
        items = data.items;
      } else if (data && Array.isArray(data.skills)) {
        items = data.skills;
      }
      setSkills(items);
      setHasMore(items.length === PAGE_SIZE);
      setIsSearching(false);
    } catch (err) {
      setError('Failed to load skills.');
      setSkills([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSkills(skip);
  }, [skip, fetchSkills]);

  const handleSearch = async () => {
    const trimmed = searchQuery.trim();
    if (!trimmed) {
      setSkip(0);
      fetchSkills(0);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await searchSkills(trimmed);
      const data = res.data;
      let items = [];
      if (Array.isArray(data)) {
        items = data;
      } else if (data && Array.isArray(data.items)) {
        items = data.items;
      } else if (data && Array.isArray(data.skills)) {
        items = data.skills;
      } else if (data && Array.isArray(data.results)) {
        items = data.results;
      }
      setSkills(items);
      setIsSearching(true);
      setHasMore(false);
    } catch (err) {
      setError('Search failed. Please try again.');
      setSkills([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  const truncate = (text, maxLen = 100) => {
    if (!text) return 'No description';
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Skills</h1>

      {/* Search Bar */}
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search skills..."
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
        <button
          onClick={handleSearch}
          className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          Search
        </button>
        {isSearching && (
          <button
            onClick={() => {
              setSearchQuery('');
              setSkip(0);
              fetchSkills(0);
            }}
            className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {error && (
        <div className="mb-6 rounded-lg bg-red-50 p-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center min-h-[40vh]">
          <LoadingSpinner />
        </div>
      ) : skills.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg">No skills found.</p>
          {isSearching && (
            <p className="text-gray-400 text-sm mt-2">
              Try a different search query.
            </p>
          )}
        </div>
      ) : (
        <>
          {/* Skills Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
            {skills.map((skill) => (
              <div
                key={skill.id}
                onClick={() => navigate(`/skills/${skill.id}`)}
                className="cursor-pointer rounded-lg border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-base font-semibold text-gray-900 truncate pr-2">
                    {skill.name}
                  </h3>
                  <StatusBadge status={skill.status} />
                </div>
                {skill.department && (
                  <p className="text-xs text-indigo-600 font-medium mb-1">
                    {skill.department}
                  </p>
                )}
                <p className="text-sm text-gray-500 mb-3">
                  {truncate(skill.description)}
                </p>
                <div className="flex items-center justify-between">
                  <ConfidenceBadge score={skill.confidence} />
                  <span className="text-xs text-gray-400">
                    {skill.steps?.length ?? 0} step
                    {(skill.steps?.length ?? 0) !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {!isSearching && (
            <div className="flex items-center justify-between border-t border-gray-200 pt-4">
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
          )}
        </>
      )}
    </div>
  );
}
