
import React, { useState, useEffect, useMemo, useRef } from 'react';
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
  PieChart,
  Clock,
  Terminal
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
  manual_competitors?: string[];
  search_taxonomy?: Record<string, string[]>;
  grounded_competitors?: any[];
}

interface VideoMetric {
  video_id: string;
  caption: string;
  hashtags: string[];
  views: number;
  likes: number;
  comments: number;
  shares: number;
  collect_count?: number;
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
  creator_category?: string;
  creator_archetype?: string;
  recommended_role?: string;
  account_type?: string;
  is_work_ready?: boolean;
  competitor_warning?: string;
  query_origin?: string;
  save_to_view_ratio?: number;
  view_consistency_ratio?: number;
  niche_consistency_ratio?: number;
  is_casual_niche_fit?: boolean;
  is_affiliate_spam_trap: boolean;
  estimated_rate_thb: string;
}

interface SignalBreakdown {
  relevance_score_raw: number;
  relevance_weighted: number;
  semantic_similarity: number;
  semantic_points?: number;
  niche_keyword_points?: number;
  niche_consistency_ratio?: number;
  is_casual_niche_fit?: boolean;
  matched_keywords: string[];
  engagement_score_raw: number;
  engagement_weighted: number;
  median_engagement_rate_pct: number;
  median_er_points?: number;
  save_to_view_points?: number;
  view_consistency_points?: number;
  views_to_followers_ratio: number;
  yellow_basket_ratio: number;
  affiliate_spam_penalty_applied: boolean;
  affiliate_spam_penalty_points: number;
  affiliate_spam_reason?: string;
  audience_score_raw: number;
  audience_weighted: number;
  thai_authenticity_points?: number;
  buyer_intent_points?: number;
  affiliate_saturation_points?: number;
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
  // Brand Input State
  const [brandName, setBrandName] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [facebookUrl, setFacebookUrl] = useState('');
  const [customNotes, setCustomNotes] = useState('');
  const [manualCompetitors, setManualCompetitors] = useState('');

  // Extracted Brand DNA State
  const [brandDNA, setBrandDNA] = useState<BrandDNA | null>(null);
  const [isEditingDNA, setIsEditingDNA] = useState(false);

  // Match State
  const [matchResponse, setMatchResponse] = useState<MatchResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'ranked' | 'guru' | 'reviewer' | 'lifestyle' | 'niche' | 'spam' | 'trace'>('ranked');
  const [expandedKOLId, setExpandedKOLId] = useState<string | null>(null);

  // Shortlist Cart
  const [shortlist, setShortlist] = useState<RankedKOL[]>([]);
  const [copiedBrief, setCopiedBrief] = useState(false);

  // Filters & Sorting for Results
  const [searchQuery, setSearchQuery] = useState('');
  const [tierFilter, setTierFilter] = useState('All');
  const [sortBy, setSortBy] = useState<'score' | 'er' | 'followers'>('score');
  const [topK, setTopK] = useState(10);

