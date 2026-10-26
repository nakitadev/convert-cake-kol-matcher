
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
  Zap,
  Award,
  CheckCircle,
  Play,
  PieChart
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
  // Brand Input State
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
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(errBody || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setBrandDNA(data);
    } catch (err: any) {
      console.error('Analyze brand error:', err);
      alert(`Analyze brand failed: ${err.message || 'Ensure backend is running.'}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleMatchKOLs = async () => {
    if (!brandDNA) return;
    setIsMatching(true);
    setActiveStep(1);

    const stepTimer = setInterval(() => {
      setActiveStep(prev => (prev < 4 ? prev + 1 : prev));
    }, 3500);

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
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(errBody || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setMatchResponse(data);
      setActiveTab('ranked');
    } catch (err: any) {
      console.error('Match KOLs error:', err);
      alert(`Live TikTok matching failed: ${err.message || 'Please verify APIFY_API_TOKEN.'}`);
    } finally {
      clearInterval(stepTimer);
      setIsMatching(false);
      setActiveStep(0);
    }
  };

  const handleAutoMatch = async () => {
    if (!brandName && !websiteUrl && !facebookUrl && !customNotes) {
      alert('Please enter a Brand Name, Website URL, or select a quick test example.');
      return;
    }
    setIsMatching(true);
    setActiveStep(1);

    const stepTimer = setInterval(() => {
      setActiveStep(prev => (prev < 4 ? prev + 1 : prev));
    }, 3500);

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
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(errBody || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setBrandDNA(data.brand_dna);
      setMatchResponse(data);
      setActiveTab('ranked');
    } catch (err: any) {
      console.error('Auto-match error:', err);
      alert(`Auto-matching error: ${err.message || 'Please verify APIFY_API_TOKEN and backend.'}`);
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
        `   • Est Commercial Rate: ${item.kol.estimated_rate_thb}\n` +
        `   • Primary Hook: "${item.thai_campaign_hooks[0] || ''}"\n`
      ).join('\n');

    navigator.clipboard.writeText(summary);
    setCopiedBrief(true);
    setTimeout(() => setCopiedBrief(false), 2500);
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans selection:bg-[#0536d2] selection:text-white">
      {/* TOP CONVERT CAKE BRAND HEADER */}
      <header className="border-b border-slate-200/90 bg-white/95 backdrop-blur-md sticky top-0 z-50 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            {/* Official Convert Cake Monogram */}
            <div className="relative flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-[#0536d2] via-[#0428a8] to-[#020027] border border-[#597ef3]/40 shadow-[0_0_20px_rgba(5,54,210,0.35)] shrink-0">
              <span className="text-base font-black tracking-tighter text-white font-mono">CC</span>
              <span className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-[#03e78b] border-2 border-white shadow-sm" />
            </div>

            <div>
              <div className="flex items-center space-x-2.5">
                <h1 className="text-xl font-black tracking-tight text-slate-950 flex items-center space-x-1">
                  <span className="text-slate-950">CONVERT</span>
                  <span className="text-[#0536d2]">CAKE</span>
                </h1>
                <span className="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-blue-50 text-[#0536d2] border border-blue-200 flex items-center space-x-1.5">
                  <Radio className="w-2.5 h-2.5 animate-pulse text-[#0536d2]" />
                  <span>Performance TikTok Matcher</span>
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                The Performance-Only Agency · Real-time Apify Scraper & Gemini 3.5 Flash Lite
              </p>
            </div>
          </div>

          {/* Live System Health Pill */}
          <div className="flex items-center space-x-3">
            <div className="hidden md:flex items-center space-x-3 text-xs text-slate-400 pr-2 border-r border-slate-200/90">
              <span className="flex items-center space-x-1">
                <Award className="w-3.5 h-3.5 text-[#597ef3]" />
                <span>Official TikTok Partner Standard</span>
              </span>
            </div>

            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-50 border border-slate-200">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  apiOnline === true
                    ? 'bg-[#03e78b] shadow-[0_0_8px_#03e78b] animate-pulse'
                    : apiOnline === false
                    ? 'bg-rose-500'
                    : 'bg-amber-400'
                }`}
              />
              <span className="text-slate-200 font-semibold">
                {apiOnline === true
                  ? 'FastAPI & Apify Ready'
                  : apiOnline === false
                  ? 'Engine Offline'
                  : 'Checking Engine...'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* MAIN DASHBOARD CONTAINER */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* AGENCY HERO BANNER */}
        <div className="relative overflow-hidden rounded-3xl bg-white border border-slate-200/90 p-6 sm:p-8 shadow-xs">
          <div className="absolute -top-24 -left-24 w-72 h-72 bg-blue-50/60 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -right-24 w-72 h-72 bg-slate-100/60 rounded-full blur-2xl pointer-events-none" />

          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2.5 max-w-3xl">
              <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#0536d2] bg-blue-50 border border-blue-200/80 px-3 py-1 rounded-full">
                <Sparkles className="w-3.5 h-3.5 text-[#03e78b]" />
                <span>Built for Brands That Need Results, Not Reports</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-slate-950 tracking-tight leading-snug">
                Live Thai TikTok KOL Discovery & Anti-Spam Intelligence
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
                Enter any client website or campaign brief. Our engine crawls real web content, extracts <strong>Brand DNA</strong> with Gemini 3.5 Flash Lite, searches <strong>live TikTok creators via Apify</strong>, and calculates a 3-part Hybrid Match Score (<strong>45% Relevance</strong>, <strong>35% Engagement & Spam Filter</strong>, <strong>20% Demographics</strong>) designed to maximize ROAS for performance campaigns.
              </p>

              <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-slate-400 font-medium">
                <span className="flex items-center space-x-1.5 text-slate-300">
                  <CheckCircle className="w-4 h-4 text-[#03e78b]" />
                  <span>100% Pure Live Scrape (No Mocks)</span>
                </span>
                <span>•</span>
                <span className="flex items-center space-x-1.5 text-slate-300">
                  <ShieldCheck className="w-4 h-4 text-[#597ef3]" />
                  <span>Anti-Spam ตะกร้าเหลือง Defense</span>
                </span>
                <span>•</span>
                <span className="flex items-center space-x-1.5 text-slate-300">
                  <Zap className="w-4 h-4 text-amber-400" />
                  <span>AI Thai Campaign Pitch Hooks</span>
                </span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row lg:flex-col gap-3 shrink-0">
              <button
                onClick={handleAutoMatch}
                disabled={isMatching || isAnalyzing}
                className="px-6 py-3.5 rounded-2xl bg-gradient-to-r from-[#0536d2] via-[#0436d1] to-[#597ef3] hover:from-[#042cae] hover:to-[#456ce4] text-white font-bold text-sm shadow-[0_0_25px_rgba(5,54,210,0.45)] hover:shadow-[0_0_35px_rgba(5,54,210,0.65)] transition-all flex items-center justify-center space-x-2.5 disabled:opacity-50 cursor-pointer border border-[#597ef3]/30"
              >
                {isMatching ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-white" />
                    <span>Running Live Search...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 text-[#03e78b]" />
                    <span>1-Click Live Auto Match</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* 2-COLUMN MAIN WORKFLOW */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* LEFT COLUMN: Input & Extracted DNA (5 Cols) */}
          <div className="lg:col-span-5 space-y-5">
            {/* Input Form Card */}
            <div className="bg-white border border-slate-200/90 rounded-3xl p-5 sm:p-6 shadow-xs space-y-4 backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-slate-200/90 pb-3.5">
                <div className="flex items-center space-x-2.5">
                  <span className="flex items-center justify-center w-7 h-7 rounded-xl bg-[#0536d2]/20 text-[#597ef3] text-xs font-black border border-[#0536d2]/40">
                    1
                  </span>
                  <h3 className="font-bold text-slate-900 text-base">Input Brand Information</h3>
                </div>
                <span className="text-[11px] font-bold text-[#03e78b] bg-[#03e78b]/10 border border-[#03e78b]/25 px-2.5 py-0.5 rounded-full flex items-center space-x-1">
                  <Globe className="w-3 h-3" />
                  <span>Live Web Crawler</span>
                </span>
              </div>

              {/* Sample Brand Chips */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Quick Test With Real Thai Brands:
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {SAMPLE_QUICK_TESTS.map((s, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => fillQuickSample(s)}
                      className="text-left px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 text-slate-700 hover:text-[#0536d2] text-xs font-medium transition cursor-pointer flex items-center space-x-1.5"
                    >
                      <span>{s.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Input Fields */}
              <div className="space-y-3 pt-2 border-t border-slate-200/90/60">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Brand Name
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={e => setBrandName(e.target.value)}
                    placeholder="e.g. Her Hyness / Srichand / After You"
                    className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-500 focus:outline-none focus:border-[#597ef3] focus:ring-1 focus:ring-[#597ef3] transition"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Website URL
                    </label>
                    <input
                      type="text"
                      value={websiteUrl}
                      onChange={e => setWebsiteUrl(e.target.value)}
                      placeholder="https://..."
                      className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-500 focus:outline-none focus:border-[#597ef3] focus:ring-1 focus:ring-[#597ef3] transition"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Facebook Page URL
                    </label>
                    <input
                      type="text"
                      value={facebookUrl}
                      onChange={e => setFacebookUrl(e.target.value)}
                      placeholder="https://facebook.com/..."
                      className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-500 focus:outline-none focus:border-[#597ef3] focus:ring-1 focus:ring-[#597ef3] transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Campaign Focus & Target Audience Notes
                  </label>
                  <textarea
                    rows={2}
                    value={customNotes}
                    onChange={e => setCustomNotes(e.target.value)}
                    placeholder="Specific product lines, price points, target personas, or special campaign instructions..."
                    className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-500 focus:outline-none focus:border-[#597ef3] focus:ring-1 focus:ring-[#597ef3] transition"
                  />
                </div>
              </div>

              <button
                onClick={handleAnalyzeBrand}
                disabled={isAnalyzing || isMatching}
                className="w-full py-3 rounded-2xl bg-slate-900 hover:bg-slate-800 border border-slate-900 text-white font-semibold text-xs transition flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50 shadow-md"
              >
                {isAnalyzing ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-[#597ef3]" />
                    <span>Crawling Live Web & Analyzing with Gemini...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4 text-[#597ef3]" />
                    <span>Extract Brand DNA (Live Web & Gemini)</span>
                  </>
                )}
              </button>
            </div>

            {/* Extracted Brand DNA Card */}
            {brandDNA && (
              <div className="bg-white border border-slate-200/90 rounded-3xl p-5 sm:p-6 shadow-xs space-y-4 backdrop-blur-md animate-in fade-in duration-300">
                <div className="flex items-center justify-between border-b border-slate-200/90 pb-3.5">
                  <div className="flex items-center space-x-2.5">
                    <CheckCircle2 className="w-5 h-5 text-[#03e78b]" />
                    <h3 className="font-bold text-slate-900 text-base">Extracted Brand DNA</h3>
                  </div>
                  <button
                    onClick={() => setIsEditingDNA(!isEditingDNA)}
                    className="text-xs font-semibold text-[#597ef3] hover:text-white transition flex items-center space-x-1 cursor-pointer bg-[#0536d2]/15 px-3 py-1 rounded-xl border border-[#0536d2]/30"
                  >
                    <Sliders className="w-3 h-3" />
                    <span>{isEditingDNA ? 'Lock DNA' : 'Edit DNA'}</span>
                  </button>
                </div>

                <div className="space-y-3.5 text-xs">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-400 font-medium">Market Vertical:</span>
                      <span className="font-bold text-[#597ef3] px-2.5 py-0.5 rounded-lg bg-[#0536d2]/20 border border-[#0536d2]/35">
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
                        className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none"
                      />
                    ) : (
                      <p className="text-slate-800 bg-slate-50 p-3 rounded-2xl border border-slate-200 leading-relaxed">
                        {brandDNA.target_audience}
                      </p>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2.5 pt-1">
                    <div className="bg-slate-50 p-3 rounded-2xl border border-slate-200">
                      <span className="text-slate-400 block text-[10px] font-medium">Price Positioning</span>
                      <span className="font-bold text-slate-900 text-xs mt-0.5 block">{brandDNA.price_positioning}</span>
                      <span className="text-emerald-600 block text-[11px] font-mono mt-0.5 font-bold">
                        ~{brandDNA.average_price_thb.toLocaleString()} THB
                      </span>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-2xl border border-slate-200">
                      <span className="text-slate-400 block text-[10px] font-medium">Core Regions & Age</span>
                      <span className="font-bold text-slate-900 text-xs mt-0.5 block truncate">
                        {brandDNA.target_locations.slice(0, 2).join(', ')}
                      </span>
                      <span className="text-slate-400 block text-[11px] mt-0.5">
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
                          className="px-2.5 py-0.5 rounded-lg bg-slate-50 text-slate-700 text-[11px] border border-slate-200 font-medium"
                        >
                          {tone}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-400 font-medium block mb-1.5">Live TikTok Search Hashtags:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {brandDNA.thai_keywords.map((kw, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-0.5 rounded-full bg-[#0536d2]/15 text-[#597ef3] text-[11px] border border-[#597ef3]/30 font-mono font-medium"
                        >
                          #{kw}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <button
                  onClick={handleMatchKOLs}
                  disabled={isMatching}
                  className="w-full mt-3 py-3.5 rounded-2xl bg-gradient-to-r from-[#0536d2] via-[#0436d1] to-[#597ef3] hover:from-[#042cae] hover:to-[#456ce4] text-white font-bold text-xs sm:text-sm shadow-[0_0_20px_rgba(5,54,210,0.35)] transition flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50 border border-[#597ef3]/30"
                >
                  {isMatching ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-white" />
                      <span>Querying Live TikTok via Apify...</span>
                    </>
                  ) : (
                    <>
                      <Target className="w-4 h-4 text-[#03e78b]" />
                      <span>Discover & Match Live TikTok Creators</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Results Dashboard (7 Cols) */}
          <div className="lg:col-span-7 space-y-4">
            {/* Filter Bar */}
            <div className="bg-white border border-slate-200/90 rounded-3xl p-4 sm:p-5 shadow-xs flex flex-wrap items-center justify-between gap-3 backdrop-blur-md">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <span className="flex items-center justify-center w-7 h-7 rounded-xl bg-[#03e78b]/20 text-[#03e78b] text-xs font-black border border-[#03e78b]/35">
                    2
                  </span>
                  <h3 className="font-bold text-slate-900 text-base">Creator Intelligence</h3>
                </div>

                {matchResponse && (
                  <span className="text-xs font-bold px-3 py-1 rounded-full bg-blue-50 text-[#0536d2] border border-blue-200">
                    {filteredRankedKOLs.length} Matches
                  </span>
                )}
              </div>

              <div className="flex items-center space-x-2 flex-wrap">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Filter handle, bio..."
                    className="bg-white border border-slate-200 rounded-2xl pl-8.5 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-[#597ef3] w-32 sm:w-44 transition"
                  />
                </div>

                <select
                  value={tierFilter}
                  onChange={e => setTierFilter(e.target.value)}
                  className="bg-white border border-slate-200 rounded-2xl px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-[#597ef3]"
                >
                  <option value="All">All Tiers</option>
                  <option value="Nano">Nano (&lt;50K)</option>
                  <option value="Micro">Micro (50K-250K)</option>
                  <option value="Mid">Mid-Tier (250K-1M)</option>
                  <option value="Macro">Macro (&gt;1M)</option>
                </select>

                <select
                  value={sortBy}
                  onChange={e => setSortBy(e.target.value as any)}
                  className="bg-white border border-slate-200 rounded-2xl px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-[#597ef3]"
                >
                  <option value="score">Sort: Match Score</option>
                  <option value="er">Sort: Highest ER%</option>
                  <option value="followers">Sort: Followers</option>
                </select>

                {matchResponse && (
                  <button
                    onClick={exportToCSV}
                    className="px-3.5 py-2 rounded-2xl bg-[#0d1945] hover:bg-[#122361] border border-[#2b3d87] text-xs font-semibold text-white transition flex items-center space-x-1.5 cursor-pointer shadow-sm"
                  >
                    <Download className="w-3.5 h-3.5 text-[#03e78b]" />
                    <span>Export CSV</span>
                  </button>
                )}
              </div>
            </div>

            {/* Loading Stepper Display */}
            {isMatching && (
              <div className="bg-white border border-slate-200/90 rounded-3xl p-8 text-center space-y-6 shadow-xs backdrop-blur-md">
                <div className="relative flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full border-4 border-slate-200/90 border-t-[#0536d2] animate-spin flex items-center justify-center" />
                  <Radio className="w-6 h-6 text-[#03e78b] absolute animate-pulse" />
                </div>

                <div className="space-y-1.5 max-w-md mx-auto">
                  <h4 className="text-base font-bold text-slate-900">Live TikTok Crawling & Scoring Engine Active</h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Fetching real-time video telemetry and creator profiles directly from TikTok via Apify Actor...
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5 text-left text-xs max-w-xl mx-auto pt-2">
                  <div className={`p-3 rounded-2xl border ${activeStep >= 1 ? 'bg-blue-50 border-blue-200 text-[#0536d2] font-semibold' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                    <span className="block font-bold text-[10px]">Step 1</span>
                    <span className="font-semibold">Brand DNA</span>
                  </div>
                  <div className={`p-3 rounded-2xl border ${activeStep >= 2 ? 'bg-blue-50 border-blue-200 text-[#0536d2] font-semibold' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                    <span className="block font-bold text-[10px]">Step 2</span>
                    <span className="font-semibold">Apify Scraper</span>
                  </div>
                  <div className={`p-3 rounded-2xl border ${activeStep >= 3 ? 'bg-blue-50 border-blue-200 text-[#0536d2] font-semibold' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                    <span className="block font-bold text-[10px]">Step 3</span>
                    <span className="font-semibold">Anti-Spam Filter</span>
                  </div>
                  <div className={`p-3 rounded-2xl border ${activeStep >= 4 ? 'bg-blue-50 border-blue-200 text-[#0536d2] font-semibold' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                    <span className="block font-bold text-[10px]">Step 4</span>
                    <span className="font-semibold">Gemini Ranking</span>
                  </div>
                </div>
              </div>
            )}

            {/* Empty State before any search */}
            {!isMatching && !matchResponse && (
              <div className="bg-white border border-slate-200/90 rounded-3xl p-12 text-center space-y-4 shadow-xs backdrop-blur-md">
                <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto text-[#0536d2] shadow-xs">
                  <Search className="w-8 h-8 text-[#597ef3]" />
                </div>
                <div className="space-y-1.5 max-w-sm mx-auto">
                  <h4 className="text-base font-bold text-slate-900">Ready for Live Performance Match</h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Select an example Thai brand above or enter custom client URLs, then click <strong>Extract Brand DNA</strong> to discover high-converting TikTok creators.
                  </p>
                </div>
              </div>
            )}

            {/* Nav Tabs for Results */}
            {!isMatching && matchResponse && (
              <>
                <div className="flex items-center space-x-2 border-b border-slate-200/90 pb-2 text-xs font-semibold">
                  <button
                    onClick={() => setActiveTab('ranked')}
                    className={`px-4 py-2 rounded-2xl transition cursor-pointer flex items-center space-x-2 ${
                      activeTab === 'ranked'
                        ? 'bg-[#0536d2] text-white font-bold shadow-xs'
                        : 'text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200'
                    }`}
                  >
                    <span>Top Ranked Matches</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] bg-white/20 text-white font-bold">
                      {matchResponse.ranked_kols.length}
                    </span>
                  </button>
                  <button
                    onClick={() => setActiveTab('spam')}
                    className={`px-4 py-2 rounded-2xl transition cursor-pointer flex items-center space-x-1.5 ${
                      activeTab === 'spam'
                        ? 'bg-amber-500 text-slate-950 font-bold shadow-xs'
                        : 'text-amber-800 hover:bg-amber-100 bg-amber-50 border border-amber-200'
                    }`}
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>Anti-Spam Filter ({matchResponse.penalized_spam_kols.length})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('trace')}
                    className={`px-4 py-2 rounded-2xl transition cursor-pointer ${
                      activeTab === 'trace'
                        ? 'bg-slate-900 text-white font-bold shadow-xs'
                        : 'text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200'
                    }`}
                  >
                    Pipeline Trace
                  </button>
                </div>

                {/* Telemetry Status Bar */}
                <div className="p-3.5 rounded-2xl bg-white border border-slate-200/90 text-xs text-slate-300 flex items-center justify-between backdrop-blur">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="w-4 h-4 text-[#03e78b]" />
                    <span>Telemetry Source:</span>
                    <span className="font-semibold text-[#03e78b]">
                      {matchResponse.apify_enrichment_status}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-medium font-mono">
                    Evaluated {matchResponse.total_candidates_evaluated} Live Creators
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
                          className="bg-white border border-slate-200/90 hover:border-[#597ef3]/50 rounded-3xl p-5 sm:p-6 shadow-xs transition-all space-y-4 relative backdrop-blur-md"
                        >
                          {/* Top Header: Avatar, Names, Links & Total Score */}
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-start space-x-3.5">
                              {/* Avatar */}
                              <div className="relative shrink-0">
                                <img
                                  src={item.kol.avatar_url || `https://api.dicebear.com/7.x/notionists/svg?seed=${item.kol.handle}`}
                                  alt={item.kol.display_name}
                                  className="w-13 h-13 rounded-2xl bg-slate-100 border-2 border-slate-200 object-cover shadow-xs"
                                />
                                <span className="absolute -top-1.5 -left-1.5 flex items-center justify-center w-5 h-5 rounded-full bg-[#0536d2] text-white font-black text-[10px] shadow border border-[#597ef3]">
                                  #{item.rank}
                                </span>
                              </div>

                              <div>
                                <div className="flex items-center space-x-2 flex-wrap">
                                  <h4 className="font-bold text-slate-900 text-base hover:text-[#597ef3] transition">
                                    {item.kol.display_name}
                                  </h4>
                                  <a
                                    href={item.kol.tiktok_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center space-x-1 text-xs text-[#597ef3] hover:text-white font-mono bg-[#0536d2]/15 px-2.5 py-0.5 rounded-full border border-[#0536d2]/35 transition"
                                  >
                                    <span>@{item.kol.handle}</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                                <p className="text-xs text-slate-300 mt-1 line-clamp-1">{item.kol.bio}</p>
                                <div className="flex items-center space-x-2 text-xs text-slate-400 mt-1.5 flex-wrap font-medium">
                                  <span className="text-slate-700 font-semibold px-2 py-0.5 rounded-lg bg-slate-100 border border-slate-200">
                                    {item.kol.tier}
                                  </span>
                                  <span>•</span>
                                  <span className="font-mono">{item.kol.follower_count.toLocaleString()} Followers</span>
                                  <span>•</span>
                                  <span className="text-[#03e78b] font-semibold font-mono">
                                    Est Rate: {item.kol.estimated_rate_thb}
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Match Score Badge & Shortlist */}
                            <div className="flex flex-col items-end space-y-2 shrink-0">
                              <div className="inline-flex items-baseline space-x-1 px-3.5 py-1.5 rounded-2xl bg-gradient-to-r from-[#0536d2]/20 to-[#03e78b]/20 border border-[#03e78b]/40 text-[#03e78b] font-black text-lg shadow-[0_0_15px_rgba(3,231,139,0.2)]">
                                <span>{item.total_match_score.toFixed(1)}</span>
                                <span className="text-[10px] text-slate-400 font-medium">/100</span>
                              </div>

                              <button
                                onClick={() => toggleShortlist(item)}
                                className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer ${
                                  isShortlisted
                                    ? 'bg-[#03e78b] text-slate-950 shadow-sm font-bold'
                                    : 'bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-[#0536d2] border border-slate-200'
                                }`}
                              >
                                {isShortlisted ? (
                                  <>
                                    <Check className="w-3.5 h-3.5" />
                                    <span>Shortlisted</span>
                                  </>
                                ) : (
                                  <>
                                    <Plus className="w-3.5 h-3.5" />
                                    <span>Add to Brief</span>
                                  </>
                                )}
                              </button>
                            </div>
                          </div>

                          {/* 3-Part Hybrid Score Breakdown */}
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs">
                            {/* 1. Relevance (45%) */}
                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-400 font-medium">1. Brand Relevance</span>
                                <span className="font-bold text-slate-100 font-mono">
                                  {item.score_breakdown.relevance_weighted.toFixed(1)} / 45 pts
                                </span>
                              </div>
                              <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-[#0536d2] to-[#597ef3] rounded-full transition-all duration-500"
                                  style={{
                                    width: `${item.score_breakdown.relevance_score_raw}%`,
                                  }}
                                />
                              </div>
                              <div className="flex justify-between text-[10px] text-slate-400">
                                <span>Vector Similarity</span>
                                <span className="text-[#597ef3] font-semibold">
                                  {item.score_breakdown.matched_keywords.length} tags matched
                                </span>
                              </div>
                            </div>

                            {/* 2. Engagement Quality (35%) */}
                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-400 font-medium">2. Engagement Quality</span>
                                <span className="font-bold text-slate-100 font-mono">
                                  {item.score_breakdown.engagement_weighted.toFixed(1)} / 35 pts
                                </span>
                              </div>
                              <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-[#0428a8] to-[#03e78b] rounded-full transition-all duration-500"
                                  style={{
                                    width: `${item.score_breakdown.engagement_score_raw}%`,
                                  }}
                                />
                              </div>
                              <div className="flex justify-between text-[10px] text-slate-400">
                                <span>
                                  Median ER:{' '}
                                  <strong className="text-[#03e78b] font-mono">
                                    {item.score_breakdown.median_engagement_rate_pct.toFixed(1)}%
                                  </strong>
                                </span>
                                <span className="font-mono">Retention: {item.score_breakdown.views_to_followers_ratio.toFixed(2)}x</span>
                              </div>
                            </div>

                            {/* 3. Multi-Signal Demographics (20%) */}
                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-400 font-medium">3. Audience Signal</span>
                                <span className="font-bold text-slate-100 font-mono">
                                  {item.score_breakdown.audience_weighted.toFixed(1)} / 20 pts
                                </span>
                              </div>
                              <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                                <div
                                  className="h-full bg-[#03e78b] rounded-full transition-all duration-500"
                                  style={{
                                    width: `${item.score_breakdown.audience_score_raw}%`,
                                  }}
                                />
                              </div>
                              <div className="flex justify-between items-center text-[10px] gap-1.5 min-w-0">
                                <span className="text-slate-400 truncate">Triangulation</span>
                                <span
                                  className={`px-2 py-0.5 rounded-full font-bold text-[9px] shrink-0 whitespace-nowrap inline-flex items-center gap-1.5 ${
                                    item.score_breakdown.confidence_level === 'High'
                                      ? 'bg-[#03e78b]/15 text-[#03e78b] border border-[#03e78b]/30'
                                      : item.score_breakdown.confidence_level === 'Medium'
                                      ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                                      : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                                  }`}
                                >
                                  <span
                                    className={`w-1.5 h-1.5 rounded-full ${
                                      item.score_breakdown.confidence_level === 'High'
                                        ? 'bg-[#03e78b]'
                                        : item.score_breakdown.confidence_level === 'Medium'
                                        ? 'bg-amber-400'
                                        : 'bg-rose-400'
                                    }`}
                                  />
                                  <span>{item.score_breakdown.confidence_level} Conf.</span>
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Evidence Tags */}
                          <div className="space-y-1.5">
                            <span className="text-[11px] font-semibold text-slate-400 flex items-center space-x-1.5">
                              <Info className="w-3.5 h-3.5 text-[#597ef3]" />
                              <span>Live Telemetry Evidence:</span>
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {item.score_breakdown.evidence_list.map((ev, i) => (
                                <span
                                  key={i}
                                  className="px-2.5 py-1 rounded-xl bg-slate-50 text-slate-700 text-[11px] border border-slate-200 leading-tight font-medium"
                                >
                                  {ev}
                                </span>
                              ))}
                            </div>
                          </div>

                          {/* Strategic Rationale */}
                          <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200 text-xs leading-relaxed text-slate-800">
                            <strong className="text-white font-semibold flex items-center space-x-1.5 mb-1">
                              <Award className="w-3.5 h-3.5 text-[#597ef3]" />
                              <span>Convert Cake Performance Rationale:</span>
                            </strong>
                            {item.why_this_kol}
                          </div>

                          {/* Campaign Pitch Hooks */}
                          {item.thai_campaign_hooks && item.thai_campaign_hooks.length > 0 && (
                            <div className="space-y-2 pt-1 border-t border-slate-200/90/60">
                              <span className="text-xs font-semibold text-[#597ef3] flex items-center space-x-1.5">
                                <Sparkles className="w-3.5 h-3.5 text-[#03e78b]" />
                                <span>Suggested Thai TikTok Campaign Hooks (Ready for Pitch):</span>
                              </span>
                              <div className="grid grid-cols-1 gap-1.5">
                                {item.thai_campaign_hooks.map((hook, hIdx) => {
                                  const hookId = `${item.kol.id}-${hIdx}`;
                                  return (
                                    <div
                                      key={hIdx}
                                      className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-800 group"
                                    >
                                      <span className="pr-2 italic text-slate-800">{hook}</span>
                                      <button
                                        onClick={() => copyToClipboard(hook, hookId)}
                                        className="text-slate-400 hover:text-[#0536d2] transition p-1.5 cursor-pointer shrink-0 bg-white hover:bg-blue-50 rounded-lg border border-slate-200"
                                        title="Copy Hook"
                                      >
                                        {copiedHook === hookId ? (
                                          <Check className="w-3.5 h-3.5 text-[#03e78b]" />
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

                          {/* Audited Video Telemetry Drawer */}
                          {item.kol.recent_videos && item.kol.recent_videos.length > 0 && (
                            <div className="pt-1 border-t border-slate-200/90/60">
                              <button
                                onClick={() => setExpandedKOLId(isExpanded ? null : item.kol.id)}
                                className="w-full py-2.5 rounded-2xl bg-slate-50 hover:bg-slate-100 text-xs text-slate-700 font-semibold transition flex items-center justify-center space-x-2 cursor-pointer border border-slate-200"
                              >
                                <BarChart3 className="w-3.5 h-3.5 text-[#597ef3]" />
                                <span>
                                  {isExpanded
                                    ? 'Hide Audited TikTok Videos & Audience Telemetry'
                                    : `Inspect Audited TikTok Videos (${item.kol.recent_videos.length}) & Comments`}
                                </span>
                                {isExpanded ? (
                                  <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                                ) : (
                                  <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                                )}
                              </button>

                              {isExpanded && (
                                <div className="mt-3 space-y-3 bg-slate-50 p-4 sm:p-5 rounded-2xl border border-slate-200 text-xs animate-in fade-in duration-300">
                                  <h5 className="font-bold text-white text-xs flex items-center space-x-2">
                                    <Eye className="w-3.5 h-3.5 text-[#597ef3]" />
                                    <span>Recent Videos Audited by Scoring Engine:</span>
                                  </h5>

                                  <div className="space-y-2">
                                    {item.kol.recent_videos.map((vid, vIdx) => (
                                      <div
                                        key={vIdx}
                                        className="p-3 rounded-xl bg-white border border-slate-200/90 space-y-1.5"
                                      >
                                        <div className="flex items-start justify-between gap-2">
                                          <p className="text-slate-900 text-xs font-medium line-clamp-1">
                                            {vid.caption || 'TikTok video clip'}
                                          </p>
                                          {vid.has_yellow_basket && (
                                            <span className="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 text-[10px] font-bold border border-amber-500/30 shrink-0 flex items-center space-x-1">
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
                                    <div className="pt-2 border-t border-slate-200/90">
                                      <h5 className="font-bold text-white text-xs mb-2 flex items-center space-x-2">
                                        <MessageSquare className="w-3.5 h-3.5 text-[#03e78b]" />
                                        <span>Audience Comments & Sentiment:</span>
                                      </h5>
                                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                        {item.kol.sample_comments.map((cmt, cIdx) => (
                                          <div
                                            key={cIdx}
                                            className="p-2.5 rounded-xl bg-white border border-slate-200 text-slate-700 text-[11px] italic shadow-2xs"
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
                    <div className="p-5 rounded-3xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs space-y-2">
                      <div className="flex items-center space-x-2 font-bold text-amber-400 text-sm">
                        <ShieldAlert className="w-4 h-4" />
                        <span>Affiliate Spam / Yellow-Basket Protection Engine</span>
                      </div>
                      <p className="leading-relaxed">
                        Thai TikTok hashtags like #ป้ายยา and #รีวิวบิวตี้ are flooded with accounts that re-post low-effort product slides solely to earn 10% affiliate commissions via TikTok Shop (ตะกร้าเหลือง). Convert Cake detects these accounts when yellow-basket ratios exceed 70% alongside low view-to-follower retention, penalizing them 55 points to safeguard client media spend.
                      </p>
                    </div>

                    {matchResponse.penalized_spam_kols.map(item => (
                      <div
                        key={item.kol.id}
                        className="bg-white border border-amber-300 rounded-3xl p-5 sm:p-6 shadow-xs space-y-3"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-400 font-bold text-[10px] border border-rose-500/30">
                                FLAGGED SPAM TRAP
                              </span>
                              <h4 className="font-bold text-slate-900 text-base">{item.kol.display_name}</h4>
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
                            <span className="text-base font-extrabold text-amber-400 font-mono">
                              {item.total_match_score.toFixed(1)} / 100
                            </span>
                            <span className="block text-[10px] text-rose-400 font-semibold">
                              -55 pts Penalty Applied
                            </span>
                          </div>
                        </div>

                        <div className="p-3 rounded-2xl bg-amber-50/60 border border-amber-200 text-xs text-amber-900 leading-relaxed">
                          <strong>Detection Trigger: </strong>
                          {item.score_breakdown.affiliate_spam_reason}
                        </div>

                        <div className="grid grid-cols-3 gap-2 text-center text-xs text-slate-400 font-mono">
                          <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                            <span className="block text-[10px] text-slate-400">Yellow-Basket Ratio</span>
                            <span className="font-bold text-rose-400 text-sm">
                              {Math.round(item.score_breakdown.yellow_basket_ratio * 100)}%
                            </span>
                          </div>
                          <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                            <span className="block text-[10px] text-slate-400">Median ER</span>
                            <span className="font-bold text-slate-200 text-sm">
                              {item.score_breakdown.median_engagement_rate_pct.toFixed(1)}%
                            </span>
                          </div>
                          <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                            <span className="block text-[10px] text-slate-400">Views-to-Followers</span>
                            <span className="font-bold text-slate-200 text-sm">
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
                  <div className="bg-white border border-slate-200/90 rounded-3xl p-5 sm:p-6 shadow-xs space-y-4 backdrop-blur-md">
                    <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                      <RefreshCw className="w-4 h-4 text-[#597ef3]" />
                      <span>LangGraph Execution Nodes & State Transitions</span>
                    </h4>
                    <div className="space-y-2">
                      {matchResponse.workflow_trace.map((step, idx) => (
                        <div
                          key={idx}
                          className="flex items-start space-x-3 p-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700"
                        >
                          <span className="text-[#03e78b] font-bold shrink-0">[{idx + 1}]</span>
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

      {/* CAMPAIGN SHORTLIST FLOATING DRAWER */}
      {shortlist.length > 0 && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-40 w-11/12 max-w-3xl bg-slate-950/95 border border-slate-800 rounded-3xl p-4 shadow-2xl backdrop-blur-xl flex items-center justify-between gap-4 animate-in slide-in-from-bottom duration-300 text-white">
          <div className="flex items-center space-x-3.5">
            <div className="w-11 h-11 rounded-2xl bg-[#0536d2] text-white flex items-center justify-center font-black text-sm shrink-0 font-mono shadow-md">
              {shortlist.length}
            </div>
            <div>
              <h4 className="font-bold text-white text-xs sm:text-sm">
                Campaign Shortlist ({shortlist.length} Creators)
              </h4>
              <p className="text-[11px] text-slate-400">
                Projected Potential Reach:{' '}
                <strong className="text-[#03e78b] font-semibold font-mono">
                  {shortlist.reduce((acc, c) => acc + c.kol.follower_count, 0).toLocaleString()}
                </strong>{' '}
                followers
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={copyCampaignProposal}
              className="px-5 py-2.5 rounded-2xl bg-[#0536d2] hover:bg-[#042cae] active:bg-[#031f7a] text-white font-bold text-xs transition flex items-center space-x-1.5 shadow-md shadow-blue-600/30 cursor-pointer border border-blue-500"
            >
              {copiedBrief ? (
                <>
                  <Check className="w-4 h-4 text-white" />
                  <span>Copied Proposal!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 text-white" />
                  <span>Copy Pitch Proposal</span>
                </>
              )}
            </button>
            <button
              onClick={() => setShortlist([])}
              className="p-2.5 rounded-2xl bg-slate-900 hover:bg-rose-950/40 text-slate-400 hover:text-rose-400 border border-slate-800 transition cursor-pointer"
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
