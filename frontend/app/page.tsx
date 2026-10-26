'use client';

import React, { useState, useEffect, useMemo } from 'react';
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
  ChevronDown,
  ChevronUp,
  Sliders,
  Info,
  Flame,
  Check,
  Copy,
  Eye,
  Heart,
  MessageSquare,
  Share2,
  ShoppingBag,
  Plus,
  Trash2,
  Briefcase,
  Layers,
  Globe,
  DollarSign,
  BarChart3,
  ArrowUpDown,
  FileText,
  SlidersHorizontal,
  Radio,
  Zap
} from 'lucide-react';

const API_BASE = '';

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

// Quick one-click testing chips
const SAMPLE_QUICK_TESTS = [
  {
    label: 'Her Hyness (Clean Skincare)',
    name: 'Her Hyness',
    url: 'https://herhyness.com',
    fb: 'https://facebook.com/herhyness',
    notes: 'Dermatological clean skincare for sensitive acne-prone Thai skin, price 400-900 THB',
  },
  {
    label: 'After You (Cafe & Dessert)',
    name: 'After You Dessert Cafe',
    url: 'https://afteryoudessertcafe.com',
    fb: 'https://facebook.com/afteryoucafe',
    notes: 'Bangkok trendy dessert cafe, Kakigori, Shibuya toast, young adult foodies',
  },
  {
    label: 'Bewell (Ergonomics & Tech)',
    name: 'Bewell Ergonomics',
    url: 'https://bewellstyle.com',
    fb: 'https://facebook.com/bewellhealth',
    notes: 'Ergonomic chairs, standing desks, pain-relief for Bangkok office workers WFH',
  },
];