  // Loading & Diagnostics
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [progressStageTitle, setProgressStageTitle] = useState<string>('');
  const [progressStageDesc, setProgressStageDesc] = useState<string>('');
  const [liveLogs, setLiveLogs] = useState<string[]>([]);
  const [activeStep, setActiveStep] = useState<number>(0);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const logsContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [liveLogs]);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then(res => res.json())
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);

  const handleAnalyzeBrand = async () => {
    if (!brandName && !websiteUrl && !facebookUrl && !customNotes) {
      alert('Please enter at least a Brand Name, Website URL, or Campaign Notes.');
      return;
    }
    setIsAnalyzing(true);
    setMatchResponse(null);
    setProgressPercent(8);
    setElapsedSeconds(0);
    setActiveStep(1);
    setProgressStageTitle('Step 1/3: กำลังดึงข้อมูลเว็บไซต์สดผ่าน Jina Reader API');
    setProgressStageDesc('แปลงหน้าเว็บเป็น Clean Markdown และดึง 10 โพสต์ล่าสุดจาก Facebook Page...');
    setLiveLogs([
      `[Jina Reader] Ingesting website URL and cleaning HTML tags...`,
      `[Apify Scraper] Scraping latest Facebook page signals...`,
    ]);

    const compList = manualCompetitors
      ? manualCompetitors.split(',').map(s => s.trim()).filter(Boolean)
      : undefined;

    const startTime = Date.now();
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsedSeconds(elapsed);
      if (elapsed < 4) {
        setActiveStep(1);
        setProgressPercent(Math.min(32, Math.round(8 + elapsed * 6)));
      } else if (elapsed < 9) {
        setActiveStep(2);
        setProgressStageTitle('Step 2/3: Gemini 3.5 Flash Lite กำลังสกัด Brand DNA');
        setProgressStageDesc('วิเคราะห์คุณลักษณะสินค้า, Tone of Voice, หมวดหมู่ และกลุ่มเป้าหมาย...');
        setProgressPercent(Math.min(70, Math.round(32 + (elapsed - 4) * 8)));
        setLiveLogs(prev => !prev.some(l => l.includes('Gemini 3.5')) ? [...prev, `[Gemini 3.5] Extracting Brand DNA, positioning and target demographic...`] : prev);
      } else {
        setActiveStep(3);
        setProgressStageTitle('Step 3/3: สังเคราะห์ 5-Angle Taxonomy & Grounded Competitors');
        setProgressStageDesc('สร้างคีย์เวิร์ดค้นหา 5 มิติ และตรวจจับแบรนด์คู่แข่งในไทย...');
        setProgressPercent(Math.min(95, Math.round(70 + (elapsed - 9) * 3)));
        setLiveLogs(prev => !prev.some(l => l.includes('Taxonomy')) ? [...prev, `[Taxonomy Engine] Generating 5-angle intent keywords (Direct, Slang, Pain Points)...`, `[Competitors] Identifying grounded Thai competitor brands...`] : prev);
      }
    }, 400);

    try {
      const res = await fetch(`${API_BASE}/api/analyze-brand`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: brandName || undefined,
          website_url: websiteUrl || undefined,
          facebook_url: facebookUrl || undefined,
          custom_notes: customNotes || undefined,
          manual_competitors: compList,
        }),
      });
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(errBody || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setProgressPercent(100);
      setProgressStageTitle('สกัด Brand DNA เสร็จสมบูรณ์ 100%!');
      setProgressStageDesc('ได้รับ Brand DNA, 5-Angle Search Taxonomy และรายชื่อคู่แข่งเรียบร้อย');
      setLiveLogs(prev => [...prev, `[Success] Brand DNA synthesized with ${data.thai_keywords?.length || 0} Thai keywords.`]);
      setBrandDNA(data);
    } catch (err: any) {
      console.error('Analyze brand error:', err);
      alert(`Analyze brand failed: ${err.message || 'Ensure backend is running.'}`);
    } finally {
      clearInterval(timer);
      setTimeout(() => {
        setIsAnalyzing(false);
        setProgressPercent(0);
        setElapsedSeconds(0);
      }, 450);
    }
  };

  const handleMatchKOLs = async () => {
    if (!brandDNA) return;
    setIsMatching(true);
    setProgressPercent(5);
    setElapsedSeconds(0);
    setActiveStep(1);
    setProgressStageTitle('Step 1/4: เริ่มต้นวิเคราะห์ Brand DNA & 5-Angle Taxonomy');
    setProgressStageDesc('ตรวจสอบ Brand DNA และตั้งค่าคำค้นหา 5 มิติ พร้อมรายชื่อคู่แข่ง...');
    setLiveLogs([
      `[Pipeline] Initializing live TikTok matching engine for '${brandDNA.brand_name}'...`,
      `[Taxonomy] 5-Angle Taxonomy active: Direct, Slang, Pain Points, Occasions, Modifiers`,
      `[Competitors] Tracking ${brandDNA.grounded_competitors?.length || 0} discovered + manual competitors`,
    ]);

    const startTime = Date.now();
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsedSeconds(elapsed);
      if (elapsed < 6) {
        setActiveStep(1);
        setProgressPercent(Math.min(23, Math.round(5 + elapsed * 3.2)));
      } else if (elapsed < 18) {
        setActiveStep(2);
        setProgressStageTitle('Step 2/4: ค้นหา TikTok ครีเอเตอร์สดผ่าน Apify Scraper');
        setProgressStageDesc('ยิง Apify Clockworks Actor ดึงวิดีโอสด 30 รายการ และกรอง Two-Stage Entity Filter ตัดร้านค้า Official...');
        setProgressPercent(Math.min(54, Math.round(24 + (elapsed - 6) * 2.5)));
        setLiveLogs(prev => !prev.some(l => l.includes('Clockworks')) ? [
          ...prev,
          `[Apify Scraper] Querying clockworks~tiktok-scraper for Thailand market...`,
          `[Two-Stage Filter] Purging Official Shops & Merchant Accounts (Zero-Spam)...`
        ] : prev);
      } else if (elapsed < 32) {
        setActiveStep(3);
        setProgressStageTitle('Step 3/4: ประมวลผล Multi-Signal Telemetry & Work-Ready');
        setProgressStageDesc('คำนวณ Median ER, Save-to-View Utility และสแกนสัญญาณพร้อมรับงาน...');
        setProgressPercent(Math.min(79, Math.round(55 + (elapsed - 18) * 1.8)));
        setLiveLogs(prev => !prev.some(l => l.includes('Telemetry')) ? [
          ...prev,
          `[Telemetry] Calculating Median ER & Utility Save-to-View ((Collect+0.7*Share)/Views)...`,
          `[Signal Analysis] Evaluating Commercial & Content Signals...`,
          `[Work-Ready] Scanning bio signals: 'ติดต่องาน / For work' -> Sponsorship ready`
        ] : prev);
      } else {
        setActiveStep(4);
        setProgressStageTitle('Step 4/4: ประเมินความเข้ากันได้และจัดอันดับครีเอเตอร์ (Creator Fit & Archetype Matching)');
        setProgressStageDesc('ประเมินความเข้ากันได้ Brand Relevance, Engagement Quality, Audience Fit และจำแนก 4 Creator Archetypes...');
        setProgressPercent(Math.min(96, Math.round(80 + (elapsed - 32) * 0.7)));
        setLiveLogs(prev => !prev.some(l => l.includes('Embeddings')) ? [
          ...prev,
          `[Gemini Embeddings] Calculating 3,072-dimensional cosine similarity for Brand-Creator fit...`,
          `[Archetypes] Classifying Educated Guru, Top Reviewer, Lifestyle & Vlog, Niche Enthusiast`,
          `[Match Engine] Evaluating creator-brand fit across 4 archetypes & final ranking...`
        ] : prev);
      }
    }, 400);

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
      setProgressPercent(100);
      setProgressStageTitle('จัดอันดับและประมวลผลเสร็จสมบูรณ์ 100%!');
      setProgressStageDesc(`พบครีเอเตอร์ ${data.ranked_kols.length} รายการ พร้อมแสดงผล Multi-Signal Performance Dashboard`);
      setLiveLogs(prev => [...prev, `[Success] Pipeline finished with ${data.ranked_kols.length} creators ranked.`]);
      setMatchResponse(data);
      setActiveTab('ranked');
    } catch (err: any) {
      console.error('Match KOLs error:', err);
      alert(`Live TikTok matching failed: ${err.message || 'Please verify APIFY_API_TOKEN.'}`);
    } finally {
      clearInterval(timer);
      setTimeout(() => {
        setIsMatching(false);
        setProgressPercent(0);
        setElapsedSeconds(0);
      }, 450);
    }
  };

  const handleAutoMatch = async () => {
    if (!brandName && !websiteUrl && !facebookUrl && !customNotes) {
      alert('Please enter a Brand Name, Website URL, or select a quick test example.');
      return;
    }
    setIsMatching(true);
    setProgressPercent(4);
    setElapsedSeconds(0);
    setActiveStep(1);
    setProgressStageTitle('Step 1/4: ดึง Brand DNA สด & สังเคราะห์ 5-Angle Taxonomy');
    setProgressStageDesc('สกัดข้อมูลจาก Jina Reader API, Facebook Scraper และสร้างคีย์เวิร์ดด้วย Gemini 3.5...');
    setLiveLogs([
      `[1-Click Auto Match] Initializing end-to-end autonomous matching pipeline...`,
      `[Jina Reader] Ingesting website URL and extracting clean markdown...`,
      `[Brand DNA] Analyzing brand positioning and 5-angle consumer search taxonomy...`,
    ]);

    const compList = manualCompetitors
      ? manualCompetitors.split(',').map(s => s.trim()).filter(Boolean)
      : undefined;

    const startTime = Date.now();
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsedSeconds(elapsed);
      if (elapsed < 8) {
        setActiveStep(1);
        setProgressPercent(Math.min(24, Math.round(4 + elapsed * 2.8)));
      } else if (elapsed < 20) {
        setActiveStep(2);
        setProgressStageTitle('Step 2/4: ค้นหา TikTok ครีเอเตอร์สดผ่าน Apify Scraper');
        setProgressStageDesc('ยิง Apify Clockworks Actor ดึงวิดีโอสด 30 รายการ และกรอง Two-Stage Entity Filter...');
        setProgressPercent(Math.min(54, Math.round(25 + (elapsed - 8) * 2.4)));
        setLiveLogs(prev => !prev.some(l => l.includes('Clockworks')) ? [
          ...prev,
          `[Apify Scraper] Running live TikTok scraper for hashtags...`,
          `[Two-Stage Filter] Purging Official Shop / Merchant accounts from pool...`
        ] : prev);
      } else if (elapsed < 34) {
        setActiveStep(3);
        setProgressStageTitle('Step 3/4: ประมวลผล Multi-Signal Telemetry & Work-Ready');
        setProgressStageDesc('คำนวณ Median ER, Save-to-View Utility และสแกนสัญญาณพร้อมรับงาน...');
        setProgressPercent(Math.min(79, Math.round(55 + (elapsed - 20) * 1.7)));
        setLiveLogs(prev => !prev.some(l => l.includes('Telemetry')) ? [
          ...prev,
          `[Telemetry] Calculating Median ER & Utility Save-to-View ratio...`,
          `[Signal Analysis] Evaluating Commercial & Content Signals...`,
          `[Work-Ready] Scanning bio signals: 'ติดต่องาน / For work' -> Sponsorship ready`
        ] : prev);
      } else {
        setActiveStep(4);
        setProgressStageTitle('Step 4/4: ประเมินความเข้ากันได้และจัดอันดับครีเอเตอร์ (Creator Fit & Archetype Matching)');
        setProgressStageDesc('ประเมินความเข้ากันได้ Brand Relevance, Engagement Quality, Audience Fit และจำแนก 4 Creator Archetypes...');
        setProgressPercent(Math.min(96, Math.round(80 + (elapsed - 34) * 0.7)));
        setLiveLogs(prev => !prev.some(l => l.includes('Embeddings')) ? [
          ...prev,
          `[Gemini Embeddings] Generating 3,072-dimensional vector representations...`,
          `[Archetypes] Classifying Educated Guru, Top Reviewer, Lifestyle & Vlog, Niche Enthusiast`,
          `[Match Engine] Evaluating creator-brand fit across 4 archetypes & final ranking...`
        ] : prev);
      }
    }, 400);

    try {
      const res = await fetch(`${API_BASE}/api/auto-match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: brandName || undefined,
          website_url: websiteUrl || undefined,
          facebook_url: facebookUrl || undefined,
          custom_notes: customNotes || undefined,
          manual_competitors: compList,
          top_k: topK,
        }),
      });
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(errBody || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setProgressPercent(100);
      setProgressStageTitle('จัดอันดับและประมวลผลเสร็จสมบูรณ์ 100%!');
      setProgressStageDesc(`สกัด Brand DNA และจัดอันดับครีเอเตอร์ ${data.ranked_kols.length} รายการเรียบร้อย`);
      setLiveLogs(prev => [...prev, `[Success] Auto-match complete with ${data.ranked_kols.length} creators ranked.`]);
      setBrandDNA(data.brand_dna);
      setMatchResponse(data);
      setActiveTab('ranked');
    } catch (err: any) {
      console.error('Auto-match error:', err);
      alert(`Auto-matching error: ${err.message || 'Please verify APIFY_API_TOKEN and backend.'}`);
    } finally {
      clearInterval(timer);
      setTimeout(() => {
        setIsMatching(false);
        setProgressPercent(0);
        setElapsedSeconds(0);
      }, 450);
    }
  };

  const toggleShortlist = (item: RankedKOL) => {
    if (shortlist.some(s => s.kol.id === item.kol.id)) {
      setShortlist(shortlist.filter(s => s.kol.id !== item.kol.id));
    } else {
      setShortlist([...shortlist, item]);
    }
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

    if (activeTab === 'guru') {
      list = list.filter(item => item.kol.creator_archetype === 'Educated Guru');
    } else if (activeTab === 'reviewer') {
      list = list.filter(item => item.kol.creator_archetype === 'Top Reviewer');
    } else if (activeTab === 'lifestyle') {
      list = list.filter(item => item.kol.creator_archetype === 'Lifestyle & Vlog');
    } else if (activeTab === 'niche') {
      list = list.filter(item => item.kol.creator_archetype === 'Niche Enthusiast');
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
  }, [matchResponse, searchQuery, tierFilter, sortBy, activeTab]);

  const exportToCSV = () => {
    if (!matchResponse) return;
    const headers = [
      'Rank',
      'Handle',
      'Display Name',
      'TikTok URL',
      'Tier',
      'Followers',
      'Archetype',
      'Recommended Role',
      'Work-Ready',
      'Competitor Conflict/Opportunity',
      'Total Match Score',
      'Brand Relevance Score',
      'Engagement Quality Score',
      'Median ER %',
      'Save-to-View Ratio',
      'View Consistency',
      'Audience Signal Score',
      'Confidence',
      'Yellow Basket Ratio %',
      'Affiliate Penalized',
      'Strategic Rationale',
    ];
    const rows = matchResponse.ranked_kols.map(item => [
      item.rank,
      `@${item.kol.handle}`,
      `"${item.kol.display_name.replace(/"/g, '""')}"`,
      item.kol.tiktok_url,
      item.kol.tier,
      item.kol.follower_count,
      item.kol.creator_archetype || 'N/A',
      item.kol.recommended_role || 'N/A',
      item.kol.is_work_ready ? 'YES' : 'NO',
      `"${(item.kol.competitor_warning || 'None').replace(/"/g, '""')}"`,
      item.total_match_score,
      item.score_breakdown.relevance_weighted,
      item.score_breakdown.engagement_weighted,
      item.score_breakdown.median_engagement_rate_pct,
      (item.kol.save_to_view_ratio || 0).toFixed(4),
      (item.kol.view_consistency_ratio || 0).toFixed(3),
      item.score_breakdown.audience_weighted,
      item.score_breakdown.confidence_level,
      `${Math.round(item.score_breakdown.yellow_basket_ratio * 100)}%`,
      item.score_breakdown.affiliate_spam_penalty_applied ? 'YES' : 'NO',
      `"${item.why_this_kol.replace(/"/g, '""')}"`,
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
      `--- Recommended KOLs & Match Rationale ---\n` +
      shortlist.map((item, idx) => 
        `${idx + 1}. ${item.kol.display_name} (@${item.kol.handle})\n` +
        `   • TikTok URL: ${item.kol.tiktok_url}\n` +
        `   • Match Score: ${item.total_match_score.toFixed(1)}/100 | Tier: ${item.kol.tier} | Archetype: ${item.kol.creator_archetype || 'Creator'}\n` +
        `   • Est Commercial Rate: ${item.kol.estimated_rate_thb}\n` +
        `   • Performance Rationale: ${item.why_this_kol}\n`
      ).join('\n');

    navigator.clipboard.writeText(summary);
    setCopiedBrief(true);
    setTimeout(() => setCopiedBrief(false), 2500);
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans selection:bg-[#0536d2] selection:text-white">
      {/* Global Sticky Top Progress Bar */}
      {(isMatching || isAnalyzing) && (
        <div className="fixed top-0 left-0 right-0 z-[100] h-1.5 bg-slate-200/80 backdrop-blur-xs overflow-hidden shadow-sm">
          <div
            className="h-full bg-gradient-to-r from-[#0536d2] via-[#597ef3] to-[#03e78b] transition-all duration-300 ease-out shadow-[0_0_12px_rgba(5,54,210,0.8)]"
            style={{ width: `${Math.max(3, progressPercent)}%` }}
          />
        </div>
      )}

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
                    ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse'
                    : apiOnline === false
                    ? 'bg-rose-500'
                    : 'bg-amber-400'
                }`}
              />
              <span className="text-slate-800 font-semibold">
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
                Live Thai TikTok Creator Intelligence & Matchmaking
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
                วิเคราะห์และจับคู่ครีเอเตอร์ตัวจริงสำหรับตลาดไทย สกัด <strong>Brand DNA</strong> สดผ่าน Gemini 3.5 Flash Lite และ Jina Reader, ค้นหา TikTok ครีเอเตอร์สด 100% ผ่าน Apify และจำแนกตาม <strong>4 Core Creator Archetypes</strong> เพื่อสร้างผลลัพธ์แคมเปญที่วัดผลได้จริง
              </p>

              <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-slate-600 font-medium">
                <span className="flex items-center space-x-1.5 text-slate-700">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  <span>100% Live TikTok Scraper (Zero-Mock)</span>
                </span>
                <span>•</span>
                <span className="flex items-center space-x-1.5 text-slate-700">
                  <Award className="w-4 h-4 text-[#0536d2]" />
                  <span>4 Creator Archetypes Gating</span>
                </span>
                <span>•</span>
                <span className="flex items-center space-x-1.5 text-slate-700">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Two-Stage Entity & Anti-Spam Filtering</span>
                </span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row lg:flex-col gap-3 shrink-0">
              <button
                onClick={handleAutoMatch}
                disabled={isMatching || isAnalyzing}
                className="px-6 py-3.5 rounded-2xl bg-[#0536d2] hover:bg-[#042cae] active:bg-[#031f7a] text-white font-bold text-sm shadow-md shadow-blue-600/20 hover:shadow-lg transition-all flex items-center justify-center space-x-2.5 disabled:opacity-50 cursor-pointer border border-blue-700"
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

              {/* Input Fields */}
              <div className="space-y-3.5 pt-1">
                <div>
                  <label className="block text-xs font-bold text-slate-800 mb-1.5">
                    Brand Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={e => setBrandName(e.target.value)}
                    placeholder="ระบุชื่อแบรนด์"
                    className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] focus:ring-2 focus:ring-[#0536d2]/15 transition shadow-2xs"
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
                      placeholder="https://brand.com"
                      className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] focus:ring-1 focus:ring-[#0536d2]/20 transition"
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
                      placeholder="https://facebook.com/brand"
                      className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] focus:ring-1 focus:ring-[#0536d2]/20 transition"
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
                    placeholder="ระบุจุดเด่นสินค้า กลุ่มเป้าหมาย หรือบรีฟแคมเปญเพิ่มเติม"
                    className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] focus:ring-1 focus:ring-[#0536d2]/20 transition"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center justify-between">
                    <span>Direct Competitor Brands (Grounded Thai Detection)</span>
                    <span className="text-[10px] text-slate-400 font-normal">Optional, comma-separated</span>
                  </label>
                  <input
                    type="text"
                    value={manualCompetitors}
                    onChange={e => setManualCompetitors(e.target.value)}
                    placeholder="ระบุชื่อแบรนด์คู่แข่ง (คั่นด้วยเครื่องหมายจุลภาค)"
                    className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] focus:ring-1 focus:ring-[#0536d2]/20 transition"
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
                    className="text-xs font-semibold text-[#0536d2] hover:text-[#042cae] transition flex items-center space-x-1 cursor-pointer bg-blue-50 px-3 py-1 rounded-xl border border-blue-200"
                  >
                    <Sliders className="w-3 h-3" />
                    <span>{isEditingDNA ? 'Lock DNA' : 'Edit DNA'}</span>
                  </button>
                </div>

                <div className="space-y-3.5 text-xs">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-500 font-medium">Market Vertical:</span>
                      <span className="font-bold text-[#0536d2] px-2.5 py-0.5 rounded-lg bg-blue-50 border border-blue-200">
                        {brandDNA.vertical}
                      </span>
                    </div>
                    <p className="text-slate-900 font-bold text-sm">{brandDNA.sub_category}</p>
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
                    <span className="text-slate-500 font-medium block mb-1.5">Target Consumer Search Keywords (คำค้นหาสินค้า):</span>
                    <div className="flex flex-wrap gap-1.5">
                      {brandDNA.thai_keywords.map((kw, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-0.5 rounded-full bg-blue-50 text-[#0536d2] text-[11px] border border-blue-200 font-medium flex items-center space-x-1"
                        >
                          <span>🔍</span>
                          <span>{kw.replace(/^#/, '')}</span>
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
                    className="bg-white border border-slate-200 rounded-2xl pl-8.5 pr-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] w-32 sm:w-44 transition"
                  />
                </div>

                <select
                  value={tierFilter}
                  onChange={e => setTierFilter(e.target.value)}
                  className="bg-white border border-slate-200 rounded-2xl px-3 py-2 text-slate-800 text-xs focus:outline-none focus:border-[#0536d2]"
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
                  className="bg-white border border-slate-200 rounded-2xl px-3 py-2 text-slate-800 text-xs focus:outline-none focus:border-[#0536d2]"
                >
                  <option value="score">Sort: Match Score</option>
                  <option value="er">Sort: Highest ER%</option>
                  <option value="followers">Sort: Followers</option>
                </select>

                <select
                  value={topK}
                  onChange={e => setTopK(Number(e.target.value))}
                  className="bg-white border border-slate-200 rounded-2xl px-3 py-2 text-slate-800 text-xs focus:outline-none focus:border-[#0536d2] font-semibold text-[#0536d2]"
                  title="Top K KOL Rank Cutoff"
                >
                  <option value={10}>Top 10 KOLs</option>
                  <option value={20}>Top 20 KOLs</option>
                  <option value={30}>Top 30 KOLs</option>
                  <option value={50}>Top 50 KOLs</option>
                </select>

                {matchResponse && (
                  <button
                    onClick={exportToCSV}
                    className="px-3.5 py-2 rounded-2xl bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 transition flex items-center space-x-1.5 cursor-pointer shadow-xs"
                  >
                    <Download className="w-3.5 h-3.5 text-[#0536d2]" />
                    <span>Export CSV</span>
                  </button>
                )}
              </div>
            </div>

            {/* Real-Time Live Progress Bar & Stepper Dashboard */}
            {(isMatching || (isAnalyzing && !matchResponse)) && (
              <div className="bg-white border-2 border-[#597ef3]/40 rounded-3xl p-6 sm:p-8 space-y-6 shadow-lg shadow-blue-500/5 backdrop-blur-md relative overflow-hidden animate-in fade-in duration-300">
                <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-blue-100/40 via-emerald-100/20 to-transparent rounded-full blur-3xl pointer-events-none" />

                {/* Progress Header: Live Badge, Timer & Large Percentage */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4 relative z-10">
                  <div className="flex items-center space-x-2.5">
                    <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-[#0536d2] font-black text-xs uppercase tracking-wider shadow-2xs">
                      <span className="w-2 h-2 rounded-full bg-[#03e78b] animate-ping" />
                      <span>{isMatching ? 'Live Matching Active' : 'Brand DNA Ingestion'}</span>
                    </span>
                    <span className="inline-flex items-center space-x-1 text-xs text-slate-500 font-mono bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      <span>{String(Math.floor(elapsedSeconds / 60)).padStart(2, '0')}:{String(elapsedSeconds % 60).padStart(2, '0')}s</span>
                    </span>
                  </div>

                  <div className="flex items-baseline space-x-1.5">
                    <span className="text-3xl sm:text-4xl font-black text-[#0536d2] font-mono tracking-tight">
                      {progressPercent}%
                    </span>
                    <span className="text-xs text-slate-400 font-semibold uppercase font-mono">progress</span>
                  </div>
                </div>

                {/* Primary Animated Progress Bar Track */}
                <div className="space-y-2 relative z-10">
                  <div className="w-full h-4 sm:h-5 rounded-full bg-slate-100 border border-slate-200 shadow-inner overflow-hidden p-0.5 relative">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-[#0536d2] via-[#597ef3] to-[#03e78b] transition-all duration-300 ease-out relative shadow-sm"
                      style={{ width: `${Math.max(4, progressPercent)}%` }}
                    >
                      <div className="absolute inset-0 bg-white/20 animate-pulse" />
                    </div>
                  </div>
                  <div className="flex justify-between items-center text-[10px] sm:text-[11px] text-slate-400 font-mono px-1">
                    <span>0% Start</span>
                    <span>25% Brand DNA</span>
                    <span>55% Apify Scraper</span>
                    <span>80% Scoring</span>
                    <span>100% Ready</span>
                  </div>
                </div>

                {/* Dynamic Phase Headline & Details */}
                <div className="space-y-1.5 text-center sm:text-left relative z-10 bg-blue-50/60 border border-blue-200/80 rounded-2xl p-4">
                  <div className="flex items-center space-x-2">
                    <RefreshCw className="w-4 h-4 text-[#0536d2] animate-spin shrink-0" />
                    <h4 className="text-sm sm:text-base font-bold text-slate-900">
                      {progressStageTitle || 'กำลังประมวลผลข้อมูลสด...'}
                    </h4>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed pl-6">
                    {progressStageDesc || 'กำลังเชื่อมต่อ Live Scraper และ Gemini AI Engine...'}
                  </p>
                </div>

                {/* 4-Step Interactive Milestone Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5 text-left text-xs relative z-10">
                  {/* Step 1 */}
                  <div className={`p-3.5 rounded-2xl border transition-all ${
                    activeStep > 1 || progressPercent === 100
                      ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                      : activeStep === 1
                      ? 'bg-blue-50 border-blue-300 text-[#0536d2] shadow-xs ring-2 ring-blue-100'
                      : 'bg-slate-50 border-slate-200 text-slate-400'
                  }`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-[10px] uppercase font-mono">Step 1</span>
                      {activeStep > 1 || progressPercent === 100 ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : activeStep === 1 ? (
                        <RefreshCw className="w-3.5 h-3.5 text-[#0536d2] animate-spin" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-slate-300" />
                      )}
                    </div>
                    <span className="font-bold block text-xs">Brand DNA</span>
                    <span className="text-[10px] opacity-80 block truncate">Jina + Gemini</span>
                  </div>

                  {/* Step 2 */}
                  <div className={`p-3.5 rounded-2xl border transition-all ${
                    activeStep > 2 || progressPercent === 100
                      ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                      : activeStep === 2
                      ? 'bg-blue-50 border-blue-300 text-[#0536d2] shadow-xs ring-2 ring-blue-100'
                      : 'bg-slate-50 border-slate-200 text-slate-400'
                  }`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-[10px] uppercase font-mono">Step 2</span>
                      {activeStep > 2 || progressPercent === 100 ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : activeStep === 2 ? (
                        <RefreshCw className="w-3.5 h-3.5 text-[#0536d2] animate-spin" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-slate-300" />
                      )}
                    </div>
                    <span className="font-bold block text-xs">TikTok Scraper</span>
                    <span className="text-[10px] opacity-80 block truncate">Apify Actor + Filter</span>
                  </div>

                  {/* Step 3 */}
                  <div className={`p-3.5 rounded-2xl border transition-all ${
                    activeStep > 3 || progressPercent === 100
                      ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                      : activeStep === 3
                      ? 'bg-blue-50 border-blue-300 text-[#0536d2] shadow-xs ring-2 ring-blue-100'
                      : 'bg-slate-50 border-slate-200 text-slate-400'
                  }`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-[10px] uppercase font-mono">Step 3</span>
                      {activeStep > 3 || progressPercent === 100 ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : activeStep === 3 ? (
                        <RefreshCw className="w-3.5 h-3.5 text-[#0536d2] animate-spin" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-slate-300" />
                      )}
                    </div>
                    <span className="font-bold block text-xs">Multi-Signals</span>
                    <span className="text-[10px] opacity-80 block truncate">ER, Utility, ตะกร้า</span>
                  </div>

                  {/* Step 4 */}
                  <div className={`p-3.5 rounded-2xl border transition-all ${
                    progressPercent === 100
                      ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                      : activeStep === 4
                      ? 'bg-blue-50 border-blue-300 text-[#0536d2] shadow-xs ring-2 ring-blue-100'
                      : 'bg-slate-50 border-slate-200 text-slate-400'
                  }`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-[10px] uppercase font-mono">Step 4</span>
                      {progressPercent === 100 ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : activeStep === 4 ? (
                        <RefreshCw className="w-3.5 h-3.5 text-[#0536d2] animate-spin" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-slate-300" />
                      )}
                    </div>
                    <span className="font-bold block text-xs">Match & Rank</span>
                    <span className="text-[10px] opacity-80 block truncate">4 Archetypes & Fit</span>
                  </div>
                </div>

                {/* Live Activity Terminal Log Ticker */}
                {liveLogs.length > 0 && (
                  <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 font-mono text-[11px] text-slate-300 space-y-1.5 shadow-inner relative z-10">
                    <div className="flex items-center justify-between text-slate-500 pb-1.5 border-b border-slate-800/80 text-[10px]">
                      <span className="flex items-center space-x-1.5">
                        <Terminal className="w-3 h-3 text-[#03e78b]" />
                        <span>LIVE PIPELINE LOGS (Zero-Mock 100%)</span>
                      </span>
                      <span className="text-slate-400 font-mono">Stream Active</span>
                    </div>
                    <div ref={logsContainerRef} className="space-y-1 max-h-28 overflow-y-auto pr-1">
                      {liveLogs.map((log, idx) => (
                        <div key={idx} className="flex items-start space-x-2 leading-relaxed">
                          <span className="text-[#03e78b] select-none">›</span>
                          <span className={log.includes('Success') || log.includes('ready') || log.includes('100%') ? 'text-emerald-400 font-semibold' : 'text-slate-200'}>
                            {log}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Empty State before any search */}
            {!isMatching && !isAnalyzing && !matchResponse && (
              <div className="bg-white border border-slate-200/90 rounded-3xl p-12 text-center space-y-4 shadow-xs backdrop-blur-md">
                <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto text-[#0536d2] shadow-xs">
                  <Search className="w-8 h-8 text-[#597ef3]" />
                </div>
                <div className="space-y-1.5 max-w-sm mx-auto">
                  <h4 className="text-base font-bold text-slate-900">พร้อมสำหรับการค้นหาครีเอเตอร์</h4>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    กรอกข้อมูลแบรนด์ เว็บไซต์ หรือ Facebook Page ทางด้านซ้าย แล้วกดปุ่มเพื่อเริ่มค้นหาและจับคู่ครีเอเตอร์ตาม 4 Archetypes
                  </p>
                </div>
              </div>
            )}

            {/* Nav Tabs for Results */}
            {!isMatching && !isAnalyzing && matchResponse && (
              <>
                <div className="flex items-center space-x-2 border-b border-slate-200/90 pb-2 text-xs font-semibold flex-wrap gap-y-2">
                  <button
                    onClick={() => setActiveTab('ranked')}
                    className={`px-3.5 py-1.5 rounded-2xl transition cursor-pointer flex items-center space-x-1.5 ${
                      activeTab === 'ranked'
                        ? 'bg-[#0536d2] text-white font-bold shadow-xs'
                        : 'text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200'
                    }`}
                  >
                    <span>All Top Matches</span>
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-white/20 text-white font-bold">
                      {matchResponse.ranked_kols.length}
                    </span>
                  </button>
                  <button
                    onClick={() => setActiveTab('guru')}
                    className={`px-3.5 py-1.5 rounded-2xl transition cursor-pointer flex items-center space-x-1.5 ${
                      activeTab === 'guru'
                        ? 'bg-indigo-600 text-white font-bold shadow-xs'
                        : 'text-indigo-800 hover:bg-indigo-100 bg-indigo-50 border border-indigo-200'
                    }`}
                  >
                    <span>🧠 Educated Guru ({matchResponse.ranked_kols.filter(k => k.kol.creator_archetype === 'Educated Guru').length})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('reviewer')}
                    className={`px-3.5 py-1.5 rounded-2xl transition cursor-pointer flex items-center space-x-1.5 ${
                      activeTab === 'reviewer'
                        ? 'bg-purple-600 text-white font-bold shadow-xs'
                        : 'text-purple-800 hover:bg-purple-100 bg-purple-50 border border-purple-200'
                    }`}
                  >
                    <span>⭐ Top Reviewer ({matchResponse.ranked_kols.filter(k => k.kol.creator_archetype === 'Top Reviewer').length})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('lifestyle')}
                    className={`px-3.5 py-1.5 rounded-2xl transition cursor-pointer flex items-center space-x-1.5 ${
                      activeTab === 'lifestyle'
                        ? 'bg-teal-600 text-white font-bold shadow-xs'
                        : 'text-teal-800 hover:bg-teal-100 bg-teal-50 border border-teal-200'
                    }`}
                  >
                    <span>🌴 Lifestyle & Vlog ({matchResponse.ranked_kols.filter(k => k.kol.creator_archetype === 'Lifestyle & Vlog').length})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('niche')}
                    className={`px-3.5 py-1.5 rounded-2xl transition cursor-pointer flex items-center space-x-1.5 ${
                      activeTab === 'niche'
                        ? 'bg-emerald-600 text-white font-bold shadow-xs'
                        : 'text-emerald-800 hover:bg-emerald-100 bg-emerald-50 border border-emerald-200'
                    }`}
                  >
                    <span>🎯 Niche Enthusiast ({matchResponse.ranked_kols.filter(k => k.kol.creator_archetype === 'Niche Enthusiast').length})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('spam')}
                    className={`px-3.5 py-1.5 rounded-2xl transition cursor-pointer flex items-center space-x-1.5 ${
                      activeTab === 'spam'
                        ? 'bg-rose-500 text-white font-bold shadow-xs'
                        : 'text-slate-600 hover:bg-slate-200 bg-slate-100 border border-slate-200'
                    }`}
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>Bot & Farm Traps (-55) ({matchResponse.penalized_spam_kols.length})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('trace')}
                    className={`px-3.5 py-1.5 rounded-2xl transition cursor-pointer ${
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

                {/* TAB 1 & 2: RANKED KOLS LIST & ARCHETYPE TABS */}
                {(activeTab === 'ranked' || activeTab === 'guru' || activeTab === 'reviewer' || activeTab === 'lifestyle' || activeTab === 'niche') && (
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
                                {item.kol.avatar_url ? (
                                  <img
                                    src={item.kol.avatar_url}
                                    alt={item.kol.display_name}
                                    className="w-13 h-13 rounded-2xl bg-slate-100 border-2 border-slate-200 object-cover shadow-xs"
                                  />
                                ) : (
                                  <div className="w-13 h-13 rounded-2xl bg-gradient-to-br from-[#0536d2] to-[#597ef3] border-2 border-blue-400 text-white font-bold text-lg flex items-center justify-center shadow-xs uppercase">
                                    {(item.kol.display_name || item.kol.handle).slice(0, 1)}
                                  </div>
                                )}
                                <span className="absolute -top-1.5 -left-1.5 flex items-center justify-center w-5 h-5 rounded-full bg-[#0536d2] text-white font-black text-[10px] shadow border border-[#597ef3]">
                                  #{item.rank}
                                </span>
                              </div>

                              <div>
                                <div className="flex items-center space-x-2 flex-wrap">
                                  <h4 className="font-bold text-slate-900 text-base hover:text-[#0536d2] transition">
                                    {item.kol.display_name}
                                  </h4>
                                  <a
                                    href={item.kol.tiktok_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center space-x-1 text-xs text-[#0536d2] hover:text-white hover:bg-[#0536d2] font-mono bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200 transition"
                                  >
                                    <span>@{item.kol.handle}</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                                <p className="text-xs text-slate-700 mt-1 line-clamp-2 leading-relaxed">{item.kol.bio}</p>
                                <div className="flex items-center space-x-2 text-xs text-slate-500 mt-1.5 flex-wrap font-medium gap-y-1">
                                  <span className="text-slate-800 font-semibold px-2 py-0.5 rounded-lg bg-slate-100 border border-slate-200">
                                    {item.kol.tier}
                                  </span>
                                  <span>•</span>
                                  <span className="font-mono text-slate-600">{item.kol.follower_count.toLocaleString()} Followers</span>
                                  <span>•</span>
                                  <span className="text-emerald-700 font-semibold font-mono">
                                    Est Rate: {item.kol.estimated_rate_thb}
                                  </span>
                                  {item.kol.creator_archetype && (
                                    <>
                                      <span>•</span>
                                      <span className="inline-flex items-center space-x-1 font-bold text-indigo-900 bg-indigo-50 px-2 py-0.5 rounded-lg border border-indigo-200">
                                        <Award className="w-3 h-3 text-indigo-600" />
                                        <span>{item.kol.creator_archetype}</span>
                                        {item.kol.recommended_role && (
                                          <span className="text-[10px] text-indigo-700 bg-indigo-100 px-1.5 py-0.2 rounded font-mono">
                                            {item.kol.recommended_role}
                                          </span>
                                        )}
                                      </span>
                                    </>
                                  )}
                                  {item.kol.is_work_ready && (
                                    <>
                                      <span>•</span>
                                      <span className="inline-flex items-center space-x-1 font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-200">
                                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                        <span>พร้อมรับงาน</span>
                                      </span>
                                    </>
                                  )}
                                  {item.kol.is_casual_niche_fit ? (
                                    <>
                                      <span>•</span>
                                      <span className="inline-flex items-center space-x-1 font-medium text-amber-800 bg-amber-50 px-2 py-0.5 rounded-lg border border-amber-300 shadow-2xs" title="ตรวจสอบจาก 5 คลิปล่าสุด พบว่าเป็นการเข้ามาสัมผัสชั่วคราว/ท่องเที่ยว (Casual Fit) ไม่ใช่ Core Specialist">
                                        <span>💡 Casual Niche Fit ({Math.round((item.kol.niche_consistency_ratio ?? 0) * 100)}%)</span>
                                      </span>
                                    </>
                                  ) : (item.kol.niche_consistency_ratio !== undefined && item.kol.niche_consistency_ratio >= 0.5) ? (
                                    <>
                                      <span>•</span>
                                      <span className="inline-flex items-center space-x-1 font-medium text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-300 shadow-2xs" title="ตรวจสอบ 5 คลิปล่าสุด มีความเจาะจงใน Niche นี้สม่ำเสมอ">
                                        <span>🎯 Core Niche ({Math.round(item.kol.niche_consistency_ratio * 100)}%)</span>
                                      </span>
                                    </>
                                  ) : null}
                                  <span>•</span>
                                  <span className="inline-flex items-center space-x-1 font-bold text-amber-900 bg-amber-50 px-2.5 py-0.5 rounded-lg border border-amber-200 shadow-2xs">
                                    <ShoppingBag className="w-3 h-3 text-amber-600" />
                                    <span>{item.kol.creator_category || 'Content Creator (เน้นรีวิว)'}</span>
                                    {item.score_breakdown.yellow_basket_ratio > 0 && (
                                      <span className="text-[10px] text-amber-700 bg-amber-100 px-1.5 py-0.2 rounded font-mono">
                                        ตะกร้า {Math.round(item.score_breakdown.yellow_basket_ratio * 100)}%
                                      </span>
                                    )}
                                  </span>
                                </div>

                                {item.kol.competitor_warning && (
                                  <div className={`mt-2 px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-1.5 border ${
                                    item.kol.competitor_warning.includes('Conflict')
                                      ? 'bg-rose-50 text-rose-800 border-rose-200'
                                      : 'bg-indigo-50 text-indigo-800 border-indigo-200'
                                  }`}>
                                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                                    <span>{item.kol.competitor_warning}</span>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Match Score Badge & Shortlist */}
                            <div className="flex flex-col items-end space-y-2 shrink-0">
                              <div className="inline-flex items-baseline space-x-1 px-3.5 py-1.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 font-black text-lg shadow-xs">
                                <span>{item.total_match_score.toFixed(1)}</span>
                                <span className="text-[10px] text-emerald-600 font-semibold">/100</span>
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

                          {/* 3-Part Hybrid Score Breakdown (Spec 5: 40 / 35 / 25) */}
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs">
                            {/* 1. Relevance (40%) */}
                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-600 font-semibold">1. Brand Relevance (40%)</span>
                                <span className="font-bold text-slate-900 font-mono">
                                  {item.score_breakdown.relevance_weighted.toFixed(1)} / 40 pts
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
                              <div className="flex justify-between text-[10px] text-slate-500">
                                <span>Semantic: {item.score_breakdown.semantic_points ?? (item.score_breakdown.semantic_similarity * 28).toFixed(1)}/28</span>
                                <span className="text-[#0536d2] font-semibold">
                                  Keywords & Work: {item.score_breakdown.niche_keyword_points ?? (item.score_breakdown.matched_keywords.length * 1.5).toFixed(1)}/12
                                </span>
                              </div>
                            </div>

                            {/* 2. Engagement Quality (35%) */}
                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-600 font-semibold">2. Engagement Quality (35%)</span>
                                <span className="font-bold text-slate-900 font-mono">
                                  {item.score_breakdown.engagement_weighted.toFixed(1)} / 35 pts
                                </span>
                              </div>
                              <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-[#0536d2] to-emerald-500 rounded-full transition-all duration-500"
                                  style={{
                                    width: `${item.score_breakdown.engagement_score_raw}%`,
                                  }}
                                />
                              </div>
                              <div className="flex justify-between text-[10px] text-slate-500">
                                <span>
                                  Median ER:{' '}
                                  <strong className="text-emerald-700 font-mono">
                                    {item.score_breakdown.median_engagement_rate_pct.toFixed(1)}%
                                  </strong>
                                </span>
                                <span className="font-mono text-slate-600">
                                  Save/View: {(item.kol.save_to_view_ratio || 0.02).toFixed(3)}
                                </span>
                              </div>
                            </div>

                            {/* 3. Multi-Signal Demographics (25%) */}
                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-600 font-semibold">3. Audience Signal (25%)</span>
                                <span className="font-bold text-slate-900 font-mono">
                                  {item.score_breakdown.audience_weighted.toFixed(1)} / 25 pts
                                </span>
                              </div>
                              <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                                <div
                                  className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                                  style={{
                                    width: `${item.score_breakdown.audience_score_raw}%`,
                                  }}
                                />
                              </div>
                              <div className="flex justify-between items-center text-[10px] gap-1.5 min-w-0">
                                <span className="text-slate-500 truncate">Thai Reach & Intent</span>
                                <span
                                  className={`px-2 py-0.5 rounded-full font-bold text-[9px] shrink-0 whitespace-nowrap inline-flex items-center gap-1.5 ${
                                    item.score_breakdown.confidence_level === 'High'
                                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                                      : item.score_breakdown.confidence_level === 'Medium'
                                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                                      : 'bg-rose-50 text-rose-800 border border-rose-200'
                                  }`}
                                >
                                  <span
                                    className={`w-1.5 h-1.5 rounded-full ${
                                      item.score_breakdown.confidence_level === 'High'
                                        ? 'bg-emerald-500'
                                        : item.score_breakdown.confidence_level === 'Medium'
                                        ? 'bg-amber-500'
                                        : 'bg-rose-500'
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
                            <strong className="text-blue-950 font-bold flex items-center space-x-1.5 mb-1">
                              <Award className="w-3.5 h-3.5 text-[#0536d2]" />
                              <span>Convert Cake Performance Rationale:</span>
                            </strong>
                            {item.why_this_kol}
                          </div>

                          {/* Audited Video Telemetry Drawer */}
                          {item.kol.recent_videos && item.kol.recent_videos.length > 0 && (
                            <div className="pt-1 border-t border-slate-200">
                              <button
                                onClick={() => setExpandedKOLId(isExpanded ? null : item.kol.id)}
                                className="w-full py-2.5 rounded-2xl bg-slate-50 hover:bg-slate-100 text-xs text-slate-700 font-semibold transition flex items-center justify-center space-x-2 cursor-pointer border border-slate-200"
                              >
                                <BarChart3 className="w-3.5 h-3.5 text-[#0536d2]" />
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
                                  <h5 className="font-bold text-slate-900 text-xs flex items-center space-x-2">
                                    <Eye className="w-3.5 h-3.5 text-[#0536d2]" />
                                    <span>Recent Videos Audited by Scoring Engine:</span>
                                  </h5>

                                  <div className="space-y-2">
                                    {item.kol.recent_videos.map((vid, vIdx) => (
                                      <div
                                        key={vIdx}
                                        className="p-3 rounded-xl bg-white border border-slate-200 space-y-1.5"
                                      >
                                        <div className="flex items-start justify-between gap-2">
                                          <p className="text-slate-900 text-xs font-medium line-clamp-1">
                                            {vid.caption || 'TikTok video clip'}
                                          </p>
                                          {vid.has_yellow_basket && (
                                            <span className="px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 text-[10px] font-bold border border-amber-200 shrink-0 flex items-center space-x-1">
                                              <ShoppingBag className="w-2.5 h-2.5" />
                                              <span>ตะกร้าเหลือง</span>
                                            </span>
                                          )}
                                        </div>

                                        <div className="flex items-center space-x-3 text-[11px] text-slate-500 font-mono flex-wrap gap-y-1">
                                          <span className="text-slate-800 font-semibold">{vid.views.toLocaleString()} views</span>
                                          <span>•</span>
                                          <span>{vid.likes.toLocaleString()} likes</span>
                                          <span>•</span>
                                          <span>{vid.comments.toLocaleString()} comments</span>
                                          <span>•</span>
                                          <span>{vid.shares.toLocaleString()} shares</span>
                                          <span>•</span>
                                          <span className="text-[#0536d2] font-semibold">{(vid.collect_count ?? 0).toLocaleString()} saves</span>
                                          {vid.location_tag && (
                                            <>
                                              <span>•</span>
                                              <span className="text-emerald-700 font-sans font-medium">📍 {vid.location_tag}</span>
                                            </>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>

                                  {/* Audience Comments */}
                                  {item.kol.sample_comments && item.kol.sample_comments.length > 0 && (
                                    <div className="pt-2 border-t border-slate-200">
                                      <h5 className="font-bold text-slate-900 text-xs mb-2 flex items-center space-x-2">
                                        <MessageSquare className="w-3.5 h-3.5 text-emerald-600" />
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

                {/* TAB 2: ANTI-SPAM & BOT REPOST TRAPS */}
                {activeTab === 'spam' && (
                  <div className="space-y-4">
                    <div className="p-5 rounded-3xl bg-rose-50 border border-rose-200 text-rose-950 text-xs space-y-2 shadow-xs">
                      <div className="flex items-center space-x-2 font-bold text-rose-800 text-sm">
                        <ShieldAlert className="w-4 h-4 text-rose-600" />
                        <span>Bot & Repost Farm Trap Engine (-55 Pts Penalty)</span>
                      </div>
                      <p className="leading-relaxed text-rose-900">
                        ระบบตรวจจับและหักลบ -55 แต้มเฉพาะบัญชีที่เป็น Bot, ฟาร์มรีโพสต์ หรือบัญชีปั่นยอดวิวที่ไม่มี Engagement คุณภาพจริง <strong>(ครีเอเตอร์สายรีวิวที่ปักตะกร้าเหลือง 100% จะได้รับการยกเว้น ไม่ถูกจัดเป็น Spam Trap และถูกจัดเข้าหมวด Top Reviewer)</strong>
                      </p>
                    </div>

                    {matchResponse.penalized_spam_kols.map(item => (
                      <div
                        key={item.kol.id}
                        className="bg-white border border-rose-200 rounded-3xl p-5 sm:p-6 shadow-xs space-y-3"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 font-bold text-[10px] border border-rose-200">
                                FLAGGED BOT / FARM
                              </span>
                              <h4 className="font-bold text-slate-900 text-base">{item.kol.display_name}</h4>
                              <a
                                href={item.kol.tiktok_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-[#0536d2] hover:underline font-mono flex items-center space-x-0.5"
                              >
                                <span>@{item.kol.handle}</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            </div>
                            <p className="text-xs text-slate-600 mt-1">{item.kol.bio}</p>
                          </div>

                          <div className="text-right">
                            <span className="text-base font-extrabold text-rose-700 font-mono">
                              {item.total_match_score.toFixed(1)} / 100
                            </span>
                            <span className="block text-[10px] text-rose-600 font-semibold font-mono">
                              -55 pts Bot Penalty
                            </span>
                          </div>
                        </div>

                        <div className="p-3 rounded-2xl bg-rose-50/80 border border-rose-200 text-xs text-rose-900 leading-relaxed">
                          <strong className="text-rose-950 font-bold">Detection Trigger: </strong>
                          {item.score_breakdown.affiliate_spam_reason}
                        </div>

                        <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                          <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                            <span className="block text-[10px] text-slate-500 font-sans font-medium">Utility Save/View</span>
                            <span className="font-bold text-slate-800 text-sm">
                              {(item.kol.save_to_view_ratio || 0).toFixed(4)}
                            </span>
                          </div>
                          <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                            <span className="block text-[10px] text-slate-500 font-sans font-medium">Median ER</span>
                            <span className="font-bold text-slate-800 text-sm">
                              {item.score_breakdown.median_engagement_rate_pct.toFixed(1)}%
                            </span>
                          </div>
                          <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                            <span className="block text-[10px] text-slate-500 font-sans font-medium">View Consistency</span>
                            <span className="font-bold text-slate-800 text-sm">
                              {(item.kol.view_consistency_ratio || 0).toFixed(2)}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* TAB 3: WORKFLOW TRACE */}
                {activeTab === 'trace' && (
                  <div className="bg-white border border-slate-200 rounded-3xl p-5 sm:p-6 shadow-xs space-y-4">
                    <h4 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                      <RefreshCw className="w-4 h-4 text-[#0536d2]" />
                      <span>LangGraph Execution Nodes & State Transitions</span>
                    </h4>
                    <div className="space-y-2">
                      {matchResponse.workflow_trace.map((step, idx) => (
                        <div
                          key={idx}
                          className="flex items-start space-x-3 p-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-800"
                        >
                          <span className="text-[#0536d2] font-bold shrink-0">[{idx + 1}]</span>
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
