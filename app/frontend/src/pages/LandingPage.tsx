import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Stethoscope,
  Brain,
  Zap,
  Shield,
  Award,
  ArrowRight,
  CheckCircle,
  Users,
  Clock,
  Target,
  TrendingUp,
  Star,
  PlayCircle,
} from 'lucide-react';

import { Button, Card, CardHeader, CardTitle, CardContent } from '../components/ui';
import { useAuth, useTheme } from '../contexts';

const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { isDark } = useTheme();
  const { t } = useTranslation(['landing', 'common']);

  return (
    <div className="min-h-screen bg-gradient-medical dark:bg-gradient-medical-dark">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-medical-50/90 to-teal-50/90 dark:from-slate-900/90 dark:to-slate-800/90 pointer-events-none" />

        <div className="relative container mx-auto px-4 py-20 lg:py-32">
          <div className="text-center max-w-4xl mx-auto">
            {/* Logo */}
            <div className="mx-auto w-20 h-20 bg-gradient-to-r from-medical-500 to-teal-500 rounded-full flex items-center justify-center mb-8 animate-fade-in">
              <Stethoscope className="w-10 h-10 text-white" />
            </div>

            {/* Main Headline */}
            <h1 className="text-5xl lg:text-7xl font-bold mb-6 animate-slide-up">
              <span className="medical-gradient-text">{t('landing:hero.titleLine1')}</span>
              <br />
              <span className="text-slate-900 dark:text-slate-100">
                {t('landing:hero.titleLine2')}
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-xl lg:text-2xl text-slate-600 dark:text-slate-300 mb-8 leading-relaxed animate-slide-up">
              {t('landing:hero.subtitle')}
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12 animate-slide-up">
              {isAuthenticated ? (
                <>
                  <Link to="/dashboard">
                    <Button variant="medical" size="xl" leftIcon={Brain}>
                      {t('landing:hero.openDashboard')}
                    </Button>
                  </Link>
                  <Link to="/analyze">
                    <Button variant="outline" size="xl" leftIcon={PlayCircle}>
                      {t('landing:hero.startAnalysis')}
                    </Button>
                  </Link>
                </>
              ) : (
                <>
                  <Link to="/auth/register">
                    <Button variant="medical" size="xl" leftIcon={ArrowRight}>
                      {t('landing:hero.getStarted')}
                    </Button>
                  </Link>
                  <Link to="/auth/login">
                    <Button variant="outline" size="xl" leftIcon={PlayCircle}>
                      {t('landing:hero.watchDemo')}
                    </Button>
                  </Link>
                </>
              )}
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center animate-fade-in">
              <div>
                <div className="text-3xl font-bold medical-gradient-text">99.2%</div>
                <div className="text-slate-600 dark:text-slate-400">{t('landing:stats.accuracy')}</div>
              </div>
              <div>
                <div className="text-3xl font-bold medical-gradient-text">50K+</div>
                <div className="text-slate-600 dark:text-slate-400">{t('landing:stats.imagesAnalyzed')}</div>
              </div>
              <div>
                <div className="text-3xl font-bold medical-gradient-text">&lt;2s</div>
                <div className="text-slate-600 dark:text-slate-400">{t('landing:stats.analysisTime')}</div>
              </div>
              <div>
                <div className="text-3xl font-bold medical-gradient-text">500+</div>
                <div className="text-slate-600 dark:text-slate-400">{t('landing:stats.healthcarePartners')}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white dark:bg-slate-900">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold medical-gradient-text mb-4">
              {t('landing:features.heading')}
            </h2>
            <p className="text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto">
              {t('landing:features.subtitle')}
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <Card variant="medical" className="group hover:shadow-medical-xl transition-all duration-300">
              <CardContent className="p-8">
                <div className="w-12 h-12 bg-medical-100 dark:bg-medical-900 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Brain className="w-6 h-6 text-medical-600 dark:text-medical-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3 text-slate-900 dark:text-slate-100">
                  {t('landing:features.multiModal')}
                </h3>
                <p className="text-slate-600 dark:text-slate-400 mb-4">
                  {t('landing:features.multiModalDesc')}
                </p>
                <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> X-ray Classification</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> CT Segmentation</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Ultrasound &amp; MRI Analysis</li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature 2 */}
            <Card variant="medical" className="group hover:shadow-medical-xl transition-all duration-300">
              <CardContent className="p-8">
                <div className="w-12 h-12 bg-teal-100 dark:bg-teal-900 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Zap className="w-6 h-6 text-teal-600 dark:text-teal-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3 text-slate-900 dark:text-slate-100">
                  {t('landing:features.realTime')}
                </h3>
                <p className="text-slate-600 dark:text-slate-400 mb-4">
                  {t('landing:features.realTimeDesc')}
                </p>
                <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Sub-second inference</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Batch processing</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Real-time monitoring</li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature 3 */}
            <Card variant="medical" className="group hover:shadow-medical-xl transition-all duration-300">
              <CardContent className="p-8">
                <div className="w-12 h-12 bg-success-100 dark:bg-success-900 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Shield className="w-6 h-6 text-success-600 dark:text-success-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3 text-slate-900 dark:text-slate-100">
                  {t('landing:features.hipaa')}
                </h3>
                <p className="text-slate-600 dark:text-slate-400 mb-4">
                  {t('landing:features.hipaaDesc')}
                </p>
                <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> End-to-end encryption</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Audit trails</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Owner-data privacy (GDPR)</li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature 4 */}
            <Card variant="medical" className="group hover:shadow-medical-xl transition-all duration-300">
              <CardContent className="p-8">
                <div className="w-12 h-12 bg-warning-100 dark:bg-warning-900 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Award className="w-6 h-6 text-warning-600 dark:text-warning-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3 text-slate-900 dark:text-slate-100">
                  {t('landing:features.clinical')}
                </h3>
                <p className="text-slate-600 dark:text-slate-400 mb-4">
                  {t('landing:features.clinicalDesc')}
                </p>
                <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Validated datasets</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Peer reviewed</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Reproducible metrics</li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature 5 */}
            <Card variant="medical" className="group hover:shadow-medical-xl transition-all duration-300">
              <CardContent className="p-8">
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Target className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3 text-slate-900 dark:text-slate-100">
                  {t('landing:features.precision')}
                </h3>
                <p className="text-slate-600 dark:text-slate-400 mb-4">
                  {t('landing:features.precisionDesc')}
                </p>
                <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Patient-specific</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Risk stratification</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Treatment guidance</li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature 6 */}
            <Card variant="medical" className="group hover:shadow-medical-xl transition-all duration-300">
              <CardContent className="p-8">
                <div className="w-12 h-12 bg-indigo-100 dark:bg-indigo-900 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <TrendingUp className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3 text-slate-900 dark:text-slate-100">
                  {t('landing:features.continuousLearning')}
                </h3>
                <p className="text-slate-600 dark:text-slate-400 mb-4">
                  {t('landing:features.continuousLearningDesc')}
                </p>
                <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Active learning</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Model updates</li>
                  <li className="flex items-center"><CheckCircle className="w-4 h-4 text-success-500 mr-2" /> Performance tracking</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-20 bg-slate-50 dark:bg-slate-800">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold medical-gradient-text mb-4">
              {t('landing:useCases.heading')}
            </h2>
            <p className="text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto">
              {t('landing:cta.subtitle')}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 mb-16">
            <div className="text-center">
              <div className="w-16 h-16 bg-medical-100 dark:bg-medical-900 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-medical-600 dark:text-medical-400" />
              </div>
              <h3 className="text-2xl font-semibold mb-2 text-slate-900 dark:text-slate-100">{t('landing:useCases.radiologists')}</h3>
              <p className="text-slate-600 dark:text-slate-400">{t('landing:useCases.radiologistsDesc')}</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-teal-100 dark:bg-teal-900 rounded-full flex items-center justify-center mx-auto mb-4">
                <Clock className="w-8 h-8 text-teal-600 dark:text-teal-400" />
              </div>
              <h3 className="text-2xl font-semibold mb-2 text-slate-900 dark:text-slate-100">{t('landing:useCases.emergency')}</h3>
              <p className="text-slate-600 dark:text-slate-400">{t('landing:useCases.emergencyDesc')}</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-success-100 dark:bg-success-900 rounded-full flex items-center justify-center mx-auto mb-4">
                <Brain className="w-8 h-8 text-success-600 dark:text-success-400" />
              </div>
              <h3 className="text-2xl font-semibold mb-2 text-slate-900 dark:text-slate-100">{t('landing:useCases.researchers')}</h3>
              <p className="text-slate-600 dark:text-slate-400">{t('landing:useCases.researchersDesc')}</p>
            </div>
          </div>

          {/* Testimonials */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {([1, 2, 3] as const).map((i) => (
              <Card key={i} variant="glass" className="p-6">
                <div className="flex items-center mb-4">
                  <div className="flex space-x-1">
                    {[1,2,3,4,5].map((star) => (
                      <Star key={star} className="w-4 h-4 text-warning-500 fill-current" />
                    ))}
                  </div>
                </div>
                <p className="text-slate-600 dark:text-slate-300 mb-4 italic">
                  "{t(`landing:testimonials.quote${i}`)}"
                </p>
                <div className="text-sm">
                  <div className="font-semibold text-slate-900 dark:text-slate-100">{t(`landing:testimonials.author${i}`)}</div>
                  <div className="text-slate-500 dark:text-slate-400">{t(`landing:testimonials.position${i}`)}</div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-medical-600 to-teal-600">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold text-white mb-4">
            {t('landing:cta.heading')}
          </h2>
          <p className="text-xl text-medical-100 mb-8 max-w-2xl mx-auto">
            {t('landing:cta.subtitle')}
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            {!isAuthenticated && (
              <>
                <Link to="/auth/register">
                  <Button variant="secondary" size="xl" leftIcon={ArrowRight}>
                    {t('landing:cta.startTrial')}
                  </Button>
                </Link>
                <Link to="/contact">
                  <Button variant="ghost" size="xl" className="text-white border-white hover:bg-white hover:text-medical-600">
                    {t('landing:cta.contactSales')}
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-300">
        <div className="container mx-auto px-4 py-16">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center mb-4">
                <div className="w-8 h-8 bg-medical-500 rounded-lg flex items-center justify-center mr-3">
                  <Stethoscope className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold text-white">{t('common:footer.tagline')}</span>
              </div>
              <p className="text-slate-400 mb-4">
                {t('common:footer.compliance')}
              </p>
              <div className="text-sm text-slate-500">
                {t('common:footer.allRightsReserved', { year: new Date().getFullYear() })}
              </div>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">{t('common:footer.platform')}</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/features" className="hover:text-medical-400">{t('common:footer.features')}</Link></li>
                <li><Link to="/pricing" className="hover:text-medical-400">{t('common:footer.pricing')}</Link></li>
                <li><Link to="/security" className="hover:text-medical-400">{t('common:footer.security')}</Link></li>
                <li><Link to="/api" className="hover:text-medical-400">{t('common:footer.apiRef')}</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">{t('common:footer.resources')}</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/docs" className="hover:text-medical-400">{t('common:footer.docs')}</Link></li>
                <li><Link to="/research" className="hover:text-medical-400">{t('common:footer.research')}</Link></li>
                <li><Link to="/blog" className="hover:text-medical-400">{t('common:footer.blog')}</Link></li>
                <li><Link to="/support" className="hover:text-medical-400">{t('auth:login.support')}</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">{t('common:footer.company')}</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/about" className="hover:text-medical-400">{t('common:footer.about')}</Link></li>
                <li><Link to="/careers" className="hover:text-medical-400">{t('common:footer.careers')}</Link></li>
                <li><Link to="/privacy" className="hover:text-medical-400">{t('auth:login.privacy')}</Link></li>
                <li><Link to="/terms" className="hover:text-medical-400">{t('auth:login.terms')}</Link></li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;