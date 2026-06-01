/**
 * DICOM Tag Editor
 *
 * Searchable table of DICOM tags with inline editing.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Search, Save, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '../../utils/api';

interface DicomTag {
  vr: string;
  name: string;
  value: string | string[] | null;
}

interface DicomTagEditorProps {
  imageId: number | null;
}

const DicomTagEditor: React.FC<DicomTagEditorProps> = ({ imageId }) => {
  const [tags, setTags] = useState<Record<string, DicomTag>>({});
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [edits, setEdits] = useState<Record<string, string>>({});

  const fetchTags = useCallback(async () => {
    if (!imageId) return;
    setLoading(true);
    try {
      const params = search ? `?search=${encodeURIComponent(search)}` : '';
      const response = await apiClient.getDicomTags(imageId, search || undefined);
      setTags(response.tags);
    } catch {
      toast.error('Failed to load DICOM tags');
    } finally {
      setLoading(false);
    }
  }, [imageId, search]);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  const handleEdit = (tagKey: string, value: string) => {
    setEdits(prev => ({ ...prev, [tagKey]: value }));
  };

  const handleSave = async () => {
    if (!imageId || Object.keys(edits).length === 0) return;

    const tagUpdates = Object.entries(edits).map(([tag, value]) => ({ tag, value }));

    try {
      const response = await apiClient.updateDicomTags(imageId, tagUpdates);
      setTags(response.tags);
      setEdits({});
      toast.success('Tags updated successfully');
    } catch {
      toast.error('Failed to update tags');
    }
  };

  if (!imageId) {
    return (
      <div className="medical-card p-8 text-center">
        <AlertCircle className="w-12 h-12 text-slate-400 mx-auto mb-4" />
        <p className="text-slate-600 dark:text-slate-400">
          Select an image to edit its DICOM tags
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search + Save */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tags by name or ID..."
            className="w-full pl-10 pr-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm"
          />
        </div>
        {Object.keys(edits).length > 0 && (
          <button
            onClick={handleSave}
            className="medical-button-primary flex items-center gap-2 px-4 py-2"
          >
            <Save className="w-4 h-4" />
            Save ({Object.keys(edits).length})
          </button>
        )}
      </div>

      {/* Tags Table */}
      <div className="medical-card overflow-hidden">
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800 sticky top-0">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Tag</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Name</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-300">VR</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                    Loading tags...
                  </td>
                </tr>
              ) : Object.keys(tags).length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                    No tags found
                  </td>
                </tr>
              ) : (
                Object.entries(tags).map(([key, tag]) => (
                  <tr key={key} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="px-4 py-2 font-mono text-xs text-medical-600">
                      ({key.slice(0, 4)},{key.slice(4)})
                    </td>
                    <td className="px-4 py-2 text-slate-700 dark:text-slate-300">
                      {tag.name}
                    </td>
                    <td className="px-4 py-2 text-slate-500 font-mono text-xs">
                      {tag.vr}
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={edits[key] !== undefined ? edits[key] : String(tag.value ?? '')}
                        onChange={(e) => handleEdit(key, e.target.value)}
                        className="w-full px-2 py-1 border border-transparent hover:border-slate-300 dark:hover:border-slate-600 rounded text-sm bg-transparent focus:border-medical-500 focus:outline-none"
                      />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DicomTagEditor;
