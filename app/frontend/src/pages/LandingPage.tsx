import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Heart,
  ArrowRight,
  ShieldCheck,
  PawPrint,
  Lock,
  CheckCircle2,
  Network,
  TrendingUp,
  Stethoscope,
  Check,
  Users,
  Search,
  Share2,
  Sparkles,
  BadgeCheck,
  Image as ImageIcon,
  Star,
} from 'lucide-react';

import { useAuth, useLanguage } from '../contexts';

/* -------------------------------------------------------------------------- */
/*  Assets — Unsplash placeholders (replace with licensed/own photos in prod) */
/*  and the in-repo stylised radiograph (swap for a real Cornerstone render). */
/* -------------------------------------------------------------------------- */
const HERO_IMG =
  'https://images.unsplash.com/photo-1770836037289-e00e5f351d11?auto=format&fit=crop&w=1000&q=72';
const OWNER_IMG =
  'https://images.unsplash.com/photo-1728013274420-ed02b1f58887?auto=format&fit=crop&w=900&q=72';
const OWNER_AVATAR =
  'https://images.unsplash.com/photo-1630438994394-3deff7a591bf?auto=format&fit=crop&w=120&q=70';
const TESTIMONIAL_AVATAR =
  'https://images.unsplash.com/photo-1770836037949-c5e8db65aa86?auto=format&fit=crop&w=120&q=70';
const RADIOGRAPH = '/assets/radiograph-thorax.webp';

const CONTAINER = 'mx-auto max-w-[1200px] px-6 sm:px-8';
const PRIMARY_BTN =
  'inline-flex items-center gap-2.5 rounded-[13px] bg-gradient-to-br from-[#13B886] to-brand-deep px-6 py-[15px] text-base font-semibold text-white shadow-[0_12px_26px_rgba(12,138,107,0.30)] transition-all hover:-translate-y-0.5 hover:shadow-[0_16px_32px_rgba(12,138,107,0.36)]';

/** Newsreader-italic "eyebrow" used above section headings */
const Eyebrow: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = 'text-peach',
}) => (
  <span className={`font-serif-accent text-[19px] italic ${className}`}>{children}</span>
);

/** Compact in-header language switch (flags) — keeps i18n on the public page */
const LanguageFlags: React.FC = () => {
  const { currentLanguage, setLanguage, languages } = useLanguage();
  return (
    <div className="flex items-center gap-1">
      {languages.map((lang) => (
        <button
          key={lang.code}
          type="button"
          onClick={() => setLanguage(lang.code)}
          aria-label={lang.name}
          aria-pressed={currentLanguage === lang.code}
          className={`rounded-md px-1.5 py-1 text-base leading-none transition-opacity ${
            currentLanguage === lang.code ? 'opacity-100' : 'opacity-45 hover:opacity-80'
          }`}
        >
          {lang.flag}
        </button>
      ))}
    </div>
  );
};