export default function HomePage() {
  // Brand Input State (Initial empty, no mock pre-load!)
  const [brandName, setBrandName] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [facebookUrl, setFacebookUrl] = useState('');
  const [customNotes, setCustomNotes] = useState('');

  // Extracted Brand DNA State
  const [brandDNA, setBrandDNA] = useState<BrandDNA | null>(null);
  const [isEditingDNA, setIsEditingDNA] = useState(false);

  // Match State
  const [matchResponse, setMatchResponse] = useState<MatchResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'ranked' | 'spam' | 'trace'>('ranked');
  const [expandedKOLId, setExpandedKOLId] = useState<string | null>(null);

  // Shortlist Cart
  const [shortlist, setShortlist] = useState<RankedKOL[]>([]);
  const [copiedBrief, setCopiedBrief] = useState(false);

  // Filters & Sorting for Results
  const [searchQuery, setSearchQuery] = useState('');
  const [tierFilter, setTierFilter] = useState('All');
  const [sortBy, setSortBy] = useState<'score' | 'er' | 'followers'>('score');
  const [topK, setTopK] = useState(6);

  // Loading & Diagnostics
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [activeStep, setActiveStep] = useState<number>(0);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [copiedHook, setCopiedHook] = useState<string | null>(null);

  // Check API health on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then(res => res.json())
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);

  const fillQuickSample = (sample: typeof SAMPLE_QUICK_TESTS[0]) => {
    setBrandName(sample.name);
    setWebsiteUrl(sample.url);
    setFacebookUrl(sample.fb);
    setCustomNotes(sample.notes);
  };

  // Stage 1: Live Brand DNA Extraction
  const handleAnalyzeBrand = async () => {
    if (!brandName && !websiteUrl && !facebookUrl && !customNotes) {
      alert('Please enter at least a Brand Name, Website URL, or Campaign Notes.');
      return;
    }
    setIsAnalyzing(true);
    setMatchResponse(null);
    try {
      const res = await fetch(`${API_BASE}/api/analyze-brand`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: brandName || undefined,
          website_url: websiteUrl || undefined,
          facebook_url: facebookUrl || undefined,
          custom_notes: customNotes || undefined,
        }),
      });
      const data = await res.json();
      setBrandDNA(data);
    } catch (err) {
      console.error(err);
      alert('Failed to analyze brand. Ensure backend is running.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Stage 2: Match Live TikTok Creators
  const handleMatchKOLs = async () => {
    if (!brandDNA) return;
    setIsMatching(true);
    setActiveStep(1);

    const stepTimer = setInterval(() => {
      setActiveStep(prev => (prev < 4 ? prev + 1 : prev));
    }, 4500);

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
      setActiveTab('ranked');
    } catch (err) {
      console.error(err);
      alert('Live TikTok matching failed. Please verify APIFY_API_TOKEN.');
    } finally {
      clearInterval(stepTimer);
      setIsMatching(false);
      setActiveStep(0);
    }
  };

  // 1-Click Auto End-to-End Match
  const handleAutoMatch = async () => {
    if (!brandName && !websiteUrl && !facebookUrl && !customNotes) {
      alert('Please enter a Brand Name, Website URL, or select a quick test example.');
      return;
    }
    setIsMatching(true);
    setActiveStep(1);

    const stepTimer = setInterval(() => {
      setActiveStep(prev => (prev < 4 ? prev + 1 : prev));
    }, 5500);

    try {
      const res = await fetch(`${API_BASE}/api/auto-match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: brandName || undefined,
          website_url: websiteUrl || undefined,
          facebook_url: facebookUrl || undefined,
          custom_notes: customNotes || undefined,
          top_k: topK,
        }),
      });
      const data = await res.json();
      setBrandDNA(data.brand_dna);
      setMatchResponse(data);
      setActiveTab('ranked');
    } catch (err) {
      console.error(err);
      alert('Auto-matching failed. Please verify APIFY_API_TOKEN and backend.');
    } finally {
      clearInterval(stepTimer);
      setIsMatching(false);
      setActiveStep(0);
    }
  };

  const toggleShortlist = (item: RankedKOL) => {
    if (shortlist.some(s => s.kol.id === item.kol.id)) {
      setShortlist(shortlist.filter(s => s.kol.id !== item.kol.id));
    } else {
      setShortlist([...shortlist, item]);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHook(id);
    setTimeout(() => setCopiedHook(null), 2000);
  };

  // Filtered & Sorted Ranked List
  const filteredRankedKOLs = useMemo(() => {
    if (!matchResponse) return [];
    let list = [...matchResponse.ranked_kols];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        item =>
          item.kol.display_name.toLowerCase().includes(q) ||
          item.kol.handle.toLowerCase().includes(q) ||
          item.kol.bio.toLowerCase().includes(q) ||
          item.score_breakdown.matched_keywords.some(k => k.toLowerCase().includes(q))
      );
    }

    if (tierFilter !== 'All') {
      list = list.filter(item => item.kol.tier.toLowerCase().includes(tierFilter.toLowerCase()));
    }

    if (sortBy === 'er') {
      list.sort(
        (a, b) =>
          b.score_breakdown.median_engagement_rate_pct -
          a.score_breakdown.median_engagement_rate_pct
      );
    } else if (sortBy === 'followers') {
      list.sort((a, b) => b.kol.follower_count - a.kol.follower_count);
    } else {
      list.sort((a, b) => b.total_match_score - a.total_match_score);
    }

    return list;
  }, [matchResponse, searchQuery, tierFilter, sortBy]);

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
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `convert_cake_kol_recommendations_${brandDNA?.brand_name || 'brand'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const copyCampaignProposal = () => {
    if (shortlist.length === 0) return;
    const totalFollowers = shortlist.reduce((acc, curr) => acc + curr.kol.follower_count, 0);
    const avgER = (
      shortlist.reduce((acc, curr) => acc + curr.score_breakdown.median_engagement_rate_pct, 0) /
      shortlist.length
    ).toFixed(1);

    const summary = `📌 Convert Cake — Thai TikTok Influencer Campaign Proposal\n` +
      `Client: ${brandDNA?.brand_name || 'Brand'}\n` +
      `Vertical: ${brandDNA?.vertical || 'General'}\n` +
      `Selected Creators: ${shortlist.length} Influencers\n` +
      `Total Potential Reach: ${totalFollowers.toLocaleString()} Followers\n` +
      `Avg Median ER: ${avgER}%\n\n` +
      `--- Recommended KOLs & Pitch Hooks ---\n` +
      shortlist.map((item, idx) => 
        `${idx + 1}. ${item.kol.display_name} (@${item.kol.handle})\n` +
        `   • TikTok URL: ${item.kol.tiktok_url}\n` +
        `   • Match Score: ${item.total_match_score.toFixed(1)}/100 | Tier: ${item.kol.tier}\n` +
        `   • Est Rate: ${item.kol.estimated_rate_thb}\n` +
        `   • Primary Hook: "${item.thai_campaign_hooks[0] || ''}"\n`
      ).join('\n');

    navigator.clipboard.writeText(summary);
    setCopiedBrief(true);
    setTimeout(() => setCopiedBrief(false), 2500);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-rose-500 selection:text-white">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-rose-500 via-pink-500 to-amber-400 flex items-center justify-center font-bold text-white shadow-lg shadow-rose-500/25 shrink-0">
              CC
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold tracking-tight text-white">
                  Convert Cake
                </h1>
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center space-x-1">
                  <Radio className="w-2.5 h-2.5 animate-pulse text-rose-400" />
                  <span>Live TikTok Matcher (Thailand)</span>
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">
                Apify Live Actor + Gemini 3.5 Flash Lite + Multi-Signal Scoring Engine
              </p>
            </div>
          </div>

          {/* Live Telemetry Status Pill */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-800/80 border border-slate-700/80">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  apiOnline === true
                    ? 'bg-emerald-400 shadow-sm shadow-emerald-400/80 animate-pulse'
                    : apiOnline === false
                    ? 'bg-rose-500'
                    : 'bg-amber-400'
                }`}
              />
              <span className="text-slate-200 font-semibold">
                {apiOnline === true
                  ? 'FastAPI & Apify Engine Ready'
                  : apiOnline === false
                  ? 'Engine Offline'
                  : 'Checking Engine...'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Intro Banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 p-6 shadow-xl">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5">
            <div className="space-y-1.5 max-w-3xl">
              <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-rose-400">
                <Sparkles className="w-4 h-4" />
                <span>Live TikTok Influencer Intelligence Engine</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                Live Thai TikTok KOL Discovery & Anti-Spam Matcher
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                Enter any Thai client website or brand brief. The engine crawls the site, extracts <strong>Brand DNA</strong> with Gemini 3.5 Flash Lite, searches <strong>live TikTok creators via Apify</strong>, and ranks them with a 3-part Hybrid Formula (<strong>45% Relevance</strong>, <strong>35% Engagement & Anti-Spam</strong>, <strong>20% Audience Demographics</strong>).
              </p>
            </div>

            <div className="flex sm:flex-col gap-2 shrink-0">
              <button
                onClick={handleAutoMatch}
                disabled={isMatching || isAnalyzing}
                className="px-5 py-3 rounded-xl bg-gradient-to-r from-rose-500 via-pink-500 to-rose-600 hover:from-rose-600 hover:to-pink-700 text-white font-bold text-xs sm:text-sm shadow-lg shadow-rose-500/25 transition flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
              >
                {isMatching ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Running Live Search...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 text-amber-300" />
                    <span>1-Click Live Auto Match</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* PIPELINE GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* LEFT COLUMN: Input & Brand DNA (5 Cols) */}
          <div className="lg:col-span-5 space-y-5">
            {/* Input Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-rose-500/20 text-rose-400 text-xs font-black">
                    1
                  </span>
                  <h3 className="font-bold text-white text-sm sm:text-base">Input Brand Information</h3>
                </div>
                <span className="text-[11px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                  Live Web Crawler
                </span>
              </div>

              {/* Quick Fill Test Chips */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Or Try Example Thai Brand URLs:
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {SAMPLE_QUICK_TESTS.map((s, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => fillQuickSample(s)}
                      className="text-left px-2.5 py-1.5 rounded-lg bg-slate-850 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white text-[11px] font-medium transition cursor-pointer"
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Real Inputs */}
              <div className="space-y-3 pt-2 border-t border-slate-800/80">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Brand Name
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={e => setBrandName(e.target.value)}
                    placeholder="e.g. Her Hyness / Srichand / After You"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-rose-500 transition"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-300 mb-1">
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
                    <label className="block text-[11px] font-semibold text-slate-300 mb-1">
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
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                    Campaign Focus & Target Audience Notes
                  </label>
                  <textarea
                    rows={2}
                    value={customNotes}
                    onChange={e => setCustomNotes(e.target.value)}
                    placeholder="Specific product lines, price points, target personas, or special campaign instructions..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-rose-500 transition"
                  />
                </div>
              </div>

              <button
                onClick={handleAnalyzeBrand}
                disabled={isAnalyzing || isMatching}
                className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-100 font-semibold text-xs transition flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
              >
                {isAnalyzing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-rose-400" />
                    <span>Crawling Live Web & Analyzing with Gemini...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5 text-rose-400" />
                    <span>Extract Brand DNA (Live Web & Gemini)</span>
                  </>
                )}
              </button>
            </div>

            {/* Extracted Brand DNA Card (Human-in-the-Loop) */}
            {brandDNA && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4 relative animate-in fade-in duration-300">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    <h3 className="font-bold text-white text-sm sm:text-base">Extracted Brand DNA</h3>
                  </div>
                  <button
                    onClick={() => setIsEditingDNA(!isEditingDNA)}
                    className="text-xs font-semibold text-rose-400 hover:text-rose-300 transition flex items-center space-x-1 cursor-pointer bg-rose-500/10 px-2.5 py-1 rounded-lg border border-rose-500/20"
                  >
                    <Sliders className="w-3 h-3" />
                    <span>{isEditingDNA ? 'Lock DNA' : 'Edit DNA'}</span>
                  </button>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-400 font-medium">Market Vertical:</span>
                      <span className="font-bold text-rose-400 px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/30">
                        {brandDNA.vertical}
                      </span>
                    </div>
                    <p className="text-slate-200 font-semibold">{brandDNA.sub_category}</p>
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
                      <p className="text-slate-200 bg-slate-950/80 p-2.5 rounded-xl border border-slate-800 leading-relaxed">
                        {brandDNA.target_audience}
                      </p>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                      <span className="text-slate-400 block text-[10px] font-medium">Price Positioning</span>
                      <span className="font-bold text-slate-200 text-xs mt-0.5 block">{brandDNA.price_positioning}</span>
                      <span className="text-slate-400 block text-[10px] mt-0.5">
                        ~{brandDNA.average_price_thb.toLocaleString()} THB
                      </span>
                    </div>
                    <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                      <span className="text-slate-400 block text-[10px] font-medium">Core Regions & Age</span>
                      <span className="font-bold text-slate-200 text-xs mt-0.5 block truncate">
                        {brandDNA.target_locations.slice(0, 2).join(', ')}
                      </span>
                      <span className="text-slate-400 block text-[10px] mt-0.5">
                        Age: {brandDNA.target_age_range}
                      </span>
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-400 font-medium block mb-1.5">Brand Tone & Archetype:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {brandDNA.brand_tone.map((tone, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 text-[11px] border border-slate-700 font-medium"
                        >
                          {tone}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-400 font-medium block mb-1.5">Live TikTok Search Hashtags:</span>
                    <div className="flex flex-wrap gap-1">
                      {brandDNA.thai_keywords.map((kw, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-300 text-[10px] border border-rose-500/20 font-mono"
                        >
                          #{kw}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Trigger Stage 2 Search */}
                <button
                  onClick={handleMatchKOLs}
                  disabled={isMatching}
                  className="w-full mt-3 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-xs sm:text-sm shadow-lg shadow-emerald-500/25 transition flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  {isMatching ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Querying Live TikTok via Apify...</span>
                    </>
                  ) : (
                    <>
                      <Target className="w-4 h-4" />
                      <span>Discover & Match Live TikTok Creators</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Results & Inspection (7 Cols) */}
          <div className="lg:col-span-7 space-y-4">
            {/* Results Filter Header */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-lg flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-black">
                    2
                  </span>
                  <h3 className="font-bold text-white text-sm sm:text-base">Creator Intelligence</h3>
                </div>

                {matchResponse && (
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-800 text-slate-200 border border-slate-700">
                    {filteredRankedKOLs.length} Matches
                  </span>
                )}
              </div>

              <div className="flex items-center space-x-2 flex-wrap">
                {/* Search Input */}
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Filter handle, bio..."
                    className="bg-slate-950 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-rose-500 w-32 sm:w-40"
                  />
                </div>

                {/* Tier Filter */}
                <select
                  value={tierFilter}
                  onChange={e => setTierFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
                >
                  <option value="All">All Tiers</option>
                  <option value="Nano">Nano</option>
                  <option value="Micro">Micro</option>
                  <option value="Mid">Mid-Tier</option>
                  <option value="Macro">Macro</option>
                </select>

                {/* Sort By */}
                <select
                  value={sortBy}
                  onChange={e => setSortBy(e.target.value as any)}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
                >
                  <option value="score">Sort: Match Score</option>
                  <option value="er">Sort: Highest ER%</option>
                  <option value="followers">Sort: Followers</option>
                </select>

                {matchResponse && (
                  <button
                    onClick={exportToCSV}
                    className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 transition flex items-center space-x-1.5 cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Export</span>
                  </button>
                )}
              </div>
            </div>

            {/* Loading Stepper Display */}
            {isMatching && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-6">
                <div className="relative flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full border-4 border-slate-800 border-t-rose-500 animate-spin flex items-center justify-center" />
                  <Radio className="w-6 h-6 text-rose-400 absolute animate-pulse" />
                </div>

                <div className="space-y-2 max-w-md mx-auto">
                  <h4 className="text-base font-bold text-white">Live TikTok Ingestion in Progress</h4>
                  <p className="text-xs text-slate-400">
                    Fetching real-time video telemetry and author profiles from TikTok via Apify Actor...
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 text-left text-xs max-w-xl mx-auto pt-2">
                  <div className={`p-2.5 rounded-xl border ${activeStep >= 1 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400'}`}>
                    <span className="block font-bold text-[10px]">Step 1</span>
                    <span>Brand DNA</span>
                  </div>
                  <div className={`p-2.5 rounded-xl border ${activeStep >= 2 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400'}`}>
                    <span className="block font-bold text-[10px]">Step 2</span>
                    <span>Apify Scraper</span>
                  </div>
                  <div className={`p-2.5 rounded-xl border ${activeStep >= 3 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400'}`}>
                    <span className="block font-bold text-[10px]">Step 3</span>
                    <span>Anti-Spam Filter</span>
                  </div>
                  <div className={`p-2.5 rounded-xl border ${activeStep >= 4 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400'}`}>
                    <span className="block font-bold text-[10px]">Step 4</span>
                    <span>Gemini Ranking</span>
                  </div>
                </div>
              </div>
            )}

            {/* Empty State before any search */}
            {!isMatching && !matchResponse && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center mx-auto text-slate-400">
                  <Search className="w-7 h-7 text-rose-400" />
                </div>
                <div className="space-y-1.5 max-w-sm mx-auto">
                  <h4 className="text-base font-bold text-white">Ready for Live Search</h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Enter client brand information on the left or select an example chip, then click <strong>Extract Brand DNA</strong> to start live influencer matching.
                  </p>
                </div>
              </div>
            )}

            {/* Nav Tabs for Results */}
            {!isMatching && matchResponse && (
              <>
                <div className="flex items-center space-x-2 border-b border-slate-800 pb-2 text-xs font-semibold">
                  <button
                    onClick={() => setActiveTab('ranked')}
                    className={`px-3 py-1.5 rounded-xl transition cursor-pointer ${
                      activeTab === 'ranked'
                        ? 'bg-rose-500 text-white shadow-md'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Top Ranked Matches ({matchResponse.ranked_kols.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('spam')}
                    className={`px-3 py-1.5 rounded-xl transition cursor-pointer flex items-center space-x-1.5 ${
                      activeTab === 'spam'
                        ? 'bg-amber-500 text-slate-950 font-bold shadow-md'
                        : 'text-amber-400 hover:bg-amber-500/10'
                    }`}
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>Anti-Spam Filter ({matchResponse.penalized_spam_kols.length})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('trace')}
                    className={`px-3 py-1.5 rounded-xl transition cursor-pointer ${
                      activeTab === 'trace'
                        ? 'bg-slate-700 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Pipeline Trace
                  </button>
                </div>

                {/* Telemetry Status Bar */}
                <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs text-slate-300 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Telemetry Source:</span>
                    <span className="font-semibold text-emerald-400">
                      {matchResponse.apify_enrichment_status}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-medium">
                    Evaluated {matchResponse.total_candidates_evaluated} candidates
                  </span>
                </div>

                {/* TAB 1: RANKED KOLS LIST */}
                {activeTab === 'ranked' && (
                  <div className="space-y-4">
                    {filteredRankedKOLs.map(item => {
                      const isExpanded = expandedKOLId === item.kol.id;
                      const isShortlisted = shortlist.some(s => s.kol.id === item.kol.id);

                      return (
                        <div
                          key={item.kol.id}
                          className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 shadow-lg transition space-y-4 relative"
                        >
                          {/* Top Header: Avatar, Names, Links & Total Score */}
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-start space-x-3.5">
                              {/* Real Avatar Photo */}
                              <div className="relative shrink-0">
                                <img
                                  src={item.kol.avatar_url || `https://api.dicebear.com/7.x/notionists/svg?seed=${item.kol.handle}`}
                                  alt={item.kol.display_name}
                                  className="w-12 h-12 rounded-2xl bg-slate-800 border border-slate-700 object-cover shadow-sm"
                                />
                                <span className="absolute -top-1.5 -left-1.5 flex items-center justify-center w-5 h-5 rounded-full bg-rose-500 text-white font-black text-[10px] shadow">
                                  #{item.rank}
                                </span>
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
                                    className="inline-flex items-center space-x-1 text-xs text-rose-400 hover:text-rose-300 font-mono bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/25 transition"
                                  >
                                    <span>@{item.kol.handle}</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                                <p className="text-xs text-slate-300 mt-1 line-clamp-1">{item.kol.bio}</p>
                                <div className="flex items-center space-x-2 text-xs text-slate-400 mt-1.5 flex-wrap">
                                  <span className="text-slate-200 font-semibold px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                                    {item.kol.tier}
                                  </span>
                                  <span>•</span>
                                  <span>{item.kol.follower_count.toLocaleString()} Followers</span>
                                  <span>•</span>
                                  <span className="text-emerald-400 font-semibold">
                                    Est: {item.kol.estimated_rate_thb}
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Total Score Badge & Shortlist Button */}
                            <div className="flex flex-col items-end space-y-2 shrink-0">
                              <div className="inline-flex items-baseline space-x-1 px-3 py-1 rounded-xl bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 text-emerald-400 font-black text-lg">
                                <span>{item.total_match_score.toFixed(1)}</span>
                                <span className="text-[11px] text-emerald-500 font-medium">/100</span>
                              </div>

                              <button
                                onClick={() => toggleShortlist(item)}
                                className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center space-x-1 transition cursor-pointer ${
                                  isShortlisted
                                    ? 'bg-emerald-500 text-white shadow-sm'
                                    : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
                                }`}
                              >
                                {isShortlisted ? (
                                  <>
                                    <Check className="w-3 h-3" />
                                    <span>Shortlisted</span>
                                  </>
                                ) : (
                                  <>
                                    <Plus className="w-3 h-3" />
                                    <span>Add to Brief</span>
                                  </>
                                )}
                              </button>
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
                                    width: `${item.score_breakdown.relevance_score_raw}%`,
                                  }}
                                />
                              </div>
                              <div className="flex justify-between text-[10px] text-slate-400">
                                <span>Vector Match</span>
                                <span className="text-rose-400 font-semibold">
                                  {item.score_breakdown.matched_keywords.length} tags matched
                                </span>
                              </div>
                            </div>

                            {/* Bar 2: Engagement Quality (35%) */}
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
                                    width: `${item.score_breakdown.engagement_score_raw}%`,
                                  }}
                                />
                              </div>
                              <div className="flex justify-between text-[10px] text-slate-400">
                                <span>
                                  Median ER:{' '}
                                  <strong className="text-emerald-400">
                                    {item.score_breakdown.median_engagement_rate_pct.toFixed(1)}%
                                  </strong>
                                </span>
                                <span>Retention: {item.score_breakdown.views_to_followers_ratio.toFixed(2)}x</span>
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
                                    width: `${item.score_breakdown.audience_score_raw}%`,
                                  }}
                                />
                              </div>
                              <div className="flex justify-between items-center text-[10px]">
                                <span className="text-slate-400">Triangulation</span>
                                <span
                                  className={`px-1.5 py-0.5 rounded font-bold text-[9px] ${
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

                          {/* Evidence Chips */}
                          <div className="space-y-1.5">
                            <span className="text-[11px] font-semibold text-slate-400 flex items-center space-x-1.5">
                              <Info className="w-3.5 h-3.5 text-slate-400" />
                              <span>Public Telemetry Evidence:</span>
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {item.score_breakdown.evidence_list.map((ev, i) => (
                                <span
                                  key={i}
                                  className="px-2.5 py-1 rounded-lg bg-slate-800/80 text-slate-300 text-[11px] border border-slate-700/80 leading-tight font-medium"
                                >
                                  {ev}
                                </span>
                              ))}
                            </div>
                          </div>

                          {/* Agency Strategic Rationale */}
                          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs leading-relaxed text-slate-300">
                            <strong className="text-slate-100 font-semibold">Agency Strategic Rationale: </strong>
                            {item.why_this_kol}
                          </div>

                          {/* Suggested Thai Campaign Hooks */}
                          {item.thai_campaign_hooks && item.thai_campaign_hooks.length > 0 && (
                            <div className="space-y-2 pt-1 border-t border-slate-800/70">
                              <span className="text-xs font-semibold text-rose-400 flex items-center space-x-1.5">
                                <Sparkles className="w-3.5 h-3.5" />
                                <span>Suggested Thai TikTok Campaign Hooks for Client Pitch:</span>
                              </span>
                              <div className="grid grid-cols-1 gap-1.5">
                                {item.thai_campaign_hooks.map((hook, hIdx) => {
                                  const hookId = `${item.kol.id}-${hIdx}`;
                                  return (
                                    <div
                                      key={hIdx}
                                      className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50 border border-slate-700/60 text-xs text-slate-200 group"
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

                          {/* Expand/Collapse Accordion for Video Telemetry */}
                          {item.kol.recent_videos && item.kol.recent_videos.length > 0 && (
                            <div className="pt-1 border-t border-slate-800/60">
                              <button
                                onClick={() => setExpandedKOLId(isExpanded ? null : item.kol.id)}
                                className="w-full py-2 rounded-xl bg-slate-800/40 hover:bg-slate-800 text-xs text-slate-300 font-semibold transition flex items-center justify-center space-x-2 cursor-pointer border border-slate-800"
                              >
                                <BarChart3 className="w-3.5 h-3.5 text-rose-400" />
                                <span>
                                  {isExpanded
                                    ? 'Hide Recent TikTok Videos & Audience Telemetry'
                                    : `Inspect Audited TikTok Videos (${item.kol.recent_videos.length}) & Comments`}
                                </span>
                                {isExpanded ? (
                                  <ChevronUp className="w-3.5 h-3.5" />
                                ) : (
                                  <ChevronDown className="w-3.5 h-3.5" />
                                )}
                              </button>

                              {isExpanded && (
                                <div className="mt-3 space-y-3 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs animate-in fade-in duration-300">
                                  <h5 className="font-bold text-white text-xs flex items-center space-x-2">
                                    <Eye className="w-3.5 h-3.5 text-rose-400" />
                                    <span>Recent Videos Audited by Scoring Engine:</span>
                                  </h5>

                                  <div className="space-y-2">
                                    {item.kol.recent_videos.map((vid, vIdx) => (
                                      <div
                                        key={vIdx}
                                        className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 space-y-1.5"
                                      >
                                        <div className="flex items-start justify-between gap-2">
                                          <p className="text-slate-200 text-xs font-medium line-clamp-1">
                                            {vid.caption || 'TikTok video clip'}
                                          </p>
                                          {vid.has_yellow_basket && (
                                            <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-bold border border-amber-500/30 shrink-0 flex items-center space-x-0.5">
                                              <ShoppingBag className="w-2.5 h-2.5" />
                                              <span>ตะกร้าเหลือง</span>
                                            </span>
                                          )}
                                        </div>

                                        <div className="flex items-center space-x-4 text-[11px] text-slate-400 font-mono flex-wrap">
                                          <span className="text-slate-200">{vid.views.toLocaleString()} views</span>
                                          <span>•</span>
                                          <span>{vid.likes.toLocaleString()} likes</span>
                                          <span>•</span>
                                          <span>{vid.comments.toLocaleString()} comments</span>
                                          <span>•</span>
                                          <span>{vid.shares.toLocaleString()} shares</span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>

                                  {/* Audience Comments */}
                                  {item.kol.sample_comments && item.kol.sample_comments.length > 0 && (
                                    <div className="pt-2 border-t border-slate-800/80">
                                      <h5 className="font-bold text-white text-xs mb-2 flex items-center space-x-2">
                                        <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
                                        <span>Audience Sentiment & Comment Samples:</span>
                                      </h5>
                                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                        {item.kol.sample_comments.map((cmt, cIdx) => (
                                          <div
                                            key={cIdx}
                                            className="p-2 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 text-[11px] italic"
                                          >
                                            "{cmt}"
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* TAB 2: ANTI-SPAM TRAPS */}
                {activeTab === 'spam' && (
                  <div className="space-y-4">
                    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs space-y-1.5">
                      <div className="flex items-center space-x-2 font-bold text-amber-400 text-sm">
                        <ShieldAlert className="w-4 h-4" />
                        <span>Affiliate Spam / Yellow-Basket Protection Engine</span>
                      </div>
                      <p className="leading-relaxed">
                        Thai TikTok hashtags like #ป้ายยา and #รีวิวบิวตี้ are heavily flooded with accounts that re-post low-effort product slides solely to earn 10% affiliate commissions via TikTok Shop (ตะกร้าเหลือง). Convert Cake detects these accounts when yellow-basket ratios exceed 70% alongside low view-to-follower retention, penalizing them 55 points to protect client advertising budgets.
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
                {activeTab === 'trace' && (
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
              </>
            )}
          </div>
        </div>
      </main>

      {/* CAMPAIGN SHORTLIST FLOATING BAR */}
      {shortlist.length > 0 && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-40 w-11/12 max-w-3xl bg-slate-900/95 border border-emerald-500/40 rounded-2xl p-4 shadow-2xl backdrop-blur flex items-center justify-between gap-4 animate-in slide-in-from-bottom duration-300">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-sm shrink-0">
              {shortlist.length}
            </div>
            <div>
              <h4 className="font-bold text-white text-xs sm:text-sm">
                Campaign Shortlist ({shortlist.length} Creators)
              </h4>
              <p className="text-[11px] text-slate-400">
                Projected Reach:{' '}
                <strong className="text-emerald-400 font-semibold">
                  {shortlist.reduce((acc, c) => acc + c.kol.follower_count, 0).toLocaleString()}
                </strong>{' '}
                followers
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={copyCampaignProposal}
              className="px-3.5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-xs transition flex items-center space-x-1.5 shadow-md cursor-pointer"
            >
              {copiedBrief ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Copied Proposal!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Pitch Proposal</span>
                </>
              )}
            </button>
            <button
              onClick={() => setShortlist([])}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition cursor-pointer"
              title="Clear shortlist"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
