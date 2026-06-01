/**
 * AI Toolbar Button
 *
 * Button to trigger AI analysis directly from the viewer.
 * Shows in the viewer toolbar when a study is loaded.
 */

import React, { useState } from 'react';
import { Brain, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

interface AIToolbarButtonProps {
  studyInstanceUID: string;
  disabled?: boolean;
}

export const AIToolbarButton: React.FC<AIToolbarButtonProps> = ({
  studyInstanceUID,
  disabled = false,
}) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleAnalyze = () => {
    setLoading(true);
    toast.success('Redirecting to analysis...');
    navigate(`/analyze?study=${studyInstanceUID}`);
  };

  return (
    <button
      onClick={handleAnalyze}
      disabled={disabled || loading}
      className="flex items-center gap-2 px-3 py-2 bg-medical-500 hover:bg-medical-600 disabled:bg-slate-600 text-white rounded-lg text-sm font-medium transition-colors"
      title="Analyze with AI"
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Brain className="w-4 h-4" />
      )}
      <span className="hidden lg:inline">Analyze</span>
    </button>
  );
};

export default AIToolbarButton;
