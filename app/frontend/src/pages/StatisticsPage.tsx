/**
 * Statistics Page - Phase 4 Enhanced Implementation
 *
 * Comprehensive statistics interface with:
 * - Analysis task statistics (existing)
 * - Study analytics: modality distribution, upload trends, storage usage
 * - Model performance metrics with failure rates
 * - User activity analytics
 * - Population-level insights
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { BarChart3, TrendingUp, Database, Users, Activity, PieChart } from 'lucide-react';
import {
  apiClient,
  StatisticsFilters,
  StatisticsTask,
  StatisticsAggregated,
  StudyAnalytics,
  ModelMetric,
  ModelTrend,
  UserActivity,
  PopulationInsights,
} from '../utils/api';
import {
  FilterPanel,
  TimeSeriesChart,
  StatusDistributionChart,
  ModelUsageChart,
  ExportButton,
  ModalityDistributionChart,
  UploadTrendsChart,
  StorageUsageChart,
  ModelPerformanceChart,
  ModelTrendsChart,
  UserActivityTable,
  MyActivityCard,
  PopulationInsightsPanel,
} from '../components/statistics';
import { useAuth } from '../contexts';

type TabType = 'analysis' | 'studies' | 'models' | 'users' | 'population';

export const StatisticsPage: React.FC = () => {
  const { t } = useTranslation('statistics');
  const { user } = useAuth();
  const isAdmin = user?.role === 0;

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('analysis');

  // Analysis statistics state (existing)
  const [filters, setFilters] = useState<StatisticsFilters>({
    date_from: null,
    date_to: null,
    model_keys: [],
    statuses: [],
    modalities: [],
    body_parts: [],
    patient_sex: [],
    patient_age_min: null,
    patient_age_max: null,
    page: 1,
    page_size: 50,
  });
  const [data, setData] = useState<StatisticsTask[]>([]);
  const [aggregatedData, setAggregatedData] = useState<StatisticsAggregated | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingCharts, setIsLoadingCharts] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  // Study analytics state (Item 1)
  const [studyAnalytics, setStudyAnalytics] = useState<StudyAnalytics | null>(null);
  const [studyPeriod, setStudyPeriod] = useState('daily');
  const [isLoadingStudies, setIsLoadingStudies] = useState(false);

  // Model metrics state (Item 2)
  const [modelMetrics, setModelMetrics] = useState<ModelMetric[]>([]);
  const [modelTrends, setModelTrends] = useState<ModelTrend[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  // User activity state (Item 3)
  const [userActivity, setUserActivity] = useState<UserActivity[]>([]);
  const [myActivity, setMyActivity] = useState<UserActivity | null>(null);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);

  // Population insights state (Item 4)
  const [populationData, setPopulationData] = useState<PopulationInsights | null>(null);
  const [isLoadingPopulation, setIsLoadingPopulation] = useState(false);

  // --- Fetch functions ---

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.getStatisticsData({
        ...filters,
        page: currentPage,
      });
      setData(response.results);
      setTotalCount(response.count);
    } catch (err) {
      console.error('Failed to fetch statistics:', err);
      setError(t('common:errors.loadFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAggregatedData = async () => {
    setIsLoadingCharts(true);
    try {
      const response = await apiClient.getStatisticsAggregated(filters, 'day');
      setAggregatedData(response);
    } catch (err) {
      console.error('Failed to fetch aggregated data:', err);
    } finally {
      setIsLoadingCharts(false);
    }
  };

  const fetchStudyAnalytics = async (period: string = studyPeriod) => {
    setIsLoadingStudies(true);
    try {
      const response = await apiClient.getStudyAnalytics(period);
      setStudyAnalytics(response);
    } catch (err) {
      console.error('Failed to fetch study analytics:', err);
    } finally {
      setIsLoadingStudies(false);
    }
  };

  const fetchModelMetrics = async () => {
    setIsLoadingModels(true);
    try {
      const [metrics, trends] = await Promise.all([
        apiClient.getModelMetrics(),
        apiClient.getModelTrends(),
      ]);
      setModelMetrics(metrics);
      setModelTrends(trends);
    } catch (err) {
      console.error('Failed to fetch model metrics:', err);
    } finally {
      setIsLoadingModels(false);
    }
  };

  const fetchUserActivity = async () => {
    setIsLoadingUsers(true);
    try {
      const myStats = await apiClient.getMyActivity();
      setMyActivity(myStats);
      if (isAdmin) {
        const allUsers = await apiClient.getUserActivity();
        setUserActivity(allUsers);
      }
    } catch (err) {
      console.error('Failed to fetch user activity:', err);
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const fetchPopulation = async () => {
    setIsLoadingPopulation(true);
    try {
      const response = await apiClient.getPopulationInsights();
      setPopulationData(response);
    } catch (err) {
      console.error('Failed to fetch population data:', err);
    } finally {
      setIsLoadingPopulation(false);
    }
  };

  // --- Effects ---

  useEffect(() => {
    fetchData();
  }, [currentPage]);

  useEffect(() => {
    fetchData();
    fetchAggregatedData();
  }, []);

  // Load tab data on tab change
  useEffect(() => {
    if (activeTab === 'studies' && !studyAnalytics) fetchStudyAnalytics();
    if (activeTab === 'models' && modelMetrics.length === 0) fetchModelMetrics();
    if (activeTab === 'users' && !myActivity) fetchUserActivity();
    if (activeTab === 'population' && !populationData) fetchPopulation();
  }, [activeTab]);

  const handleApplyFilters = () => {
    setCurrentPage(1);
    fetchData();
    fetchAggregatedData();
  };

  const handleResetFilters = () => {
    setFilters({
      date_from: null,
      date_to: null,
      model_keys: [],
      statuses: [],
      modalities: [],
      body_parts: [],
      patient_sex: [],
      patient_age_min: null,
      patient_age_max: null,
      page: 1,
      page_size: 50,
    });
    setCurrentPage(1);
  };

  const handleNextPage = () => {
    if (currentPage * (filters.page_size || 50) < totalCount) {
      setCurrentPage((prev) => prev + 1);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage((prev) => prev - 1);
    }
  };

  const totalPages = Math.ceil(totalCount / (filters.page_size || 50));

  const tabs: Array<{ key: TabType; label: string; icon: React.ElementType }> = [
    { key: 'analysis', label: t('tabs.analysisTasks'), icon: BarChart3 },
    { key: 'studies', label: t('tabs.studyAnalytics'), icon: Database },
    { key: 'models', label: t('tabs.modelPerformance'), icon: Activity },
    { key: 'users', label: t('tabs.userActivity'), icon: Users },
    { key: 'population', label: t('tabs.population'), icon: PieChart },
  ];

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Page Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <BarChart3 className="w-8 h-8 text-medical-500" />
              <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
                {t('title')}
              </h1>
            </div>
            <p className="text-slate-600 dark:text-slate-400">
              {t('subtitle')}
            </p>
          </div>
          {!isLoading && data.length > 0 && activeTab === 'analysis' && (
            <ExportButton data={data} filename="analysis_statistics" />
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="mb-6 border-b border-slate-200 dark:border-slate-700 overflow-x-auto">
        <nav className="flex gap-4 sm:gap-8 min-w-max">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`pb-4 px-2 font-medium transition-colors flex items-center gap-2 whitespace-nowrap ${
                  activeTab === tab.key
                    ? 'border-b-2 border-medical-500 text-medical-600 dark:text-medical-400'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* ========== Analysis Tasks Tab (existing) ========== */}
      {activeTab === 'analysis' && (
        <>
          <FilterPanel
            filters={filters}
            onFiltersChange={setFilters}
            onApply={handleApplyFilters}
            onReset={handleResetFilters}
          />

          {/* Summary Statistics */}
          {!isLoading && aggregatedData && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="medical-card p-4">
                <div className="text-sm text-slate-600 dark:text-slate-400 mb-1">{t('cards.totalTasks')}</div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">
                  {aggregatedData.total_tasks}
                </div>
              </div>
              <div className="medical-card p-4">
                <div className="text-sm text-slate-600 dark:text-slate-400 mb-1">{t('cards.completed')}</div>
                <div className="text-2xl font-bold text-success-600">
                  {aggregatedData.completed_tasks}
                  {aggregatedData.total_tasks > 0 && (
                    <span className="text-sm ml-2 text-slate-500">
                      ({((aggregatedData.completed_tasks / aggregatedData.total_tasks) * 100).toFixed(1)}%)
                    </span>
                  )}
                </div>
              </div>
              <div className="medical-card p-4">
                <div className="text-sm text-slate-600 dark:text-slate-400 mb-1">{t('cards.failed')}</div>
                <div className="text-2xl font-bold text-error-600">
                  {aggregatedData.failed_tasks}
                  {aggregatedData.total_tasks > 0 && (
                    <span className="text-sm ml-2 text-slate-500">
                      ({((aggregatedData.failed_tasks / aggregatedData.total_tasks) * 100).toFixed(1)}%)
                    </span>
                  )}
                </div>
              </div>
              <div className="medical-card p-4">
                <div className="text-sm text-slate-600 dark:text-slate-400 mb-1">{t('cards.avgProcessingTime')}</div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">
                  {aggregatedData.average_processing_time
                    ? t('seconds', { value: aggregatedData.average_processing_time.toFixed(1) })
                    : t('notAvailable')}
                </div>
              </div>
            </div>
          )}

          {/* Charts */}
          {!isLoadingCharts && aggregatedData && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {aggregatedData.time_series?.length > 0 && (
                <TimeSeriesChart
                  title={t('charts.tasksOverTime')}
                  data={aggregatedData.time_series.map((item) => ({
                    date: item.date,
                    value: item.count,
                  }))}
                  dataLabel={t('cards.totalTasks')}
                  lineColor="#0ea5e9"
                  height={300}
                  showGrid={true}
                  showLegend={false}
                />
              )}
              {aggregatedData.status_breakdown && Object.keys(aggregatedData.status_breakdown).length > 0 && (
                <StatusDistributionChart
                  title={t('charts.statusDistribution')}
                  data={aggregatedData.status_breakdown}
                  height={300}
                />
              )}
              {aggregatedData.model_usage?.length > 0 && (
                <div className="lg:col-span-2">
                  <ModelUsageChart
                    title={t('charts.modelUsage')}
                    data={aggregatedData.model_usage}
                    height={300}
                  />
                </div>
              )}
            </div>
          )}

          {/* Data Table */}
          <div className="medical-card p-6">
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-500"></div>
                <span className="ml-3 text-slate-600 dark:text-slate-400">{t('loading')}</span>
              </div>
            )}

            {error && !isLoading && (
              <div className="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
                <p className="text-error-700 dark:text-error-400">{error}</p>
              </div>
            )}

            {!isLoading && !error && totalCount === 0 && (
              <div className="text-center py-12">
                <BarChart3 className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-600 mb-4" />
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                  {t('noData')}
                </h3>
                <p className="text-slate-600 dark:text-slate-400">
                  {t('noDataMessage')}
                </p>
              </div>
            )}

            {!isLoading && !error && totalCount > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                    {t('tabs.analysisTasks')}
                  </h3>
                  <div className="text-sm text-slate-600 dark:text-slate-400">
                    {t('common:pagination.showing', { from: ((currentPage - 1) * (filters.page_size || 50)) + 1, to: Math.min(currentPage * (filters.page_size || 50), totalCount), total: totalCount })}
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-50 dark:bg-slate-800">
                      <tr>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('table.patientId')}</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('table.model')}</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('table.status')}</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('table.demographics')}</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('table.modality')}</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('table.bodyPart')}</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('table.created')}</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('table.duration')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                      {data.map((task) => (
                        <tr key={task.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                          <td className="py-3 px-4 text-sm text-slate-900 dark:text-white">{task.patient_id || t('notAvailable')}</td>
                          <td className="py-3 px-4">
                            <div className="text-sm text-slate-900 dark:text-white">{task.model_name}</div>
                            <div className="text-xs text-slate-500 dark:text-slate-400">{task.model_type}</div>
                          </td>
                          <td className="py-3 px-4">
                            <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                              task.status === 'COMPLETED'
                                ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400'
                                : task.status === 'FAILED'
                                ? 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400'
                                : 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400'
                            }`}>
                              {task.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                            {task.patient_sex || t('notAvailable')} / {task.patient_age ? `${task.patient_age}y` : t('notAvailable')}
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{task.modality || t('notAvailable')}</td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{task.body_part || t('notAvailable')}</td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{new Date(task.created_at).toLocaleDateString()}</td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                            {task.processing_duration ? t('seconds', { value: task.processing_duration.toFixed(1) }) : t('notAvailable')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
                    <button
                      onClick={handlePrevPage}
                      disabled={currentPage === 1}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        currentPage === 1
                          ? 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                          : 'bg-medical-500 hover:bg-medical-600 text-white'
                      }`}
                    >
                      {t('common:pagination.previous')}
                    </button>
                    <div className="text-sm text-slate-600 dark:text-slate-400">
                      {t('common:pagination.pageOf', { current: currentPage, total: totalPages })}
                    </div>
                    <button
                      onClick={handleNextPage}
                      disabled={currentPage >= totalPages}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        currentPage >= totalPages
                          ? 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                          : 'bg-medical-500 hover:bg-medical-600 text-white'
                      }`}
                    >
                      {t('common:pagination.next')}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* ========== Study Analytics Tab (Item 1) ========== */}
      {activeTab === 'studies' && (
        <div className="space-y-6">
          {isLoadingStudies ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-500"></div>
              <span className="ml-3 text-slate-600 dark:text-slate-400">{t('loading')}</span>
            </div>
          ) : studyAnalytics ? (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="medical-card p-4">
                  <div className="text-sm text-slate-600 dark:text-slate-400 mb-1">{t('study.totalStudies')}</div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-white">
                    {studyAnalytics.total_studies}
                  </div>
                </div>
                <div className="medical-card p-4">
                  <div className="text-sm text-slate-600 dark:text-slate-400 mb-1">{t('study.totalStorage')}</div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-white">
                    {(studyAnalytics.total_storage_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ModalityDistributionChart
                  title={t('charts.modalityDistribution')}
                  data={studyAnalytics.modality_distribution}
                  height={300}
                />
                <UploadTrendsChart
                  title={t('charts.uploadTrends')}
                  data={studyAnalytics.upload_trends}
                  height={300}
                  onPeriodChange={(period) => {
                    setStudyPeriod(period);
                    fetchStudyAnalytics(period);
                  }}
                />
              </div>
              <StorageUsageChart
                title={t('charts.storageUsage')}
                data={studyAnalytics.storage_usage}
                height={300}
              />
            </>
          ) : (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400">
              {t('noData')}
            </div>
          )}
        </div>
      )}

      {/* ========== Model Performance Tab (Item 2) ========== */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          {isLoadingModels ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-500"></div>
              <span className="ml-3 text-slate-600 dark:text-slate-400">{t('loading')}</span>
            </div>
          ) : (
            <>
              <ModelPerformanceChart
                title={t('tabs.modelPerformance')}
                data={modelMetrics}
                height={350}
              />
              <ModelTrendsChart
                title={t('tabs.modelPerformance')}
                data={modelTrends}
                height={300}
              />
              {/* Model metrics table */}
              {modelMetrics.length > 0 && (
                <div className="medical-card p-6">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                    {t('modelMetrics.title')}
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-slate-50 dark:bg-slate-800">
                        <tr>
                          <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('modelMetrics.model')}</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('modelMetrics.total')}</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('modelMetrics.completed')}</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('modelMetrics.failed')}</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('modelMetrics.failureRate')}</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">{t('modelMetrics.avgTime')}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                        {modelMetrics.map((m) => (
                          <tr key={m.model__key} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                            <td className="py-3 px-4 text-sm font-medium text-slate-900 dark:text-white">{m.model__name}</td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{m.total}</td>
                            <td className="py-3 px-4 text-sm text-success-600">{m.completed}</td>
                            <td className="py-3 px-4 text-sm text-error-600">{m.failed}</td>
                            <td className="py-3 px-4 text-sm">
                              <span className={m.failure_rate > 20 ? 'text-error-600' : m.failure_rate > 10 ? 'text-warning-600' : 'text-success-600'}>
                                {m.failure_rate}%
                              </span>
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                              {m.avg_processing_time ? t('seconds', { value: m.avg_processing_time }) : t('notAvailable')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ========== User Activity Tab (Item 3) ========== */}
      {activeTab === 'users' && (
        <div className="space-y-6">
          {isLoadingUsers ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-500"></div>
              <span className="ml-3 text-slate-600 dark:text-slate-400">{t('loading')}</span>
            </div>
          ) : (
            <>
              <MyActivityCard data={myActivity} />
              {isAdmin && userActivity.length > 0 && (
                <UserActivityTable data={userActivity} />
              )}
            </>
          )}
        </div>
      )}

      {/* ========== Population Insights Tab (Item 4) ========== */}
      {activeTab === 'population' && (
        <div>
          {isLoadingPopulation ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-500"></div>
              <span className="ml-3 text-slate-600 dark:text-slate-400">{t('loading')}</span>
            </div>
          ) : (
            <PopulationInsightsPanel data={populationData} />
          )}
        </div>
      )}
    </div>
  );
};

export default StatisticsPage;