const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { t } = useTranslation('landing');

  // Authenticated visitors get straight-to-app CTAs; everyone else converts.
  const demoTarget = isAuthenticated ? '/dashboard' : '/auth/register';

  return (
    <div className="min-h-screen scroll-smooth bg-cream font-public text-forest-ink2 antialiased [overflow-x:hidden]">
      {/* ----------------------------------------------------------------- */}
      {/* HEADER                                                            */}
      {/* ----------------------------------------------------------------- */}
      <header className="sticky top-0 z-40 border-b border-[#ECE6DA] bg-cream/80 backdrop-blur-[14px]">
        <div className={`${CONTAINER} flex items-center gap-8 py-4`}>
          <Link to="/" className="flex items-center gap-[11px] text-forest-ink2">
            <span className="flex h-[38px] w-[38px] items-center justify-center rounded-[11px] bg-gradient-to-br from-[#13B886] to-brand-deep shadow-[0_6px_16px_rgba(12,138,107,0.28)]">
              <PawPrint className="h-[21px] w-[21px] text-white" strokeWidth={2} />
            </span>
            <span className="font-display text-[21px] font-bold tracking-[-0.02em]">VetImage</span>
          </Link>

          <nav className="ml-auto flex items-center gap-6 text-[15px] font-medium text-[#46544F] sm:gap-7">
            <a href="#care" className="hidden hover:text-brand-text lg:inline">
              {t('header.forClinics')}
            </a>
            <a href="#owners" className="hidden hover:text-brand-text lg:inline">
              {t('header.forOwners')}
            </a>
            <a href="#viewer" className="hidden hover:text-brand-text lg:inline">
              {t('header.platform')}
            </a>
            <LanguageFlags />
            <Link
              to={isAuthenticated ? '/dashboard' : '/auth/login'}
              className="font-semibold text-forest-ink2 hover:text-brand-text"
            >
              {t('header.signIn')}
            </Link>
            <a
              href="#demo"
              className="rounded-[11px] bg-gradient-to-br from-[#13B886] to-brand-deep px-5 py-[11px] font-semibold text-white shadow-[0_8px_18px_rgba(12,138,107,0.26)] transition-all hover:-translate-y-px hover:brightness-105"
            >
              {t('header.bookDemo')}
            </a>
          </nav>
        </div>
      </header>

      {/* ----------------------------------------------------------------- */}
      {/* HERO                                                              */}
      {/* ----------------------------------------------------------------- */}
      <section
        className={`${CONTAINER} grid grid-cols-1 items-center gap-12 pb-10 pt-16 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14`}
      >
        <div className="motion-safe:animate-vfade">
          <div className="mb-6 inline-flex items-center gap-2.5 rounded-full border border-brand-mintborder bg-brand-mint px-3.5 py-[7px] text-[13.5px] font-semibold text-brand-text">
            <Heart className="h-[15px] w-[15px]" strokeWidth={2.2} />
            {t('hero.badge')}
          </div>
          <h1 className="mb-[22px] font-display text-[40px] font-bold leading-[1.04] tracking-[-0.03em] text-forest-ink sm:text-[48px] lg:text-[58px]">
            {t('hero.titleBefore')}{' '}
            <span className="font-serif-accent font-medium italic text-brand">
              {t('hero.titleAccent')}
            </span>
          </h1>
          <p className="mb-8 max-w-[480px] text-[19px] leading-[1.6] text-[#56655F]">
            {t('hero.subtitle')}
          </p>
          <div className="mb-[30px] flex flex-wrap items-center gap-3.5">
            <Link to={demoTarget} className={PRIMARY_BTN}>
              {t('hero.bookDemo')}
              <ArrowRight className="h-[18px] w-[18px]" strokeWidth={2.2} />
            </Link>
            <a
              href="#owners"
              className="inline-flex items-center gap-2.5 rounded-[13px] border border-[#E4DCCE] bg-white px-6 py-[15px] text-base font-semibold text-forest-ink2 transition-colors hover:border-[#13B886] hover:text-brand-text"
            >
              <Heart className="h-[18px] w-[18px] text-peach" strokeWidth={2.2} />
              {t('hero.imOwner')}
            </a>
          </div>
          <div className="flex flex-wrap items-center gap-x-[18px] gap-y-2.5 text-[13.5px] font-medium text-[#7C8A84]">
            <span className="inline-flex items-center gap-[7px]">
              <ShieldCheck className="h-4 w-4 text-brand" strokeWidth={2.2} />
              {t('hero.trust.dicom')}
            </span>
            <span className="h-1 w-1 rounded-full bg-[#CDBFA8]" />
            <span className="inline-flex items-center gap-[7px]">
              <PawPrint className="h-4 w-4 text-brand" strokeWidth={2.2} />
              {t('hero.trust.species')}
            </span>
            <span className="h-1 w-1 rounded-full bg-[#CDBFA8]" />
            <span className="inline-flex items-center gap-[7px]">
              <Lock className="h-4 w-4 text-brand" strokeWidth={2.2} />
              {t('hero.trust.privacy')}
            </span>
          </div>
        </div>

        {/* hero collage */}
        <div className="relative motion-safe:animate-vfade">
          <div className="relative aspect-[4/5] overflow-hidden rounded-[26px] shadow-[0_30px_60px_-20px_rgba(22,48,43,0.34)]">
            <img
              src={HERO_IMG}
              crossOrigin="anonymous"
              alt=""
              className="block h-full w-full bg-brand-mint object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-b from-transparent from-[55%] to-[rgba(13,35,31,0.32)]" />
          </div>

          {/* floating viewer chip */}
          <div className="absolute bottom-9 left-[-26px] w-[230px] rounded-2xl bg-[#0E1B19] p-3 shadow-[0_22px_44px_-14px_rgba(13,35,31,0.5)] motion-safe:animate-vfloat">
            <div className="relative aspect-[7/5] overflow-hidden rounded-[9px] bg-[#05070a]">
              <img src={RADIOGRAPH} alt="" className="block h-full w-full object-cover" />
              <div className="absolute left-[14%] top-[34%] h-[30%] w-[30%] rounded-[7px] border-[1.5px] border-brand-bright shadow-[0_0_0_3px_rgba(52,215,160,0.18)]" />
              <span className="absolute left-[14%] top-[calc(34%-18px)] rounded-[5px] bg-brand-bright px-1.5 py-0.5 text-[9px] font-semibold text-[#0E1B19]">
                {t('hero.chipReview')}
              </span>
            </div>
            <div className="flex items-center justify-between px-1 pb-0.5 pt-[9px]">
              <div>
                <div className="text-xs font-semibold text-white">{t('hero.chipName')}</div>
                <div className="text-[10px] text-[#7E938C]">{t('hero.chipSub')}</div>
              </div>
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-brand-bright">
                <span className="h-1.5 w-1.5 rounded-full bg-brand-bright motion-safe:animate-vpulse" />
                {t('hero.live')}
              </span>
            </div>
          </div>

          {/* warm owner chip */}
          <div
            className="absolute right-[-22px] top-[30px] flex items-center gap-[11px] rounded-[15px] border border-[#F0E5D8] bg-white px-3.5 py-3 shadow-[0_18px_38px_-16px_rgba(22,48,43,0.3)] motion-safe:animate-vfloat"
            style={{ animationDelay: '1.2s' }}
          >
            <span className="flex h-[38px] w-[38px] items-center justify-center rounded-[11px] bg-peach-bg">
              <Heart className="h-5 w-5 text-peach" strokeWidth={2.2} />
            </span>
            <div>
              <div className="text-[13px] font-semibold text-forest-ink2">
                {t('hero.explained')}
              </div>
              <div className="text-[11.5px] text-[#8A958F]">{t('hero.explainedSub')}</div>
            </div>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* TRUST STRIP                                                       */}
      {/* ----------------------------------------------------------------- */}
      <section className={`${CONTAINER} pb-14 pt-[18px]`}>
        <p className="mb-[22px] text-center text-[13px] font-semibold uppercase tracking-[0.14em] text-[#9A9486]">
          {t('strip.title')}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-x-11 gap-y-3.5 text-[15px] font-semibold text-[#46544F]">
          <span className="inline-flex items-center gap-2">
            <CheckCircle2 className="h-[17px] w-[17px] text-brand" strokeWidth={2} />
            {t('strip.peerReviewed')}
          </span>
          <span className="inline-flex items-center gap-2">
            <Lock className="h-[17px] w-[17px] text-brand" strokeWidth={2} />
            {t('strip.gdpr')}
          </span>
          <span className="inline-flex items-center gap-2">
            <Network className="h-[17px] w-[17px] text-brand" strokeWidth={2} />
            {t('strip.dicomweb')}
          </span>
          <span className="inline-flex items-center gap-2">
            <TrendingUp className="h-[17px] w-[17px] text-brand" strokeWidth={2} />
            {t('strip.fasterReads')}
          </span>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* TWO AUDIENCES                                                     */}
      {/* ----------------------------------------------------------------- */}
      <section id="care" className={`${CONTAINER} scroll-mt-24 px-6 pb-5 pt-6 sm:px-8`}>
        <div className="mx-auto mb-11 max-w-[660px] text-center">
          <Eyebrow>{t('audiences.eyebrow')}</Eyebrow>
          <h2 className="mt-2 font-display text-[32px] font-bold leading-[1.1] tracking-[-0.025em] text-forest-ink sm:text-[40px]">
            {t('audiences.heading')}
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* clinician card */}
          <div className="relative overflow-hidden rounded-[22px] bg-forest p-[34px] text-[#EAF3EF]">
            <div className="mb-[18px] flex items-center gap-3">
              <span className="flex h-[46px] w-[46px] items-center justify-center rounded-[13px] bg-white/[0.08]">
                <Stethoscope className="h-6 w-6 text-brand-bright" strokeWidth={2} />
              </span>
              <span className="text-[13px] font-semibold uppercase tracking-[0.08em] text-[#8FBFAE]">
                {t('audiences.clinic.label')}
              </span>
            </div>
            <h3 className="mb-3 font-display text-[25px] font-semibold leading-[1.18] text-white">
              {t('audiences.clinic.title')}
            </h3>
            <p className="mb-[22px] text-[15.5px] leading-[1.6] text-[#B6CEC6]">
              {t('audiences.clinic.desc')}
            </p>
            <div className="flex flex-col gap-[13px]">
              {['b1', 'b2', 'b3'].map((b) => (
                <div key={b} className="flex items-center gap-[11px] text-[15px] text-[#DCEAE5]">
                  <Check className="h-[18px] w-[18px] shrink-0 text-brand-bright" strokeWidth={2.4} />
                  {t(`audiences.clinic.${b}`)}
                </div>
              ))}
            </div>
          </div>

          {/* owner card */}
          <div className="relative overflow-hidden rounded-[22px] border border-[#F0E6D8] bg-white p-[34px]">
            <div className="mb-[18px] flex items-center gap-3">
              <span className="flex h-[46px] w-[46px] items-center justify-center rounded-[13px] bg-peach-bg">
                <Heart className="h-6 w-6 text-peach" strokeWidth={2} />
              </span>
              <span className="text-[13px] font-semibold uppercase tracking-[0.08em] text-peach-text">
                {t('audiences.owner.label')}
              </span>
            </div>
            <h3 className="mb-3 font-display text-[25px] font-semibold leading-[1.18] text-forest-ink2">
              {t('audiences.owner.title')}
            </h3>
            <p className="mb-[22px] text-[15.5px] leading-[1.6] text-[#5C6B66]">
              {t('audiences.owner.desc')}
            </p>
            <div className="flex flex-col gap-[13px]">
              {['b1', 'b2', 'b3'].map((b) => (
                <div key={b} className="flex items-center gap-[11px] text-[15px] text-[#3C4B46]">
                  <Check className="h-[18px] w-[18px] shrink-0 text-peach" strokeWidth={2.4} />
                  {t(`audiences.owner.${b}`)}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* VIEWER SHOWCASE                                                   */}
      {/* ----------------------------------------------------------------- */}
      <section id="viewer" className="mt-16 scroll-mt-20 bg-forest text-[#EAF3EF]">
        <div
          className={`${CONTAINER} grid grid-cols-1 items-center gap-12 py-[72px] lg:grid-cols-[0.92fr_1.08fr] lg:gap-[54px]`}
        >
          <div>
            <Eyebrow className="text-brand-bright">{t('viewer.eyebrow')}</Eyebrow>
            <h2 className="mb-[18px] mt-2 font-display text-[32px] font-bold leading-[1.1] tracking-[-0.025em] text-white sm:text-[40px]">
              {t('viewer.heading')}
            </h2>
            <p className="mb-7 max-w-[440px] text-[17px] leading-[1.65] text-[#B6CEC6]">
              {t('viewer.desc')}
            </p>
            <div className="flex flex-col gap-[18px]">
              {[
                { icon: Users, key: 'f1' },
                { icon: Search, key: 'f2' },
                { icon: Share2, key: 'f3' },
              ].map(({ icon: Icon, key }) => (
                <div key={key} className="flex items-start gap-3.5">
                  <span className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-[10px] bg-brand-bright/[0.14]">
                    <Icon className="h-[18px] w-[18px] text-brand-bright" strokeWidth={2.2} />
                  </span>
                  <div>
                    <div className="mb-[3px] text-base font-semibold text-white">
                      {t(`viewer.${key}Title`)}
                    </div>
                    <div className="text-[14.5px] leading-[1.5] text-[#9FBBB2]">
                      {t(`viewer.${key}Desc`)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* viewer mock */}
          <div className="overflow-hidden rounded-[20px] border border-[#1E3A33] bg-[#0A1614] shadow-[0_40px_80px_-30px_rgba(0,0,0,0.6)]">
            <div className="flex items-center gap-2 border-b border-[#16302A] bg-[#0C1B18] px-4 py-[13px]">
              <span className="h-[11px] w-[11px] rounded-full bg-[#F2705C]" />
              <span className="h-[11px] w-[11px] rounded-full bg-[#F2B544]" />
              <span className="h-[11px] w-[11px] rounded-full bg-[#34C77A]" />
              <span className="ml-2.5 truncate text-[12.5px] font-medium text-[#7E938C]">
                {t('viewer.mock.title')}
              </span>
              <span className="ml-auto inline-flex items-center gap-1.5 rounded-[7px] bg-brand-bright/[0.12] px-2.5 py-1 text-[11.5px] font-semibold text-brand-bright">
                <BadgeCheck className="h-3 w-3" strokeWidth={2.4} />
                {t('viewer.mock.dicom')}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-[128px_1fr]">
              {/* sidebar */}
              <div className="border-b border-[#16302A] bg-[#0B1815] p-3 sm:border-b-0 sm:border-r">
                <div className="mb-[9px] text-[10px] font-semibold uppercase tracking-[0.1em] text-[#5E776F]">
                  {t('viewer.mock.owner')}
                </div>
                <div className="mb-4 flex items-center gap-2">
                  <img
                    src={OWNER_AVATAR}
                    crossOrigin="anonymous"
                    alt=""
                    className="h-[30px] w-[30px] rounded-lg bg-brand-mint object-cover"
                  />
                  <div>
                    <div className="text-xs font-semibold text-[#E7F1ED]">
                      {t('viewer.mock.ownerName')}
                    </div>
                    <div className="text-[10px] text-[#6E847C]">
                      {t('viewer.mock.ownerPatients')}
                    </div>
                  </div>
                </div>
                <div className="mb-[9px] text-[10px] font-semibold uppercase tracking-[0.1em] text-[#5E776F]">
                  {t('viewer.mock.patient')}
                </div>
                <div className="mb-2 rounded-[9px] border border-brand-bright/25 bg-brand-bright/10 p-[9px]">
                  <div className="text-[12.5px] font-semibold text-white">
                    {t('viewer.mock.patientName')}
                  </div>
                  <div className="text-[10.5px] text-[#8FB3A8]">{t('viewer.mock.patientMeta')}</div>
                </div>
                <div className="rounded-[9px] p-[9px]">
                  <div className="text-[12.5px] font-semibold text-[#B6CEC6]">
                    {t('viewer.mock.patient2Name')}
                  </div>
                  <div className="text-[10.5px] text-[#6E847C]">{t('viewer.mock.patient2Meta')}</div>
                </div>
              </div>

              {/* image canvas */}
              <div className="relative min-h-[330px] bg-[#05070a]">
                <img
                  src={RADIOGRAPH}
                  alt=""
                  className="absolute inset-0 block h-full w-full object-cover"
                />
                <div className="absolute left-[13%] top-[30%] h-[30%] w-[26%] rounded-lg border-[1.5px] border-brand-bright shadow-[0_0_0_4px_rgba(52,215,160,0.16)]" />
                <span className="absolute left-[13%] top-[calc(30%-22px)] rounded-md bg-brand-bright px-[9px] py-[3px] text-[11px] font-semibold text-[#0A1614]">
                  {t('viewer.mock.regionFlagged')}
                </span>
                {/* top-left meta */}
                <div className="absolute left-3.5 top-[13px] text-[11px] leading-[1.5] text-[#9FBBB2]">
                  <div className="font-semibold text-[#E7F1ED]">{t('viewer.mock.metaName')}</div>
                  {t('viewer.mock.metaView')}
                  <br />
                  {t('viewer.mock.metaTech')}
                </div>
                {/* window controls */}
                <div className="absolute right-3.5 top-[13px] flex flex-col items-end gap-1.5 text-[10.5px] text-[#7E938C]">
                  <span className="rounded-md border border-[#1E3A33] bg-[#0A1614]/70 px-2 py-[3px]">
                    W 380 · L 40
                  </span>
                  <span className="rounded-md border border-[#1E3A33] bg-[#0A1614]/70 px-2 py-[3px]">
                    Zoom 118%
                  </span>
                </div>
                {/* bottom AI note */}
                <div className="absolute inset-x-3.5 bottom-[13px] flex items-center gap-[11px] rounded-[11px] border border-[#1E3A33] bg-[#0A1614]/80 px-3.5 py-[11px] backdrop-blur-[6px]">
                  <span className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-lg bg-brand-bright/[0.16]">
                    <Sparkles className="h-4 w-4 text-brand-bright" strokeWidth={2.2} />
                  </span>
                  <div className="flex-1">
                    <div className="mb-px text-[12.5px] font-semibold text-white">
                      {t('viewer.mock.aiTitle')}
                    </div>
                    <div className="text-[11px] text-[#8FB3A8]">{t('viewer.mock.aiSub')}</div>
                  </div>
                  <span className="shrink-0 rounded-[7px] bg-brand-bright px-[11px] py-[5px] text-[11px] font-semibold text-[#0A1614]">
                    {t('viewer.mock.confirm')}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* FEATURES                                                          */}
      {/* ----------------------------------------------------------------- */}
      <section className={`${CONTAINER} pb-5 pt-[72px]`}>
        <div className="mb-10 max-w-[600px]">
          <Eyebrow>{t('features.eyebrow')}</Eyebrow>
          <h2 className="mt-2 font-display text-[32px] font-bold leading-[1.12] tracking-[-0.025em] text-forest-ink sm:text-[38px]">
            {t('features.heading')}
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-[22px] md:grid-cols-3">
          {/* every modality */}
          <FeatureCard
            icon={<ImageIcon className="h-6 w-6 text-brand" strokeWidth={2} />}
            iconBg="bg-brand-mint"
            title={t('features.modalityTitle')}
            desc={t('features.modalityDesc')}
            chips={[
              { label: t('features.chips.xray'), tone: 'mint' },
              { label: t('features.chips.ct'), tone: 'mint' },
              { label: t('features.chips.ultrasound'), tone: 'mint' },
            ]}
          />
          {/* species aware */}
          <FeatureCard
            icon={<PawPrint className="h-6 w-6 text-peach" strokeWidth={2} />}
            iconBg="bg-peach-bg"
            title={t('features.speciesTitle')}
            desc={t('features.speciesDesc')}
            chips={[
              { label: t('features.chips.patientSpecific'), tone: 'peach' },
              { label: t('features.chips.riskContext'), tone: 'peach' },
            ]}
          />
          {/* privacy */}
          <FeatureCard
            icon={<Lock className="h-6 w-6 text-brand" strokeWidth={2} />}
            iconBg="bg-brand-mint"
            title={t('features.privacyTitle')}
            desc={t('features.privacyDesc')}
            chips={[
              { label: t('features.chips.encrypted'), tone: 'mint' },
              { label: t('features.chips.gdpr'), tone: 'mint' },
            ]}
          />
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* TESTIMONIAL + CREDIBILITY                                         */}
      {/* ----------------------------------------------------------------- */}
      <section className={`${CONTAINER} py-16`}>
        <div className="grid grid-cols-1 items-stretch gap-[26px] lg:grid-cols-[1.15fr_0.85fr]">
          <div className="flex flex-col justify-center rounded-[22px] border border-[#F0E6D8] bg-cream-card p-[38px]">
            <div className="mb-[18px] flex gap-[3px]">
              {[0, 1, 2, 3, 4].map((s) => (
                <Star key={s} className="h-5 w-5 fill-[#F2B544] text-[#F2B544]" />
              ))}
            </div>
            <p className="mb-[26px] font-serif-accent text-[26px] font-normal leading-[1.4] text-[#1B332D]">
              &ldquo;{t('testimonial.quote')}&rdquo;
            </p>
            <div className="flex items-center gap-[13px]">
              <img
                src={TESTIMONIAL_AVATAR}
                crossOrigin="anonymous"
                alt=""
                className="h-[50px] w-[50px] rounded-[13px] bg-brand-mint object-cover"
              />
              <div>
                <div className="text-base font-bold text-forest-ink2">{t('testimonial.author')}</div>
                <div className="text-sm text-[#8A958F]">{t('testimonial.role')}</div>
              </div>
            </div>
          </div>
          <div className="grid grid-rows-2 gap-[26px]">
            <div className="flex flex-col justify-center rounded-[22px] bg-gradient-to-br from-[#13B886] to-brand-deep p-[30px] text-white">
              <div className="mb-1.5 font-display text-[44px] font-bold leading-none tracking-[-0.03em]">
                {t('testimonial.stat1Value')}
              </div>
              <div className="text-[15px] leading-[1.45] text-[#E2F5EE]">
                {t('testimonial.stat1Desc')}
              </div>
            </div>
            <div className="flex flex-col justify-center rounded-[22px] bg-forest p-[30px] text-white">
              <div className="mb-1.5 font-display text-[44px] font-bold leading-none tracking-[-0.03em] text-brand-bright">
                {t('testimonial.stat2Value')}
              </div>
              <div className="text-[15px] leading-[1.45] text-[#B6CEC6]">
                {t('testimonial.stat2Desc')}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* OWNER REASSURANCE BAND                                            */}
      {/* ----------------------------------------------------------------- */}
      <section id="owners" className={`${CONTAINER} scroll-mt-20 pb-[72px] pt-5`}>
        <div className="grid grid-cols-1 items-stretch overflow-hidden rounded-[26px] bg-peach-bg md:grid-cols-2">
          <div className="flex flex-col justify-center p-8 sm:p-12">
            <Eyebrow className="text-peach-text">{t('ownersBand.eyebrow')}</Eyebrow>
            <h2 className="mb-3.5 mt-2 font-display text-[30px] font-bold leading-[1.12] tracking-[-0.025em] text-peach-ink sm:text-[36px]">
              {t('ownersBand.heading')}
            </h2>
            <p className="mb-6 max-w-[420px] text-[16.5px] leading-[1.6] text-peach-body">
              {t('ownersBand.desc')}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <a
                href="#demo"
                className="inline-flex items-center gap-2.5 rounded-xl bg-peach-solid px-6 py-3.5 text-[15.5px] font-semibold text-white shadow-[0_12px_24px_rgba(217,116,78,0.32)] transition-all hover:-translate-y-0.5 hover:brightness-105"
              >
                {t('ownersBand.cta')}
              </a>
              <a
                href="#viewer"
                className="inline-flex items-center gap-2 px-[18px] py-3.5 text-[15.5px] font-semibold text-[#8A4E37]"
              >
                {t('ownersBand.howItWorks')}
              </a>
            </div>
          </div>
          <div className="relative min-h-[280px] md:min-h-[340px]">
            <img
              src={OWNER_IMG}
              crossOrigin="anonymous"
              alt=""
              className="absolute inset-0 h-full w-full bg-peach-bg object-cover"
            />
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* FINAL CTA                                                         */}
      {/* ----------------------------------------------------------------- */}
      <section id="demo" className="scroll-mt-20 bg-forest text-white">
        <div className="mx-auto max-w-[1000px] px-6 py-20 text-center sm:px-8">
          <Eyebrow className="text-brand-bright">{t('finalCta.eyebrow')}</Eyebrow>
          <h2 className="mb-[18px] mt-2.5 font-display text-[34px] font-bold leading-[1.08] tracking-[-0.03em] sm:text-[46px]">
            {t('finalCta.heading')}
          </h2>
          <p className="mx-auto mb-[30px] max-w-[520px] text-[18px] leading-[1.6] text-[#B6CEC6]">
            {t('finalCta.desc')}
          </p>
          <div className="flex flex-wrap justify-center gap-3.5">
            <Link
              to={demoTarget}
              className="inline-flex items-center gap-2.5 rounded-[13px] bg-brand-bright px-[30px] py-4 text-base font-bold text-forest shadow-[0_14px_30px_rgba(52,215,160,0.3)] transition-all hover:-translate-y-0.5 hover:brightness-105"
            >
              {t('finalCta.bookDemo')}
              <ArrowRight className="h-[18px] w-[18px]" strokeWidth={2.4} />
            </Link>
            <Link
              to={isAuthenticated ? '/dashboard' : '/auth/login'}
              className="inline-flex items-center gap-2.5 rounded-[13px] border border-white/20 bg-white/[0.08] px-6 py-4 text-base font-semibold text-white transition-colors hover:bg-white/[0.14]"
            >
              {t('finalCta.talkToTeam')}
            </Link>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* FOOTER                                                            */}
      {/* ----------------------------------------------------------------- */}
      <footer className="bg-forest-footer text-[#9FBBB2]">
        <div
          className={`${CONTAINER} grid grid-cols-2 gap-8 pb-7 pt-14 md:grid-cols-[1.6fr_1fr_1fr_1fr]`}
        >
          <div className="col-span-2 md:col-span-1">
            <Link to="/" className="mb-4 flex items-center gap-[11px]">
              <span className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-gradient-to-br from-[#13B886] to-brand-deep">
                <PawPrint className="h-5 w-5 text-white" strokeWidth={2} />
              </span>
              <span className="font-display text-[19px] font-bold text-white">VetImage</span>
            </Link>
            <p className="mb-4 max-w-[300px] text-[14.5px] leading-[1.6]">{t('footer.desc')}</p>
            <div className="flex items-center gap-3.5 text-[13px] font-medium text-[#6E847C]">
              <span>{t('footer.compliant')}</span>
              <span className="h-1 w-1 rounded-full bg-[#33524A]" />
              <span>{t('footer.secure')}</span>
              <span className="h-1 w-1 rounded-full bg-[#33524A]" />
              <span>{t('footer.privacy')}</span>
            </div>
          </div>

          <FooterColumn
            heading={t('footer.colPlatform')}
            links={[
              { label: t('footer.platformAbout'), to: '/docs' },
              { label: t('footer.platformFeatures'), to: '/models' },
              { label: t('footer.platformClinics'), to: '#care' },
              { label: t('footer.platformOwners'), to: '#owners' },
            ]}
          />
          <FooterColumn
            heading={t('footer.colTools')}
            links={[
              { label: t('footer.toolsViewer'), to: '/analyze' },
              { label: t('footer.toolsUpload'), to: '/analyze' },
              { label: t('footer.toolsAnalysis'), to: '/analyze' },
              { label: t('footer.toolsModels'), to: '/models' },
            ]}
          />
          <FooterColumn
            heading={t('footer.colResources')}
            links={[
              { label: t('footer.resourcesDocs'), to: '/docs' },
              { label: t('footer.resourcesDicomweb'), to: '/docs' },
              { label: t('footer.resourcesSecurity'), to: '/security' },
              { label: t('footer.resourcesSupport'), to: '/docs' },
            ]}
          />
        </div>
        <div className="border-t border-[#163029]">
          <div
            className={`${CONTAINER} flex flex-wrap items-center justify-between gap-3.5 py-5 text-[13px] text-[#6E847C]`}
          >
            <span>{t('footer.legal', { year: new Date().getFullYear() })}</span>
            <div className="flex gap-5">
              <Link to="/security" className="hover:text-[#B6CEC6]">
                {t('footer.legalPrivacy')}
              </Link>
              <Link to="/security" className="hover:text-[#B6CEC6]">
                {t('footer.legalTerms')}
              </Link>
              <Link to="/security" className="hover:text-[#B6CEC6]">
                {t('footer.legalCompliance')}
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

/* -------------------------------------------------------------------------- */
/*  Small presentational helpers                                              */
/* -------------------------------------------------------------------------- */

interface Chip {
  label: string;
  tone: 'mint' | 'peach';
}

const FeatureCard: React.FC<{
  icon: React.ReactNode;
  iconBg: string;
  title: string;
  desc: string;
  chips: Chip[];
}> = ({ icon, iconBg, title, desc, chips }) => (
  <div className="rounded-[18px] border border-[#F0E6D8] bg-white p-[26px] transition-all hover:-translate-y-[3px] hover:border-brand-mintborder hover:shadow-[0_18px_36px_-22px_rgba(22,48,43,0.35)]">
    <span className={`mb-4 flex h-12 w-12 items-center justify-center rounded-[13px] ${iconBg}`}>
      {icon}
    </span>
    <h3 className="mb-2 font-display text-[19px] font-semibold text-forest-ink2">{title}</h3>
    <p className="mb-3.5 text-[14.5px] leading-[1.55] text-[#5C6B66]">{desc}</p>
    <div className="flex flex-wrap gap-[7px]">
      {chips.map((chip) => (
        <span
          key={chip.label}
          className={`rounded-[7px] px-2.5 py-1 text-xs font-semibold ${
            chip.tone === 'peach'
              ? 'bg-peach-bg text-peach-text'
              : 'bg-brand-mint text-brand-text'
          }`}
        >
          {chip.label}
        </span>
      ))}
    </div>
  </div>
);

const FooterColumn: React.FC<{
  heading: string;
  links: { label: string; to: string }[];
}> = ({ heading, links }) => (
  <div>
    <div className="mb-3.5 text-xs font-bold uppercase tracking-[0.12em] text-[#5E776F]">
      {heading}
    </div>
    <div className="flex flex-col gap-2.5 text-[14.5px]">
      {links.map((link) =>
        link.to.startsWith('#') ? (
          <a key={link.label} href={link.to} className="text-[#B6CEC6] hover:text-brand-bright">
            {link.label}
          </a>
        ) : (
          <Link key={link.label} to={link.to} className="text-[#B6CEC6] hover:text-brand-bright">
            {link.label}
          </Link>
        )
      )}
    </div>
  </div>
);

export default LandingPage;
