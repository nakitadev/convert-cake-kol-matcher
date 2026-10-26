'use client';

import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Search,
  Filter,
  TrendingUp,
  Users,
  ShieldCheck,
  ShieldAlert,
  Target,
  RefreshCw,
  Download,
  ChevronRight,
  Sliders,
  Info,
  Flame,
  Check,
  Copy,
  Eye,
  Heart,
  MessageSquare,
  Share2,
  ShoppingBag
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface BrandDNA {
  id?: string;
  brand_name: string;
  website_url: string;
  facebook_url: string;
  vertical: string;
  sub_category: string;
  brand_summary: string;
  target_audience: string;
  target_age_range: string;
  target_locations: string[];
  brand_tone: string[];
  content_style_preferences: string[];
  price_positioning: string;
  average_price_thb: number;
  thai_keywords: string[];
  scraped_sources: string[];
}

interface VideoMetric {
  video_id: string;
  caption: string;
  hashtags: string[];
  views: number;
  likes: number;
  comments: number;
  shares: number;
  has_yellow_basket: boolean;
  reviewed_item_price_thb?: number;
  location_tag?: string;
}

interface KOLProfile {
  id: string;
  handle: string;
  display_name: string;
  tiktok_url: string;
  avatar_url?: string;
  vertical: string;
  secondary_verticals: string[];
  bio: string;
  follower_count: number;
  following_count: number;
  total_likes: number;
  tier: string;
  creator_persona: string;
  content_styles: string[];
  typical_price_tier: string;
  avg_reviewed_price_thb: number;
  primary_locations: string[];
  audience_language: string;
  sample_comments: string[];
  recent_videos: VideoMetric[];
  is_affiliate_spam_trap: boolean;
  estimated_rate_thb: string;
}

interface SignalBreakdown {
  relevance_score_raw: number;
  relevance_weighted: number;
  semantic_similarity: number;
  matched_keywords: string[];
  engagement_score_raw: number;
  engagement_weighted: number;
  median_engagement_rate_pct: number;
  views_to_followers_ratio: number;
  yellow_basket_ratio: number;
  affiliate_spam_penalty_applied: boolean;
  affiliate_spam_penalty_points: number;
  affiliate_spam_reason?: string;
  audience_score_raw: number;
  audience_weighted: number;
  persona_signal_score: number;
  price_proxy_signal_score: number;
  geo_language_signal_score: number;
  comment_sentiment_signal_score: number;
  confidence_level: 'High' | 'Medium' | 'Low';
  evidence_list: string[];
}

interface RankedKOL {
  rank: number;
  kol: KOLProfile;
  total_match_score: number;
  score_breakdown: SignalBreakdown;
  why_this_kol: string;
  thai_campaign_hooks: string[];
  enrichment_source: string;
}

interface MatchResponse {
  brand_dna: BrandDNA;
  total_candidates_evaluated: number;
  apify_enrichment_status: string;
  ranked_kols: RankedKOL[];
  penalized_spam_kols: RankedKOL[];
  workflow_trace: string[];
}

export default function HomePage() {
  // Brand Presets & Form State
  const [presets, setPresets] = useState<BrandDNA[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('srichand-skincare');
  const [brandName, setBrandName] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [facebookUrl, setFacebookUrl] = useState('');
  const [customNotes, setCustomNotes] = useState('');

  // Step 1: Extracted Brand DNA
  const [brandDNA, setBrandDNA] = useState<BrandDNA | null>(null);
  const [isEditingDNA, setIsEditingDNA] = useState(false);

  // Step 2: Match Results
  const [matchResponse, setMatchResponse] = useState<MatchResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'ranked' | 'spam' | 'trace'>('ranked');

  // Loading States
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [copiedHook, setCopiedHook] = useState<string | null>(null);

  // Filters
  const [topK, setTopK] = useState(8);
  const [verticalFilter, setVerticalFilter] = useState('All');

  // Load presets on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then(res => res.json())
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));

    fetch(`${API_BASE}/api/presets`)
      .then(res => res.json())
      .then((data: BrandDNA[]) => {
        setPresets(data);
        if (data.length > 0) {
          const first = data[0];
          setSelectedPresetId(first.id || '');
          setBrandName(first.brand_name);
          setWebsiteUrl(first.website_url);
          setFacebookUrl(first.facebook_url);
          setBrandDNA(first);
        }
      })
      .catch(err => console.error('Failed to load presets:', err));
  }, []);

  const handlePresetChange = (presetId: string) => {
    setSelectedPresetId(presetId);
    const p = presets.find(item => item.id === presetId);
    if (p) {
      setBrandName(p.brand_name);
      setWebsiteUrl(p.website_url);
      setFacebookUrl(p.facebook_url);
      setBrandDNA(p);
      setMatchResponse(null);
    }
  };

  // Stage 1: Analyze Brand DNA
  const handleAnalyzeBrand = async () => {
    setIsAnalyzing(true);
    try {
      const res = await fetch(`${API_BASE}/api/analyze-brand`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: brandName || undefined,
          website_url: websiteUrl || undefined,
          facebook_url: facebookUrl || undefined,
          preset_id: selectedPresetId || undefined,
          custom_notes: customNotes || undefined,
        }),
      });
      const data = await res.json();
      setBrandDNA(data);
      setMatchResponse(null);
    } catch (err) {
      console.error(err);
      alert('Failed to analyze brand. Ensure backend is running.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Stage 2: Match KOLs from confirmed Brand DNA
  const handleMatchKOLs = async () => {
    if (!brandDNA) return;
    setIsMatching(true);
    try {
      const res = await fetch(`${API_BASE}/api/match-kols`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_dna: brandDNA,
          top_k: topK,
          include_penalized_traps: true,
        }),
      });
      const data = await res.json();
      setMatchResponse(data);
    } catch (err) {
      console.error(err);
      alert('KOL matching failed. Ensure backend is running.');
    } finally {
      setIsMatching(false);
    }
  };

  // 1-Click Auto Run (Stage 1 + Stage 2)
  const handleAutoMatch = async () => {
    setIsMatching(true);
    try {
      const res = await fetch(`${API_BASE}/api/auto-match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: brandName || undefined,
          website_url: websiteUrl || undefined,
          facebook_url: facebookUrl || undefined,
          preset_id: selectedPresetId || undefined,
          custom_notes: customNotes || undefined,
          top_k: topK,
        }),
      });
      const data = await res.json();
      setBrandDNA(data.brand_dna);
      setMatchResponse(data);
    } catch (err) {
      console.error(err);
      alert('Auto-matching failed. Ensure backend is running.');
    } finally {
      setIsMatching(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHook(id);
    setTimeout(() => setCopiedHook(null), 2000);
  };

  const exportToCSV = () => {
    if (!matchResponse) return;
    const headers = [
      'Rank',
      'Handle',
      'Display Name',
      'TikTok URL',
      'Tier',
      'Followers',
      'Total Match Score',
      'Relevance (45%)',
      'Engagement (35%)',
      'Median ER %',
      'Audience Score (20%)',
      'Confidence',
      'Affiliate Penalized',
      'Rationale',
      'Primary Hook',
    ];
    const rows = matchResponse.ranked_kols.map(item => [
      item.rank,
      `@${item.kol.handle}`,
      `"${item.kol.display_name.replace(/"/g, '""')}"`,
      item.kol.tiktok_url,
      item.kol.tier,
      item.kol.follower_count,
      item.total_match_score,
      item.score_breakdown.relevance_weighted,
      item.score_breakdown.engagement_weighted,
      item.score_breakdown.median_engagement_rate_pct,
      item.score_breakdown.audience_weighted,
      item.score_breakdown.confidence_level,
      item.score_breakdown.affiliate_spam_penalty_applied ? 'YES' : 'NO',
      `"${item.why_this_kol.replace(/"/g, '""')}"`,
      `"${(item.thai_campaign_hooks[0] || '').replace(/"/g, '""')}"`,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,﻿' +
      [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `convert_cake_kol_recommendations_${brandDNA?.brand_name || 'brand'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Header & Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-rose-500 via-pink-500 to-amber-400 flex items-center justify-center font-bold text-white shadow-lg shadow-rose-500/20">
              CC
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold tracking-tight text-white">
                  Convert Cake
                </h1>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  TikTok KOL Matcher TH
                </span>
              </div>
              <p className="text-xs text-slate-400">
                AI Automation & Multi-Agent Influencer Intelligence Platform
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium bg-slate-800 border border-slate-700">
              <span
                className={`w-2 h-2 rounded-full ${
                  apiOnline === true
                    ? 'bg-emerald-400 animate-pulse'
                    : apiOnline === false
                    ? 'bg-rose-500'
                    : 'bg-amber-400'
                }`}
              />
              <span className="text-slate-300">
                {apiOnline === true
                  ? 'FastAPI Backend Online'
                  : apiOnline === false
                  ? 'Backend Disconnected'
                  : 'Checking Service...'}
              </span>
            </div>

            <div className="hidden md:flex items-center text-xs text-slate-400 border-l border-slate-800 pl-3 space-x-2">
              <span>LangGraph 2-Stage</span>
              <span>•</span>
              <span>Apify Live Telemetry</span>
              <span>•</span>
              <span>Anti-Spam Filter</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Intro Callout Banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 p-6 shadow-xl">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1.5 max-w-3xl">
              <div className="inline-flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-rose-400">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Digital Marketing Agency AI Automation Case Study</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                Match Client Brands to High-ROI Thai TikTok KOLs in Minutes
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed">
                Autonomous pipeline: Scrapes Website & Facebook pages → extracts Brand DNA with Human-in-the-Loop review → queries pre-indexed Thai KOL vector pool + live Apify telemetry → applies 3-part Hybrid Scoring (Relevance 45%, Engagement 35%, Multi-Signal Demographics 20%) with strict Anti-Affiliate Spam defense.
              </p>
            </div>
            <div className="flex sm:flex-col gap-2 shrink-0">
              <button
                onClick={handleAutoMatch}
                disabled={isMatching || isAnalyzing}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-pink-600 hover:from-rose-600 hover:to-pink-700 text-white font-semibold text-sm shadow-lg shadow-rose-500/25 transition flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
              >
                {isMatching ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Matching...</span>
                  </>
                ) : (
                  <>
                    <Flame className="w-4 h-4" />
                    <span>1-Click Auto Match</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Grid: Left Column (Inputs & Brand DNA) / Right Column (KOL Recommendations) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* LEFT COLUMN: Stage 1 Ingestion & Brand DNA (5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Input Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-md space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-rose-500/20 text-rose-400 text-xs font-bold">
                    1
                  </span>
                  <h3 className="font-bold text-white text-base">Brand Ingestion (Stage 1)</h3>
                </div>
                <span className="text-xs text-slate-400">Web & FB Crawler</span>
              </div>

              {/* Sample Presets Picker */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Load Agency Client Presets
                </label>
                <div className="grid grid-cols-1 gap-2">
                  {presets.map(p => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => handlePresetChange(p.id || '')}
                      className={`text-left px-3.5 py-2.5 rounded-xl border transition text-xs font-medium cursor-pointer ${
                        selectedPresetId === p.id
                          ? 'bg-rose-500/10 border-rose-500/50 text-white shadow-sm'
                          : 'bg-slate-800/60 border-slate-700/60 text-slate-300 hover:bg-slate-800 hover:text-white'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold truncate">{p.brand_name.split('—')[0]}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {p.vertical.split('&')[0]}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 truncate mt-0.5">{p.sub_category}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Inputs */}
              <div className="space-y-3 pt-2 border-t border-slate-800/80">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Client Brand Name
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={e => setBrandName(e.target.value)}
                    placeholder="e.g. Srichand / After You / ErgoDesk TH"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-rose-500 transition"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Website URL
                    </label>
                    <input
                      type="text"
                      value={websiteUrl}
                      onChange={e => setWebsiteUrl(e.target.value)}
                      placeholder="https://..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-rose-500 transition"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Facebook Page URL
                    </label>
                    <input
                      type="text"
                      value={facebookUrl}
                      onChange={e => setFacebookUrl(e.target.value)}
                      placeholder="https://facebook.com/..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-rose-500 transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Agency Brief & Campaign Focus
                  </label>
                  <textarea
                    rows={2}
                    value={customNotes}
                    onChange={e => setCustomNotes(e.target.value)}
                    placeholder="Specific product lines, discount codes, or target sub-audiences..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-rose-500 transition"
                  />
                </div>
              </div>

              <button
                onClick={handleAnalyzeBrand}
                disabled={isAnalyzing}
                className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-100 font-semibold text-xs transition flex items-center justify-center space-x-2 cursor-pointer"
              >
                {isAnalyzing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Crawling & Analyzing Brand...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5" />
                    <span>Extract / Refresh Brand DNA</span>
                  </>
                )}
              </button>
            </div>

            {/* Stage 1 Output: Interactive Brand DNA Card (Human-in-the-Loop) */}
            {brandDNA && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-md space-y-4 relative">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    <h3 className="font-bold text-white text-base">Extracted Brand DNA</h3>
                  </div>
                  <button
                    onClick={() => setIsEditingDNA(!isEditingDNA)}
                    className="text-xs font-medium text-rose-400 hover:text-rose-300 transition flex items-center space-x-1 cursor-pointer"
                  >
                    <Sliders className="w-3 h-3" />
                    <span>{isEditingDNA ? 'Lock DNA' : 'Edit DNA'}</span>
                  </button>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-400 font-medium">Industry Vertical:</span>
                      <span className="font-bold text-rose-400 px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20">
                        {brandDNA.vertical}
                      </span>
                    </div>
                    <p className="text-slate-300 font-medium">{brandDNA.sub_category}</p>
                  </div>

                  <div>
                    <span className="text-slate-400 font-medium block mb-1">Target Audience & Demographics:</span>
                    {isEditingDNA ? (
                      <textarea
                        rows={2}
                        value={brandDNA.target_audience}
                        onChange={e => setBrandDNA({ ...brandDNA, target_audience: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200"
                      />
                    ) : (
                      <p className="text-slate-200 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80 leading-relaxed">
                        {brandDNA.target_audience}
                      </p>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <div className="bg-slate-950/40 p-2 rounded-lg border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">Price Tier</span>
                      <span className="font-semibold text-slate-200">{brandDNA.price_positioning}</span>
                      <span className="text-slate-400 block text-[10px] mt-0.5">
                        ~{brandDNA.average_price_thb.toLocaleString()} THB
                      </span>
                    </div>
                    <div className="bg-slate-950/40 p-2 rounded-lg border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">Key Regions</span>
                      <span className="font-semibold text-slate-200 truncate block">
                        {brandDNA.target_locations.slice(0, 2).join(', ')}
                      </span>
                      <span className="text-slate-400 block text-[10px] mt-0.5">
                        Age: {brandDNA.target_age_range}
                      </span>
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-400 font-medium block mb-1.5">Brand Tone & Personality:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {brandDNA.brand_tone.map((tone, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 text-[11px] border border-slate-700"
                        >
                          {tone}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-400 font-medium block mb-1.5">Thai Search Tags & Hashtags:</span>
                    <div className="flex flex-wrap gap-1">
                      {brandDNA.thai_keywords.slice(0, 6).map((kw, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-300 text-[10px] border border-rose-500/20"
                        >
                          #{kw}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
                    <span>Ingestion Sources:</span>
                    <span className="truncate max-w-[200px] text-slate-300">
                      {brandDNA.scraped_sources[0] || 'Verified Profile'}
                    </span>
                  </div>
                </div>

                {/* Stage 2 Trigger */}
                <button
                  onClick={handleMatchKOLs}
                  disabled={isMatching}
                  className="w-full mt-4 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-sm shadow-lg shadow-emerald-500/20 transition flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  {isMatching ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Matching Thai TikTok KOLs...</span>
                    </>
                  ) : (
                    <>
                      <Target className="w-4 h-4" />
                      <span>Confirm & Match Thai KOLs (Stage 2)</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Stage 2 & 3 Ranked Results & Analysis (7 Cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Filter & Metric Bar */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-md flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-1.5">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                    2
                  </span>
                  <h3 className="font-bold text-white text-base">Curated KOL List</h3>
                </div>

                {matchResponse && (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                    {matchResponse.ranked_kols.length} Matches Found
                  </span>
                )}
              </div>

              <div className="flex items-center space-x-3">
                {matchResponse && (
                  <button
                    onClick={exportToCSV}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 transition flex items-center space-x-1.5 cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Export CSV</span>
                  </button>
                )}

                <div className="flex items-center space-x-2 text-xs text-slate-400">
                  <span>Top:</span>
                  <select
                    value={topK}
                    onChange={e => setTopK(Number(e.target.value))}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-slate-200 text-xs focus:outline-none"
                  >
                    <option value={5}>5</option>
                    <option value={8}>8</option>
                    <option value={12}>12</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Nav Tabs: Ranked KOLs | Penalized Traps | Execution Trace */}
            {matchResponse && (
              <div className="flex items-center space-x-2 border-b border-slate-800 pb-2 text-xs font-medium">
                <button
                  onClick={() => setActiveTab('ranked')}
                  className={`px-3 py-1.5 rounded-lg transition cursor-pointer ${
                    activeTab === 'ranked'
                      ? 'bg-rose-500 text-white font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Top Ranked Matches ({matchResponse.ranked_kols.length})
                </button>
                <button
                  onClick={() => setActiveTab('spam')}
                  className={`px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center space-x-1.5 ${
                    activeTab === 'spam'
                      ? 'bg-amber-500 text-slate-950 font-bold'
                      : 'text-amber-400 hover:bg-amber-500/10'
                  }`}
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Anti-Spam Filter Catch ({matchResponse.penalized_spam_kols.length})</span>
                </button>
                <button
                  onClick={() => setActiveTab('trace')}
                  className={`px-3 py-1.5 rounded-lg transition cursor-pointer ${
                    activeTab === 'trace'
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  LangGraph Pipeline Trace
                </button>
              </div>
            )}

            {/* Telemetry Status Bar */}
            {matchResponse && (
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Telemetry Source:</span>
                  <span className="font-semibold text-slate-100">
                    {matchResponse.apify_enrichment_status}
                  </span>
                </div>
                <span className="text-[11px] text-slate-400">
                  Evaluated {matchResponse.total_candidates_evaluated} candidates
                </span>
              </div>
            )}

            {/* No Match State Yet */}
            {!matchResponse && !isMatching && (
              <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-12 text-center space-y-4">
                <div className="w-16 h-16 rounded-2xl bg-slate-800/60 border border-slate-700/60 flex items-center justify-center mx-auto text-slate-400">
                  <Users className="w-8 h-8 text-rose-400" />
                </div>
                <div className="space-y-1 max-w-sm mx-auto">
                  <h4 className="text-base font-bold text-white">Ready to Run Matching</h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Select a client brand on the left or customize inputs, then click{' '}
                    <strong className="text-slate-200">Confirm & Match Thai KOLs</strong> to trigger the 3-part Hybrid Ranking Engine.
                  </p>
                </div>
                <button
                  onClick={handleAutoMatch}
                  className="px-5 py-2 rounded-xl bg-rose-500 hover:bg-rose-600 text-white text-xs font-semibold shadow-md transition cursor-pointer"
                >
                  Run Demo with Srichand (Preset)
                </button>
              </div>
            )}

            {/* Loading State */}
            {isMatching && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-4 animate-pulse">
                <RefreshCw className="w-10 h-10 text-rose-500 animate-spin mx-auto" />
                <div className="space-y-1.5">
                  <h4 className="text-base font-bold text-white">Executing Multi-Agent Matcher...</h4>
                  <p className="text-xs text-slate-400">
                    1. Cosine Vector Search → 2. Apify Telemetry Enrichment → 3. Multi-Signal Demographics → 4. Anti-Spam Yellow-Basket Filter
                  </p>
                </div>
              </div>
            )}

            {/* TAB 1: RANKED KOLS LIST */}
            {matchResponse && activeTab === 'ranked' && (
              <div className="space-y-4">
                {matchResponse.ranked_kols.map(item => (
                  <div
                    key={item.kol.id}
                    className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 shadow-lg transition space-y-4"
                  >
                    {/* Top Row: Rank, Identity, Profile Link, Total Score */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center space-x-3.5">
                        <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 text-white font-extrabold text-sm shadow-md shadow-rose-500/20 shrink-0">
                          #{item.rank}
                        </div>

                        <div>
                          <div className="flex items-center space-x-2 flex-wrap">
                            <h4 className="font-bold text-white text-base hover:text-rose-400 transition">
                              {item.kol.display_name}
                            </h4>
                            <a
                              href={item.kol.tiktok_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center space-x-1 text-xs text-rose-400 hover:text-rose-300 font-mono bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20"
                            >
                              <span>@{item.kol.handle}</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                          <div className="flex items-center space-x-2 text-xs text-slate-400 mt-0.5">
                            <span className="text-slate-300 font-semibold">{item.kol.tier}</span>
                            <span>•</span>
                            <span>{item.kol.follower_count.toLocaleString()} Followers</span>
                            <span>•</span>
                            <span>Est. Rate: {item.kol.estimated_rate_thb}</span>
                          </div>
                        </div>
                      </div>

                      {/* Total Score Badge */}
                      <div className="text-right shrink-0">
                        <div className="inline-flex items-baseline space-x-1 px-3 py-1 rounded-xl bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 text-emerald-400 font-black text-lg">
                          <span>{item.total_match_score.toFixed(1)}</span>
                          <span className="text-[11px] text-emerald-500 font-medium">/100</span>
                        </div>
                        <span className="block text-[10px] text-slate-400 mt-0.5">
                          Match Score
                        </span>
                      </div>
                    </div>

                    {/* 3-Part Hybrid Score Breakdown Progress Bars */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 text-xs">
                      {/* Bar 1: Relevance (45%) */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center text-[11px]">
                          <span className="text-slate-400 font-medium">1. Brand Relevance</span>
                          <span className="font-bold text-slate-200">
                            {item.score_breakdown.relevance_weighted.toFixed(1)} / 45 pts
                          </span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full bg-rose-500 rounded-full transition-all duration-500"
                            style={{
                              width: `${(item.score_breakdown.relevance_score_raw)}%`,
                            }}
                          />
                        </div>
                        <div className="flex justify-between text-[10px] text-slate-400">
                          <span>Vector Cosine Match</span>
                          <span>{item.score_breakdown.matched_keywords.length} tags matched</span>
                        </div>
                      </div>

                      {/* Bar 2: Engagement (35%) */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center text-[11px]">
                          <span className="text-slate-400 font-medium">2. Engagement Quality</span>
                          <span className="font-bold text-slate-200">
                            {item.score_breakdown.engagement_weighted.toFixed(1)} / 35 pts
                          </span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full transition-all duration-500"
                            style={{
                              width: `${(item.score_breakdown.engagement_score_raw)}%`,
                            }}
                          />
                        </div>
                        <div className="flex justify-between text-[10px] text-slate-400">
                          <span>
                            Median ER:{' '}
                            <strong className="text-slate-300">
                              {item.score_breakdown.median_engagement_rate_pct.toFixed(1)}%
                            </strong>
                          </span>
                          <span>V/F: {item.score_breakdown.views_to_followers_ratio.toFixed(2)}</span>
                        </div>
                      </div>

                      {/* Bar 3: Multi-Signal Demographics (20%) */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center text-[11px]">
                          <span className="text-slate-400 font-medium">3. Audience Signal</span>
                          <span className="font-bold text-slate-200">
                            {item.score_breakdown.audience_weighted.toFixed(1)} / 20 pts
                          </span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full bg-emerald-400 rounded-full transition-all duration-500"
                            style={{
                              width: `${(item.score_breakdown.audience_score_raw)}%`,
                            }}
                          />
                        </div>
                        <div className="flex justify-between items-center text-[10px]">
                          <span className="text-slate-400">Multi-Signal Match</span>
                          <span
                            className={`px-1.5 py-0.2 rounded font-bold text-[9px] ${
                              item.score_breakdown.confidence_level === 'High'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            }`}
                          >
                            {item.score_breakdown.confidence_level} Confidence
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Multi-Signal Evidence Chips */}
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-semibold text-slate-400 flex items-center space-x-1.5">
                        <Info className="w-3.5 h-3.5 text-slate-400" />
                        <span>Verified Public Evidence Across 4 Signals:</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {item.score_breakdown.evidence_list.map((ev, i) => (
                          <span
                            key={i}
                            className="px-2.5 py-1 rounded-lg bg-slate-800/80 text-slate-300 text-[11px] border border-slate-700/80 leading-tight"
                          >
                            {ev}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Strategic Rationale (Why this KOL) */}
                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/90 text-xs leading-relaxed text-slate-300">
                      <strong className="text-slate-100 font-semibold">Agency Strategic Rationale: </strong>
                      {item.why_this_kol}
                    </div>

                    {/* Custom Thai TikTok Campaign Hooks */}
                    {item.thai_campaign_hooks && item.thai_campaign_hooks.length > 0 && (
                      <div className="space-y-2 pt-1 border-t border-slate-800/70">
                        <span className="text-xs font-semibold text-rose-400 flex items-center space-x-1.5">
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Suggested Thai Campaign Hook Ideas for Pitch:</span>
                        </span>
                        <div className="grid grid-cols-1 gap-1.5">
                          {item.thai_campaign_hooks.map((hook, hIdx) => {
                            const hookId = `${item.kol.id}-${hIdx}`;
                            return (
                              <div
                                key={hIdx}
                                className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40 border border-slate-700/50 text-xs text-slate-200 group"
                              >
                                <span className="pr-2 italic">{hook}</span>
                                <button
                                  onClick={() => copyToClipboard(hook, hookId)}
                                  className="text-slate-400 hover:text-white transition p-1 cursor-pointer shrink-0"
                                  title="Copy Hook"
                                >
                                  {copiedHook === hookId ? (
                                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                                  ) : (
                                    <Copy className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
                                  )}
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* TAB 2: PENALIZED AFFILIATE SPAM TRAPS */}
            {matchResponse && activeTab === 'spam' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs space-y-1.5">
                  <div className="flex items-center space-x-2 font-bold text-amber-400 text-sm">
                    <ShieldAlert className="w-4 h-4" />
                    <span>Affiliate Spam / Yellow-Basket Protection Engine</span>
                  </div>
                  <p className="leading-relaxed">
                    Thai TikTok hashtags like #ป้ายยา and #รีวิวบิวตี้ are flooded with automated or low-effort accounts that re-post product slides solely to earn 10% affiliate commissions via TikTok Shop (ตะกร้าเหลือง). Convert Cake's deterministic algorithm detects these accounts when yellow-basket ratios exceed 70% alongside poor view-to-follower retention, penalizing them 55 points so client budgets are never wasted.
                  </p>
                </div>

                {matchResponse.penalized_spam_kols.map(item => (
                  <div
                    key={item.kol.id}
                    className="bg-slate-900 border border-amber-500/30 rounded-2xl p-5 shadow-lg space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold text-[10px] border border-rose-500/30">
                            FLAGGED SPAM TRAP
                          </span>
                          <h4 className="font-bold text-white text-base">{item.kol.display_name}</h4>
                          <a
                            href={item.kol.tiktok_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-slate-400 hover:text-white font-mono flex items-center space-x-0.5"
                          >
                            <span>@{item.kol.handle}</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{item.kol.bio}</p>
                      </div>

                      <div className="text-right">
                        <span className="text-base font-extrabold text-amber-400">
                          {item.total_match_score.toFixed(1)} / 100
                        </span>
                        <span className="block text-[10px] text-rose-400 font-semibold">
                          -55 pts Penalty Applied
                        </span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950 border border-amber-500/20 text-xs text-amber-300 leading-relaxed">
                      <strong>Detection Trigger: </strong>
                      {item.score_breakdown.affiliate_spam_reason}
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center text-xs text-slate-400">
                      <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                        <span className="block text-[10px]">Yellow-Basket Ratio</span>
                        <span className="font-bold text-rose-400">
                          {Math.round(item.score_breakdown.yellow_basket_ratio * 100)}%
                        </span>
                      </div>
                      <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                        <span className="block text-[10px]">Median ER</span>
                        <span className="font-bold text-slate-300">
                          {item.score_breakdown.median_engagement_rate_pct.toFixed(1)}%
                        </span>
                      </div>
                      <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                        <span className="block text-[10px]">Views-to-Followers</span>
                        <span className="font-bold text-slate-300">
                          {item.score_breakdown.views_to_followers_ratio.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* TAB 3: WORKFLOW TRACE */}
            {matchResponse && activeTab === 'trace' && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                  <RefreshCw className="w-4 h-4 text-rose-400" />
                  <span>LangGraph Execution Nodes & State Transitions</span>
                </h4>
                <div className="space-y-2">
                  {matchResponse.workflow_trace.map((step, idx) => (
                    <div
                      key={idx}
                      className="flex items-start space-x-3 p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs font-mono text-slate-300"
                    >
                      <span className="text-emerald-400 font-bold shrink-0">[{idx + 1}]</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/60 py-6 text-center text-xs text-slate-500 mt-12">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>Built for Convert Cake AI Engineer Assessment • Thai Influencer Marketing Automation</p>
          <p>FastAPI • LangGraph • Next.js 16 • Apify TikTok Data Extractor • Multi-Signal AI Triangulation</p>
        </div>
      </footer>
    </div>
  );
}
