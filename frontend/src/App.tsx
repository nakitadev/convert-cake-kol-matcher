import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Search,
  Users,
  ShieldCheck,
  ShieldAlert,
  Target,
  RefreshCw,
  Download,
  ChevronDown,
  ChevronUp,
  Sliders,
  Info,
  Check,
  Copy,
  Eye,
  MessageSquare,
  ShoppingBag,
  Globe,
  BarChart3,
  Radio,
  Zap,
  Award,
  Clock,
  Terminal,
  Layers,
  FileSpreadsheet,
  Compass,
  AlertOctagon,
  X,
} from 'lucide-react';

const API_BASE = '';

// ============================================================================
// TypeScript Interfaces aligned with Spec Models
// ============================================================================
interface KolKocMix {
  kol: number;
  koc: number;
}

interface SearchQuery {
  query: string;
  side: 'KOL_QUERY' | 'KOC_QUERY';
  specificity: 'direct' | 'adjacent';
}

interface Competitor {
  brand: string;
  aliases: string[];
  source: string;
  mentions?: number;
}

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
  brand_tone: string[];
  customer_pain_points?: string[];
  price_positioning: string;
  average_price_thb: number;
  conversion_model: 'ECOMMERCE_PRODUCT' | 'APP_DIGITAL_SERVICE' | 'HIGH_TICKET_LEADGEN' | 'LIFESTYLE_EXPERIENCE';
  conversion_model_reason?: string;
  kol_koc_mix: KolKocMix;
  search_queries: SearchQuery[];
  niche_keywords: string[];
  competitors: Competitor[];
  scraped_sources: string[];
}

interface VideoMetric {
  video_id: string;
  url: string;
  caption: string;
  hashtags: string[];
  views: number;
  likes: number;
  comments: number;
  shares: number;
  collect_count?: number;
  has_yellow_basket: boolean;
  query_origin?: 'KOL_QUERY' | 'KOC_QUERY';
  search_query?: string;
}

interface CompetitorFlag {
  type: 'conflict' | 'comparison';
  label: string;
  brands: string[];
  video_id?: string;
}

interface CreatorSignals {
  basket_ratio: number;
  median_views: number;
  mean_views: number;
  median_comments: number;
  save_rate: number;
  comment_to_like: number;
  share_to_like: number;
  avg_caption_length: number;
  kol_query_hits: number;
  koc_query_hits: number;
}

interface KOLProfile {
  id: string;
  handle: string;
  display_name: string;
  tiktok_url: string;
  avatar_url?: string;
  bio: string;
  follower_count: number;
  following_count: number;
  total_likes: number;
  tier: 'Nano' | 'Micro' | 'Mid-Tier' | 'Macro';
  recent_videos: VideoMetric[];
  query_origin: 'KOL_QUERY' | 'KOC_QUERY';
  is_work_ready: boolean;
  signals: CreatorSignals;
  funnel_role?: 'KOL' | 'KOC';
  sub_style?: 'KOL - Expert / Guru' | 'KOL - Lifestyle / Aesthetic' | 'KOC - Hard-Sell Reviewer' | 'KOC - Everyday User / Vlog';
  llm_relevance_score?: number;
  why_it_fits?: string;
  real_comments?: string[];
  comment_intent_ratio?: number;
  competitor_flags?: CompetitorFlag[];
}

interface SignalBreakdown {
  relevance_total: number;
  semantic_llm_points: number;
  cosine_similarity: number;
  subniche_workready_points: number;
  matched_keywords: string[];
  engagement_total: number;
  median_er_points: number;
  median_engagement_rate: number;
  eligible_clips: number;
  utility_points: number;
  utility_score: number;
  consistency_points: number;
  view_consistency_ratio: number;
  audience_total: number;
  thai_authenticity_points: number;
  thai_ratio: number;
  buyer_intent_points: number;
  buyer_intent_tier: string;
  affiliate_health_points: number;
  evidence: string[];
}

interface RankedKOL {
  rank: number;
  kol: KOLProfile;
  total_match_score: number;
  score_breakdown: SignalBreakdown;
  pitch_hook: string;
}

interface StrategySummary {
  conversion_model: string;
  conversion_model_reason?: string;
  recommended_mix: KolKocMix;
  achieved_mix: Record<string, number>;
}

interface FilterStats {
  raw_clips: number;
  unique_creators: number;
  removed_brand_accounts: number;
  removed_merchants: number;
  removed_affiliate_bots: number;
  removed_irrelevant: number;
  scored: number;
}

interface ExcludedCreator {
  handle: string;
  display_name: string;
  tiktok_url: string;
  follower_count: number;
  bio: string;
  stage: string;
  reason: string;
}

interface ApiErrorInfo {
  type: 'apify_quota' | 'rate_limit' | 'token_missing' | 'server_error';
  title: string;
  message: string;
  status?: number;
  details?: string;
  timestamp: string;
  endpoint?: string;
}

interface MatchResponse {
  brand_dna: BrandDNA;
  strategy: StrategySummary;
  filter_stats: FilterStats;
  ranked_kols: RankedKOL[];
  excluded_creators: ExcludedCreator[];
  warnings: string[];
  workflow_trace: string[];
}

// Conversion model meta info for strategy summary banner
const MODEL_DETAILS: Record<string, { label: string; icon: string; desc: string; mix: string; color: string }> = {
  ECOMMERCE_PRODUCT: {
    label: 'E-Commerce Product',
    icon: '🛒',
    desc: 'เน้นซื้อทันทีผ่านตะกร้า TikTok Shop / Shopee (สกินแคร์, เครื่องสำอาง, อาหารเสริม, ของใช้, แกดเจ็ต)',
    mix: 'KOL 30% : KOC 70%',
    color: 'from-amber-500/10 to-orange-500/5 border-amber-200 text-amber-900',
  },
  APP_DIGITAL_SERVICE: {
    label: 'App & Digital Service',
    icon: '📱',
    desc: 'เน้นดาวน์โหลดแอป, สมัครสมาชิก, SaaS (FinTech, แพลตฟอร์ม AI, ซอฟต์แวร์, เกม)',
    mix: 'KOL 60% : KOC 40%',
    color: 'from-blue-500/10 to-cyan-500/5 border-blue-200 text-blue-900',
  },
  HIGH_TICKET_LEADGEN: {
    label: 'High-Ticket Lead Gen',
    icon: '💎',
    desc: 'เน้นทักแชท / นัดหมาย / จองคอร์ส / กรอกฟอร์ม (คลินิกเสริมความงาม, ทันตกรรม, คอร์สเรียน, อสังหาฯ)',
    mix: 'KOL 70% : KOC 30%',
    color: 'from-purple-500/10 to-indigo-500/5 border-purple-200 text-purple-900',
  },
  LIFESTYLE_EXPERIENCE: {
    label: 'Lifestyle & Experience',
    icon: '🏨',
    desc: 'เน้นไปหน้าร้าน / สร้างภาพลักษณ์พรีเมียม (โรงแรม, คาเฟ่/ร้านอาหาร, ห้างสรรพสินค้า, แบรนด์ Luxury)',
    mix: 'KOL 60% : KOC 40%',
    color: 'from-teal-500/10 to-emerald-500/5 border-teal-200 text-teal-900',
  },
};

// Golden Evaluation Dataset: 6 Representative Test Cases Across 6 Industries
const INDUSTRY_TEST_CASES = [
  {
    id: 'b2b-manufacturing',
    industry: 'B2B Manufacturing',
    label: 'Piggy Monster',
    icon: '🏭',
    badge: 'Demand-Side Query Gate',
    name: 'Piggy Monster',
    url: 'https://piggymonster-th.com/',
    fb: 'https://www.facebook.com/p/Piggy-Monster-%E0%B9%80%E0%B8%AA%E0%B8%B7%E0%B9%89%E0%B8%AD%E0%B8%AA%E0%B8%81%E0%B8%A3%E0%B8%B5%E0%B8%99-%E0%B8%A3%E0%B8%B2%E0%B8%84%E0%B8%B2%E0%B8%96%E0%B8%B9%E0%B8%81-61554003789059/',
    notes: 'บริการสกรีนเสื้อยืด เสื้อโปโล เสื้อรุ่น เสื้อคณะ สกรีน DTF และบล็อกสกรีน ไม่มีขั้นต่ำ ลายคมชัด สำหรับแบรนด์แฟชั่นและกิจกรรมมหาลัย',
    competitors: 'Korat Screen, Screen BKK',
  },
  {
    id: 'beauty-clinic',
    industry: 'Beauty Clinic',
    label: 'Emma Clinic',
    icon: '💉',
    badge: 'Competitor Venue Gate',
    name: 'Emma Clinic',
    url: 'https://emmaclinicthailand.com',
    fb: 'https://www.facebook.com/emmaclinicthailand',
    notes: 'คลินิกศัลยกรรมเสริมจมูก เสริมคาง ปรับรูปหน้า และดูแลผิวพรรณ เน้นทรงธรรมชาติ สไตล์เกาหลี ปลอดภัยโดยแพทย์เฉพาะทาง',
    competitors: 'Sowon Clinic, SLC Clinic, Apex Medical Center',
  },
  {
    id: 'skincare-beauty',
    industry: 'Skincare & Beauty',
    label: 'Dr.PONG',
    icon: '🧴',
    badge: 'Balanced Portfolio Gate',
    name: 'Dr.PONG',
    url: 'https://drpongshop.com',
    fb: 'https://www.facebook.com/drpongshop',
    notes: 'เวชสำอางและสกินแคร์คลีนบิวตี้สูตรคุณหมอ เซรั่มลดสิว ครีมกันแดดเนื้อบางเบา และอาหารเสริมผิว ตอบโจทย์คนเป็นสิวผิวแพ้ง่าย',
    competitors: 'Her Hyness, Gravich, MizuMi',
  },
  {
    id: 'sports-outdoor',
    industry: 'Sports & Outdoor',
    label: 'Proski Thailand',
    icon: '🎿',
    badge: 'Niche Consistency Gate',
    name: 'Proski Thailand',
    url: 'https://proski.co/',
    fb: 'https://www.facebook.com/p/Proski-Thailand-61594629305420/',
    notes: 'คลับฝึกซ้อมสกีและสโนว์บอร์ดในร่มแห่งแรกในไทย จำลองเนินหิมะอินดอร์ พร้อมคอร์สเรียนก่อนไปทริปเล่นสกีต่างประเทศ',
    competitors: 'Ski365, The Snow Town',
  },
  {
    id: 'fashion-streetwear',
    industry: 'Fashion & Streetwear',
    label: 'Merge Official',
    icon: '👖',
    badge: 'Entity & Spam Gate',
    name: 'Merge Official',
    url: 'https://mergeofficial.com',
    fb: 'https://www.facebook.com/mergeofficialth',
    notes: 'แบรนด์แฟชั่นเสื้อผ้าสตรีทแวร์และกางเกงยีนส์ OOTD ยอดฮิตสำหรับคนรุ่นใหม่ ดีไซน์โก้เก๋ แมตช์ง่าย ใส่ได้ทุกวัน',
    competitors: 'Gentlewoman, Stylist Shop, Mitr',
  },
  {
    id: 'fnb-cafe',
    industry: 'F&B & Cafe',
    label: 'Bearhouse',
    icon: '🧋',
    badge: 'Experience & Niche Gate',
    name: 'Bearhouse',
    url: 'https://bearhouse.co.th',
    fb: 'https://www.facebook.com/bearhouse.thailand',
    notes: 'แบรนด์ชานมไข่มุกและเครื่องดื่มไลฟ์สไตล์ จุดเด่นคือไข่มุกโมจิทำสดหนึบหนับ เค้กโรล และเมนูชาพรีเมียม ขวัญใจวัยรุ่นและสายคาเฟ่',
    competitors: 'After You, Nose Tea, Fire Tiger, ChaTraMue',
  },
];

export default function HomePage() {
  // Brand Input State
  const [brandName, setBrandName] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [facebookUrl, setFacebookUrl] = useState('');
  const [customNotes, setCustomNotes] = useState('');
  const [manualCompetitors, setManualCompetitors] = useState('');
  const [selectedTestCase, setSelectedTestCase] = useState<string | null>(null);

  const handleSelectTestCase = (tc: typeof INDUSTRY_TEST_CASES[0]) => {
    setSelectedTestCase(tc.id);
    setBrandName(tc.name);
    setWebsiteUrl(tc.url);
    setFacebookUrl(tc.fb);
    setCustomNotes(tc.notes);
    setManualCompetitors(tc.competitors);
    setBrandDNA(null);
    setMatchResponse(null);
  };

  const handleClearInputs = () => {
    setSelectedTestCase(null);
    setBrandName('');
    setWebsiteUrl('');
    setFacebookUrl('');
    setCustomNotes('');
    setManualCompetitors('');
    setBrandDNA(null);
    setMatchResponse(null);
  };

  // Extracted Brand DNA State
  const [brandDNA, setBrandDNA] = useState<BrandDNA | null>(null);
  const [isEditingDNA, setIsEditingDNA] = useState(false);

  // Match State
  const [matchResponse, setMatchResponse] = useState<MatchResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'guru' | 'lifestyle' | 'hardsell' | 'everyday' | 'excluded' | 'trace'>('all');
  const [expandedKOLId, setExpandedKOLId] = useState<string | null>(null);
  const [copiedHookId, setCopiedHookId] = useState<string | null>(null);

  // Filters & Sorting for Results
  const [roleFilter, setRoleFilter] = useState<'All' | 'KOL' | 'KOC'>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [tierFilter, setTierFilter] = useState('All');
  const [sortBy, setSortBy] = useState<'score' | 'er' | 'followers'>('score');
  const [topK, setTopK] = useState(10);
  const [forceRefresh, setForceRefresh] = useState(false);

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
  const [apiError, setApiError] = useState<ApiErrorInfo | null>(null);
  const logsContainerRef = useRef<HTMLDivElement | null>(null);

  const parseAndSetApiError = (err: any, endpoint: string) => {
    const errMsg = err?.message || String(err);
    const isQuota =
      errMsg.includes('402') ||
      errMsg.includes('Quota Exhausted') ||
      errMsg.includes('not-enough-usage') ||
      errMsg.includes('usage limit') ||
      errMsg.includes('Payment Required');
    const isRateLimit =
      errMsg.includes('429') ||
      errMsg.includes('ResourceExhausted') ||
      errMsg.includes('Rate Limit') ||
      errMsg.includes('rate limit') ||
      errMsg.includes('RATE_LIMIT');
    const isTokenMissing =
      errMsg.includes('APIFY_API_TOKEN is not configured') ||
      errMsg.includes('Token not configured');

    const info: ApiErrorInfo = {
      type: isQuota ? 'apify_quota' : isRateLimit ? 'rate_limit' : isTokenMissing ? 'token_missing' : 'server_error',
      title: isQuota
        ? 'Apify Usage Quota หมด (HTTP 402 — Quota Exhausted)'
        : isRateLimit
        ? 'API Rate Limit เกินขีดจำกัด (HTTP 429 — Rate Limit Exceeded)'
        : isTokenMissing
        ? 'ไม่ได้ตั้งค่า Apify Token ในระบบ (Token Missing)'
        : 'เกิดข้อผิดพลาดในการเชื่อมต่อบริการภายนอก',
      message: isQuota
        ? 'โควตา Free Tier / Compute Units ของ Apify Token ในระบบถูกใช้งานจนครบลิมิตแล้ว ทำให้ Actor บน Apify ไม่สามารถกวาดข้อมูลสดจาก TikTok ได้ชั่วคราว'
        : isRateLimit
        ? 'คำขอเกินข้อจำกัด RPM (Requests Per Minute) หรือโควตาการใช้งานของโมเดล AI ในช่วงเวลานี้'
        : isTokenMissing
        ? 'ไม่พบ APIFY_API_TOKEN ในไฟล์สภาพแวดล้อม backend/.env กรุณาตั้งค่า Token ก่อนเริ่มค้นหา'
        : errMsg,
      status: isQuota ? 402 : isRateLimit ? 429 : 500,
      details: errMsg,
      timestamp: new Date().toLocaleTimeString('th-TH'),
      endpoint,
    };
    setApiError(info);
    setProgressStageTitle('เกิดข้อผิดพลาด: API ติดลิมิต หรือ Token หมด');
    setProgressStageDesc(info.message);
  };

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

  // --------------------------------------------------------------------------
  // Analyze Brand (Stage 1)
  // --------------------------------------------------------------------------
  const handleAnalyzeBrand = async () => {
    if (!brandName && !websiteUrl && !facebookUrl && !customNotes) {
      alert('Please enter at least a Brand Name, Website URL, or Campaign Notes.');
      return;
    }
    setIsAnalyzing(true);
    setMatchResponse(null);
    setApiError(null);
    setProgressPercent(10);
    setElapsedSeconds(0);
    setActiveStep(1);
    setProgressStageTitle('Stage 1: สกัด Brand DNA & จำแนก 4 Conversion Models');
    setProgressStageDesc('ดึงเนื้อหาผ่าน Jina Reader, โพสต์และคอมเมนต์ลูกค้าจาก Facebook Page...');
    setLiveLogs([
      `[Jina Reader] Ingesting client website and cleaning HTML boilerplate...`,
      `[Apify Facebook] Scraping recent brand posts and real Thai customer comments...`,
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
        setProgressPercent(Math.min(35, Math.round(10 + elapsed * 6)));
      } else if (elapsed < 9) {
        setActiveStep(1);
        setProgressStageTitle('Stage 1: Gemini 3.5 Flash Lite จำแนก Brand Conversion Model');
        setProgressStageDesc('วิเคราะห์ Tone of Voice และกำหนดสัดส่วน KOL : KOC แนะนำ...');
        setProgressPercent(Math.min(70, Math.round(35 + (elapsed - 4) * 7)));
        setLiveLogs(prev => !prev.some(l => l.includes('Conversion Model')) ? [
          ...prev,
          `[Gemini 3.5] Classifying into 1 of 4 Conversion Models (E-Comm, App, High-Ticket, Lifestyle)...`,
          `[Media Mix] Setting recommended KOL : KOC media mix ratio...`
        ] : prev);
      } else {
        setActiveStep(1);
        setProgressStageTitle('ขั้นตอนที่ 1: วิเคราะห์จุดขายแบรนด์ & สกัดคำค้นหาตามพฤติกรรมลูกค้า');
        setProgressStageDesc('อ่านเว็บไซต์/เพจจริงเพื่อวิเคราะห์วิธีทำเงิน (Conversion Model), ระบุคู่แข่งในไทย และสร้างคำค้นหาภาษาไทยสั้นกระชับ (Demand-Side Search Intent) เพื่อหาครีเอเตอร์ที่ลูกค้าดูจริง...');
        setProgressPercent(Math.min(95, Math.round(70 + (elapsed - 9) * 3)));
        setLiveLogs(prev => !prev.some(l => l.includes('Scene Translation')) ? [
          ...prev,
          `[Scene Translation] Generating 2-3 words native creator search queries (60% direct / 40% adjacent)...`,
          `[Competitor Layer 1] Google Search Grounding extracting active Thai competitors...`
        ] : prev);
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
          force_refresh: forceRefresh,
        }),
      });
      if (!res.ok) {
        let errText = '';
        try {
          const errJson = await res.json();
          errText = errJson.detail || JSON.stringify(errJson);
        } catch {
          errText = await res.text();
        }
        throw new Error(errText || `HTTP ${res.status}`);
      }
      const data: BrandDNA = await res.json();
      setProgressPercent(100);
      setProgressStageTitle('สกัด Brand DNA & Scene Translation สำเร็จ 100%!');
      setProgressStageDesc(`จำแนกแบรนด์เป็น ${data.conversion_model} (สัดส่วนแนะนำ: KOL ${data.kol_koc_mix.kol}% : KOC ${data.kol_koc_mix.koc}%)`);
      setLiveLogs(prev => [
        ...prev,
        `[Success] Brand DNA complete: ${data.search_queries?.length || 0} Scene Translation queries generated.`,
        `[Competitors] ${data.competitors?.length || 0} Thai competitors catalogued.`
      ]);
      setBrandDNA(data);
    } catch (err: any) {
      console.error('Analyze brand error:', err);
      parseAndSetApiError(err, '/api/analyze-brand');
    } finally {
      clearInterval(timer);
      setTimeout(() => {
        setIsAnalyzing(false);
        setProgressPercent(0);
        setElapsedSeconds(0);
      }, 450);
    }
  };

  // --------------------------------------------------------------------------
  // Match KOLs (Stage 2, 3 & 4)
  // --------------------------------------------------------------------------
  const handleMatchKOLs = async () => {
    if (!brandDNA) return;
    setIsMatching(true);
    setApiError(null);
    setProgressPercent(5);
    setElapsedSeconds(0);
    setActiveStep(2);
    setProgressStageTitle('ขั้นตอนที่ 2: ค้นหาครีเอเตอร์สดบน TikTok & ตรวจสอบประวัติคลิป');
    setProgressStageDesc('กวาดคลิปสดบน TikTok ประเทศไทยตามคำค้นหาเฉพาะของแบรนด์ และดึงคลิปย้อนหลังมาตรวจสอบความเชี่ยวชาญจริง (5-Clip Niche Consistency Audit)...');
    setLiveLogs([
      `[Pipeline] เริ่มค้นหาและประมวลผลครีเอเตอร์สำหรับ '${brandDNA.brand_name}'...`,
      `[Apify Discovery] ค้นหาคลิปสดบน TikTok ประเทศไทย (Proxy: TH)...`,
    ]);

    const startTime = Date.now();
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsedSeconds(elapsed);
      if (elapsed < 8) {
        setActiveStep(2);
        setProgressPercent(Math.min(30, Math.round(5 + elapsed * 3.2)));
      } else if (elapsed < 20) {
        setActiveStep(2);
        setProgressStageTitle('ขั้นตอนที่ 2: ตรวจสอบความสม่ำเสมอของเนื้อหา (Niche Consistency)');
        setProgressStageDesc('ดึงคลิปย้อนหลัง 5 คลิปล่าสุด เพื่อตรวจวัดความเชี่ยวชาญเฉพาะทาง และคำนวณการพูดถึงคู่แข่ง...');
        setProgressPercent(Math.min(55, Math.round(30 + (elapsed - 8) * 2.1)));
        setLiveLogs(prev => !prev.some(l => l.includes('Co-occurrence')) ? [
          ...prev,
          `[Apify Enrichment] Auditing profile videos for candidate creators...`,
          `[Competitor Layer 2] Analyzing frequent hashtags for co-occurring competitor brands...`
        ] : prev);
      } else if (elapsed < 32) {
        setActiveStep(3);
        setProgressStageTitle('ขั้นตอนที่ 3: ระบบคัดกรอง 2 ด่าน & จำแนก 4 สไตล์ครีเอเตอร์ (2x2 Matrix)');
        setProgressStageDesc('ด่านที่ 1 ตัดร้านค้า บัญชี Official และบอทสแปมตะกร้าทิ้ง -> ด่านที่ 2 AI วิเคราะห์ความเข้ากันได้ และจำแนกเป็น 2 บทบาทหลัก (KOL / KOC) ครอบคลุม 4 สไตล์ย่อย...');
        setProgressPercent(Math.min(80, Math.round(55 + (elapsed - 20) * 2.0)));
        setLiveLogs(prev => !prev.some(l => l.includes('Relevance Gate')) ? [
          ...prev,
          `[Gate 1] Purging Official Shops & Smart Affiliate Spam Bots (Basket >85% + Zero comments)...`,
          `[Gate 2] Gemini Batch Relevance Gate evaluating creators in 1 API call...`,
          `[2x2 Matrix] Classifying 2 Roles (KOL/KOC) into 4 Sub-Styles...`
        ] : prev);
      } else {
        setActiveStep(4);
        setProgressStageTitle('ขั้นตอนที่ 4: ประเมินคะแนนความเข้ากันได้ & จัดพอร์ตโฟลิโอตาม Media Mix');
        setProgressStageDesc('คำนวณคะแนนตาม Conversion Model (Relevance 40 + Engagement 35 + Commercial Proxy 25) และจัดอันดับ Top-K ให้ได้สัดส่วน KOL:KOC ตามเป้าหมาย...');
        setProgressPercent(Math.min(96, Math.round(80 + (elapsed - 32) * 0.8)));
        setLiveLogs(prev => !prev.some(l => l.includes('Scoring')) ? [
          ...prev,
          `[Scoring] Relevance (40) + Engagement Quality & Utility (35) + Audience Proxy (25)...`,
          `[Media Mix Top-K] Enforcing ${brandDNA.kol_koc_mix.kol}% KOL : ${brandDNA.kol_koc_mix.koc}% KOC portfolio...`,
          `[Brand-Customer Fit] Evaluating persona overlap and conversion drivers...`
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
          force_refresh: forceRefresh,
        }),
      });
      if (!res.ok) {
        let errText = '';
        try {
          const errJson = await res.json();
          errText = errJson.detail || JSON.stringify(errJson);
        } catch {
          errText = await res.text();
        }
        throw new Error(errText || `HTTP ${res.status}`);
      }
      const data: MatchResponse = await res.json();
      setProgressPercent(100);
      setProgressStageTitle('ประมวลผลเสร็จสมบูรณ์ 100%!');
      setProgressStageDesc(`จัดอันดับครีเอเตอร์ ${data.ranked_kols.length} รายการ ตรงตามกลยุทธ์ ${data.strategy?.conversion_model}`);
      setLiveLogs(prev => [
        ...prev,
        `[Success] Finished: ${data.ranked_kols.length} Top-K ranked (${data.strategy?.achieved_mix?.KOL || 0} KOL, ${data.strategy?.achieved_mix?.KOC || 0} KOC).`,
        `[Filtered] ${data.filter_stats?.removed_merchants || 0} merchants, ${data.filter_stats?.removed_affiliate_bots || 0} bots excluded.`
      ]);
      setMatchResponse(data);
      setActiveTab('all');
    } catch (err: any) {
      console.error('Match KOLs error:', err);
      parseAndSetApiError(err, '/api/match-kols');
    } finally {
      clearInterval(timer);
      setTimeout(() => {
        setIsMatching(false);
        setProgressPercent(0);
        setElapsedSeconds(0);
      }, 450);
    }
  };

  // 1-Click Auto Match End-to-End
  const handleAutoMatch = async () => {
    if (brandDNA && isEditingDNA) {
      return handleMatchKOLs();
    }
    if (!brandName && !websiteUrl && !facebookUrl && !customNotes) {
      alert('Please enter at least a Brand Name, Website URL, or Campaign Notes.');
      return;
    }
    setIsMatching(true);
    setApiError(null);
    setProgressPercent(5);
    setElapsedSeconds(0);
    setActiveStep(1);
    setProgressStageTitle('1-Click Match: กำลังวิเคราะห์ Brand DNA & กวาดค้นหา TikTok...');
    setProgressStageDesc('รันกระบวนการทั้ง 4 ขั้นตอนแบบอัตโนมัติสมบูรณ์...');
    setLiveLogs([
      `[1-Click Match] Launching End-to-End autonomous pipeline...`,
      `[Stage 1] Extracting Brand DNA, Conversion Model and Scene Translation queries...`,
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
        setProgressPercent(Math.min(25, Math.round(5 + elapsed * 2.5)));
      } else if (elapsed < 20) {
        setActiveStep(2);
        setProgressStageTitle('Stage 2: TikTok Discovery via Apify Scraper');
        setProgressStageDesc('กวาดคลิปสดบน TikTok ประเทศไทย (Country: TH)...');
        setProgressPercent(Math.min(55, Math.round(25 + (elapsed - 8) * 2.3)));
      } else if (elapsed < 34) {
        setActiveStep(3);
        setProgressStageTitle('Stage 3: Two-Stage Filtering & 2x2 Classification');
        setProgressStageDesc('คัดกรองร้านค้า/บอท และจัดเข้า 4 สไตล์ย่อย...');
        setProgressPercent(Math.min(80, Math.round(55 + (elapsed - 20) * 1.8)));
      } else {
        setActiveStep(4);
        setProgressStageTitle('Stage 4: Dynamic Scoring & 3-Sec Pitch Hooks');
        setProgressStageDesc('คำนวณคะแนน 40/35/25 และสร้าง Campaign Hooks...');
        setProgressPercent(Math.min(96, Math.round(80 + (elapsed - 34) * 0.7)));
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
          force_refresh: forceRefresh,
        }),
      });
      if (!res.ok) {
        let errText = '';
        try {
          const errJson = await res.json();
          errText = errJson.detail || JSON.stringify(errJson);
        } catch {
          errText = await res.text();
        }
        throw new Error(errText || `HTTP ${res.status}`);
      }
      const data: MatchResponse = await res.json();
      setProgressPercent(100);
      setProgressStageTitle('จัดอันดับและประมวลผลเสร็จสมบูรณ์ 100%!');
      setProgressStageDesc(`พบครีเอเตอร์ ${data.ranked_kols.length} รายการ ตรงตามกลยุทธ์ ${data.strategy?.conversion_model}`);
      setBrandDNA(data.brand_dna);
      setMatchResponse(data);
      setActiveTab('all');
    } catch (err: any) {
      console.error('Auto-match error:', err);
      parseAndSetApiError(err, '/api/auto-match');
    } finally {
      clearInterval(timer);
      setTimeout(() => {
        setIsMatching(false);
        setProgressPercent(0);
        setElapsedSeconds(0);
      }, 450);
    }
  };

  // Copy 3-second hook
  const handleCopyHook = (id: string, hook: string) => {
    navigator.clipboard.writeText(hook);
    setCopiedHookId(id);
    setTimeout(() => setCopiedHookId(null), 2500);
  };

  // --------------------------------------------------------------------------
  // Filtered Ranked KOLs (3-Level Filter Bar: Main Role, Sub-style & Follower Tier)
  // --------------------------------------------------------------------------
  const filteredRankedKOLs = useMemo(() => {
    if (!matchResponse) return [];
    let list = [...matchResponse.ranked_kols];

    // Main Role Filter (Spec 6.2: All / 🧠 KOL / 🛍️ KOC)
    if (roleFilter !== 'All') {
      list = list.filter(item => item.kol.funnel_role === roleFilter);
    }

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        item =>
          item.kol.display_name.toLowerCase().includes(q) ||
          item.kol.handle.toLowerCase().includes(q) ||
          item.kol.bio.toLowerCase().includes(q) ||
          item.kol.sub_style?.toLowerCase().includes(q) ||
          item.score_breakdown.matched_keywords.some(k => k.toLowerCase().includes(q))
      );
    }

    // Follower Tier Filter
    if (tierFilter !== 'All') {
      list = list.filter(item => item.kol.tier.toLowerCase() === tierFilter.toLowerCase());
    }

    // Sub-Style Tab Filter
    if (activeTab === 'guru') {
      list = list.filter(item => item.kol.sub_style === 'KOL - Expert / Guru');
    } else if (activeTab === 'lifestyle') {
      list = list.filter(item => item.kol.sub_style === 'KOL - Lifestyle / Aesthetic');
    } else if (activeTab === 'hardsell') {
      list = list.filter(item => item.kol.sub_style === 'KOC - Hard-Sell Reviewer');
    } else if (activeTab === 'everyday') {
      list = list.filter(item => item.kol.sub_style === 'KOC - Everyday User / Vlog');
    }

    // Sort order
    if (sortBy === 'er') {
      list.sort((a, b) => b.score_breakdown.median_engagement_rate - a.score_breakdown.median_engagement_rate);
    } else if (sortBy === 'followers') {
      list.sort((a, b) => b.kol.follower_count - a.kol.follower_count);
    } else {
      list.sort((a, b) => b.total_match_score - a.total_match_score);
    }

    return list;
  }, [matchResponse, roleFilter, searchQuery, tierFilter, sortBy, activeTab]);

  // Export to CSV (Spec 5.3)
  const exportToCSV = () => {
    if (!matchResponse) return;
    const headers = [
      'Rank',
      'TikTok Handle',
      'Display Name',
      'TikTok URL',
      'Followers',
      'Tier',
      'Funnel Role',
      '2x2 Sub-Style',
      'Work-Ready Signal',
      'Competitor Conflict / Opportunity',
      'Total Match Score',
      'Relevance Score (40)',
      'Engagement Score (35)',
      'Audience Score (25)',
      'Median ER %',
      'Save/Share Utility',
      'View Consistency',
      'Yellow Basket Ratio %',
      'Strategic Fit Rationale',
      '3-Second Pitch Hook',
    ];
    const rows = matchResponse.ranked_kols.map(item => [
      item.rank,
      `@${item.kol.handle}`,
      `"${item.kol.display_name.replace(/"/g, '""')}"`,
      item.kol.tiktok_url,
      item.kol.follower_count,
      item.kol.tier,
      item.kol.funnel_role || 'KOL',
      `"${item.kol.sub_style || 'N/A'}"`,
      item.kol.is_work_ready ? 'YES' : 'NO',
      `"${(item.kol.competitor_flags?.map(f => f.label).join(' | ') || 'None').replace(/"/g, '""')}"`,
      item.total_match_score,
      item.score_breakdown.relevance_total,
      item.score_breakdown.engagement_total,
      item.score_breakdown.audience_total,
      `${(item.score_breakdown.median_engagement_rate * 100).toFixed(2)}%`,
      (item.score_breakdown.utility_score || 0).toFixed(4),
      (item.score_breakdown.view_consistency_ratio || 0).toFixed(3),
      `${Math.round(item.kol.signals.basket_ratio * 100)}%`,
      `"${(item.kol.why_it_fits || '').replace(/"/g, '""')}"`,
      `"${(item.pitch_hook || '').replace(/"/g, '""')}"`,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,\uFEFF' +
      [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `convert_cake_${brandDNA?.brand_name || 'brand'}_kols.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const modelInfo = brandDNA?.conversion_model ? MODEL_DETAILS[brandDNA.conversion_model] : null;

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
            {/* Convert Cake Monogram */}
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
                  <span>TikTok Matching Engine</span>
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                Performance-Only Marketing Agency · 4-Stage Funnel Architecture · Zero-Mock
              </p>
            </div>
          </div>

          {/* Engine Status Health Pill */}
          <div className="flex items-center space-x-3">
            <div className="hidden md:flex items-center space-x-3 text-xs text-slate-400 pr-2 border-r border-slate-200/90">
              <span className="flex items-center space-x-1">
                <Award className="w-3.5 h-3.5 text-[#597ef3]" />
                <span>2x2 KOL/KOC Funnel Matrix</span>
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
                {apiOnline === true ? 'Engine Ready' : apiOnline === false ? 'Engine Offline' : 'Checking...'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* PIPELINE OVERVIEW BANNER */}
        <div className="relative overflow-hidden rounded-3xl bg-white border border-slate-200/90 p-6 sm:p-7 shadow-xs">
          <div className="relative z-10 flex flex-col justify-between gap-4">
            <div className="space-y-2 max-w-4xl">
              <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#0536d2] bg-blue-50 border border-blue-200/80 px-3 py-1 rounded-full">
                <Sparkles className="w-3.5 h-3.5 text-[#03e78b]" />
                <span>Performance-Driven Creator Discovery</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-slate-950 tracking-tight leading-snug">
                Convert Cake TikTok KOL/KOC Matching Engine
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
                ระบบค้นหาและจับคู่ครีเอเตอร์ TikTok แบบ Live 100% สำหรับแบรนด์ไทย — วิเคราะห์จุดขายและ Business Model จากเว็บไซต์จริง เพื่อกำหนดสัดส่วน KOL และ KOC ที่ช่วยสร้างยอดขายได้จริง พร้อมระบบตัดร้านค้า/บอทสแปมตะกร้า และประเมินความสม่ำเสมอของเนื้อหา (Niche Consistency)
              </p>
            </div>
          </div>
        </div>

        {/* 2-COLUMN WORKFLOW */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* LEFT COLUMN: Input Brand & Extracted Brand DNA (5 Cols) */}
          <div className="lg:col-span-5 space-y-5">
            {/* Input Card */}
            <div className="bg-white border border-slate-200/90 rounded-3xl p-5 sm:p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200/90 pb-3.5">
                <div className="flex items-center space-x-2.5">
                  <span className="flex items-center justify-center w-7 h-7 rounded-xl bg-[#0536d2]/20 text-[#597ef3] text-xs font-black border border-[#0536d2]/40">
                    1
                  </span>
                  <h3 className="font-bold text-slate-900 text-base">Brand Information</h3>
                </div>
                <span className="text-[11px] font-bold text-[#03e78b] bg-[#03e78b]/10 border border-[#03e78b]/25 px-2.5 py-0.5 rounded-full flex items-center space-x-1">
                  <Globe className="w-3 h-3" />
                  <span>Jina + Facebook Ingestion</span>
                </span>
              </div>

              <div className="space-y-3.5 pt-1">
                {/* 6 Industry Test Cases Selection */}
                <div className="bg-slate-50/90 border border-slate-200/90 rounded-2xl p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-800">
                      <Sparkles className="w-3.5 h-3.5 text-[#0536d2]" />
                      <span>ชุดทดสอบ 6 Industry (Quick Test Cases)</span>
                    </div>
                    {selectedTestCase && (
                      <button
                        type="button"
                        onClick={handleClearInputs}
                        className="text-[11px] font-semibold text-slate-500 hover:text-rose-600 transition cursor-pointer"
                      >
                        ล้างข้อมูล
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {INDUSTRY_TEST_CASES.map(tc => {
                      const isSelected = selectedTestCase === tc.id;
                      return (
                        <button
                          key={tc.id}
                          type="button"
                          onClick={() => handleSelectTestCase(tc)}
                          className={`p-2.5 rounded-xl text-left border transition-all cursor-pointer flex flex-col justify-between ${
                            isSelected
                              ? 'bg-blue-50/90 border-[#0536d2] ring-2 ring-[#0536d2]/20 shadow-xs'
                              : 'bg-white hover:bg-slate-100/80 border-slate-200 hover:border-slate-300 text-slate-700'
                          }`}
                          title={`${tc.industry} — ${tc.name}`}
                        >
                          <div className="flex items-center space-x-1.5 mb-1">
                            <span className="text-sm">{tc.icon}</span>
                            <span
                              className={`text-[10px] font-bold uppercase tracking-wider truncate ${
                                isSelected ? 'text-[#0536d2]' : 'text-slate-500'
                              }`}
                            >
                              {tc.industry}
                            </span>
                          </div>
                          <div className="text-xs font-bold text-slate-900 truncate">
                            {tc.label}
                          </div>
                          <div className="text-[10px] text-slate-500 truncate mt-0.5">
                            {tc.badge}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-800 mb-1.5">
                    Brand Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={e => setBrandName(e.target.value)}
                    placeholder="ระบุชื่อแบรนด์ลูกค้า เช่น Her Hyness, Srichand"
                    className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] focus:ring-2 focus:ring-[#0536d2]/15 transition"
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
                    placeholder="ระบุจุดเด่นสินค้า ปัญหาที่แบรนด์ช่วยแก้ หรือบรีฟการตลาดเพิ่มเติม"
                    className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] focus:ring-1 focus:ring-[#0536d2]/20 transition"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center justify-between">
                    <span>Optional Competitor Override</span>
                    <span className="text-[10px] text-slate-400 font-normal">คั่นด้วยเครื่องหมายจุลภาค</span>
                  </label>
                  <input
                    type="text"
                    value={manualCompetitors}
                    onChange={e => setManualCompetitors(e.target.value)}
                    placeholder="รายชื่อคู่แข่งเพิ่มเติม (เว้นว่างได้ ระบบสกัดให้อัตโนมัติ)"
                    className="w-full bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] focus:ring-1 focus:ring-[#0536d2]/20 transition"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2.5 pt-2">
                <button
                  onClick={handleAnalyzeBrand}
                  disabled={isMatching || isAnalyzing}
                  className="flex-1 py-3 rounded-2xl bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 font-bold text-xs shadow-xs transition flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#0536d2]" />
                      <span>Analyzing Brand DNA...</span>
                    </>
                  ) : (
                    <>
                      <Layers className="w-3.5 h-3.5 text-[#0536d2]" />
                      <span>Step 1: Extract Brand DNA</span>
                    </>
                  )}
                </button>

                <button
                  onClick={handleAutoMatch}
                  disabled={isMatching || isAnalyzing}
                  className="flex-1 py-3 rounded-2xl bg-[#0536d2] hover:bg-[#042cae] text-white font-bold text-xs shadow-md shadow-blue-600/20 transition flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  {isMatching ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-white" />
                      <span>Matching TikTok...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-3.5 h-3.5 text-[#03e78b]" />
                      <span>1-Click Auto Match</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Extracted Brand DNA Card */}
            {brandDNA && (
              <div className="bg-white border border-slate-200/90 rounded-3xl p-5 sm:p-6 shadow-xs space-y-4 animate-in fade-in duration-300">
                <div className="flex items-center justify-between border-b border-slate-200/90 pb-3.5">
                  <div className="flex items-center space-x-2">
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
                  {/* Conversion Model Badge */}
                  <div className="p-3.5 rounded-2xl bg-gradient-to-r from-blue-50 to-indigo-50/60 border border-blue-200/90 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-[#0536d2] uppercase tracking-wider">
                        Conversion Model (วิธีทำเงิน)
                      </span>
                      <span className="font-black text-xs px-2.5 py-0.5 rounded-lg bg-blue-600 text-white font-mono">
                        {brandDNA.conversion_model}
                      </span>
                    </div>
                    <div className="flex items-center justify-between pt-1 text-[11px]">
                      <span className="text-slate-600">สัดส่วนที่แนะนำ (Media Mix):</span>
                      <span className="font-extrabold text-slate-900 bg-white px-2 py-0.5 rounded-md border border-slate-200 font-mono">
                        KOL {brandDNA.kol_koc_mix?.kol}% : KOC {brandDNA.kol_koc_mix?.koc}%
                      </span>
                    </div>
                    {brandDNA.conversion_model_reason && (
                      <p className="text-[11px] text-slate-600 italic pt-0.5">
                        "{brandDNA.conversion_model_reason}"
                      </p>
                    )}
                  </div>

                  <div>
                    <span className="text-slate-500 font-medium block mb-1">Target Audience & Market:</span>
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

                  {/* Plain & Natural Thai Search Queries (Spec 3.2) */}
                  <div>
                    <span className="text-slate-600 font-bold block mb-1.5 flex items-center justify-between">
                      <span>Plain & Natural Thai Search Queries ({brandDNA.search_queries?.length || 0}):</span>
                      <span className="text-[10px] text-slate-400 font-normal">2-4 words / ≤18 letters / Zero Hardcoded Templates</span>
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {brandDNA.search_queries?.map((q, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 rounded-xl bg-indigo-50/80 border border-indigo-200 text-indigo-950 text-xs font-medium flex items-center space-x-1.5"
                        >
                          <span className="text-indigo-600 font-bold font-mono">#</span>
                          <span>{q.query}</span>
                          {q.syntax_rule && (
                            <span className="text-[9px] uppercase px-1.5 py-0.2 rounded-md bg-white text-indigo-700 border border-indigo-100 font-mono">
                              {q.syntax_rule.replace('_', ' ')}
                            </span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Grounded Thai Competitor Dictionary (Spec 5.1) */}
                  {brandDNA.competitors && brandDNA.competitors.length > 0 && (
                    <div>
                      <span className="text-slate-600 font-bold block mb-1.5">
                        Grounded Thai Competitors ({brandDNA.competitors.length}):
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {brandDNA.competitors.map((c, i) => (
                          <span
                            key={i}
                            className="px-2.5 py-1 rounded-xl bg-slate-50 text-slate-800 text-[11px] border border-slate-200 font-medium"
                            title={`Source: ${c.source}`}
                          >
                            <span>{c.brand}</span>
                            {c.aliases && c.aliases.length > 1 && (
                              <span className="text-slate-400 text-[10px] ml-1">
                                ({c.aliases.filter(a => a !== c.brand).slice(0, 1).join(', ')})
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Match Button if DNA exists */}
                <button
                  onClick={handleMatchKOLs}
                  disabled={isMatching || isAnalyzing}
                  className="w-full mt-2 py-3.5 rounded-2xl bg-[#0536d2] hover:bg-[#042cae] text-white font-bold text-xs shadow-md shadow-blue-600/20 transition flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  {isMatching ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-white" />
                      <span>Matching Live TikTok Creators...</span>
                    </>
                  ) : (
                    <>
                      <Compass className="w-4 h-4 text-[#03e78b]" />
                      <span>Run Stage 2-4 Match (TikTok Scraper & 2x2 Matrix)</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Results Dashboard (7 Cols) */}
          <div className="lg:col-span-7 space-y-4">
            {/* DEDICATED API ERROR / QUOTA LIMIT / TOKEN EXHAUSTED SCREEN */}
            {apiError && (
              <div className="bg-white border-2 border-rose-300 rounded-3xl p-6 sm:p-7 shadow-lg shadow-rose-500/5 space-y-5 relative overflow-hidden animate-in fade-in duration-300">
                <div className="h-1.5 bg-gradient-to-r from-rose-500 via-amber-500 to-[#0536d2] absolute top-0 left-0 right-0" />

                {/* Error Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start space-x-3.5">
                    <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 shadow-xs shrink-0">
                      <AlertOctagon className="w-6 h-6 animate-pulse" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                        <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-rose-100 text-rose-800 border border-rose-200">
                          🚨 HTTP {apiError.status || 402} {apiError.type.toUpperCase()}
                        </span>
                        <span className="text-[11px] text-slate-400 font-mono">
                          ตรวจพบ: {apiError.timestamp}
                        </span>
                      </div>
                      <h3 className="text-base sm:text-lg font-black text-slate-900 mt-1">
                        {apiError.title}
                      </h3>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setApiError(null)}
                    className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition cursor-pointer"
                    title="ปิดข้อความแจ้งเตือน"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Error Cause (บอกแค่ว่า error จากอะไร) */}
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <div className="text-xs font-bold text-slate-800 flex items-center space-x-1.5">
                    <span>สาเหตุของข้อผิดพลาด (Error Cause):</span>
                  </div>
                  <div className="bg-rose-50/70 border border-rose-200 rounded-2xl p-4 space-y-2">
                    <p className="text-xs text-rose-950 font-medium leading-relaxed">
                      {apiError.message}
                    </p>
                    {apiError.details && apiError.details !== apiError.message && (
                      <div className="pt-2 border-t border-rose-200/60 font-mono text-[11px] text-rose-800 break-all whitespace-pre-wrap bg-white/80 p-3 rounded-xl border border-rose-100">
                        {apiError.details}
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions: ปุ่ม Retry */}
                <div className="pt-2 flex items-center justify-end space-x-2.5">
                  <button
                    type="button"
                    onClick={() => setApiError(null)}
                    className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 font-bold text-xs transition cursor-pointer"
                  >
                    ปิด
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setApiError(null);
                      if (apiError.endpoint === '/api/analyze-brand') {
                        handleAnalyzeBrand();
                      } else if (apiError.endpoint === '/api/match-kols' && brandDNA) {
                        handleMatchKOLs();
                      } else {
                        handleAutoMatch();
                      }
                    }}
                    className="px-5 py-2.5 rounded-xl bg-[#0536d2] hover:bg-[#042cae] text-white font-bold text-xs shadow-md shadow-blue-600/20 transition flex items-center space-x-2 cursor-pointer"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>ลองใหม่อีกครั้ง (Retry)</span>
                  </button>
                </div>
              </div>
            )}

            {/* 1. STRATEGY SUMMARY BANNER (Spec 5.3 #1) */}
            {matchResponse && matchResponse.strategy && (
              <div className="bg-white border-2 border-[#597ef3]/30 rounded-3xl p-5 shadow-sm space-y-3 relative overflow-hidden animate-in fade-in duration-300">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2.5">
                    <span className="text-2xl">{modelInfo?.icon || '🎯'}</span>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#0536d2] block">
                        Campaign Strategy & Media Mix
                      </span>
                      <h4 className="text-base font-extrabold text-slate-900">
                        {modelInfo?.label || matchResponse.strategy.conversion_model}
                      </h4>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <div className="text-right">
                      <span className="text-[10px] text-slate-500 block">Recommended Mix</span>
                      <span className="text-xs font-black text-[#0536d2] font-mono">
                        KOL {matchResponse.strategy.recommended_mix?.kol}% : KOC {matchResponse.strategy.recommended_mix?.koc}%
                      </span>
                    </div>
                    <div className="h-6 w-px bg-slate-200" />
                    <div className="text-right">
                      <span className="text-[10px] text-slate-500 block">Achieved Top-K</span>
                      <span className="text-xs font-black text-emerald-700 font-mono">
                        {matchResponse.strategy.achieved_mix?.KOL || 0} KOL : {matchResponse.strategy.achieved_mix?.KOC || 0} KOC
                      </span>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">
                  {modelInfo?.desc || matchResponse.strategy.conversion_model_reason}
                </p>

                {/* Plain & Natural Search Queries Tag Cloud (Spec 6.2) */}
                {brandDNA?.search_queries && brandDNA.search_queries.length > 0 && (
                  <div className="pt-2 border-t border-slate-200/60 space-y-1.5">
                    <span className="text-[11px] font-bold text-slate-700 flex items-center space-x-1">
                      <span>🔍 Plain & Natural Thai Search Queries ({brandDNA.search_queries.length}):</span>
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {brandDNA.search_queries.map((q, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-1 rounded-xl bg-white/90 border border-slate-200/90 text-[11px] font-medium text-slate-800 shadow-2xs font-mono flex items-center space-x-1"
                        >
                          <span className="text-indigo-600 font-bold">#</span>
                          <span>{q.query}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Filter statistics bar */}
                {matchResponse.filter_stats && (
                  <div className="flex items-center space-x-4 pt-1 text-[11px] text-slate-500 font-mono flex-wrap gap-y-1">
                    <span>Evaluated {matchResponse.filter_stats.unique_creators} Creators</span>
                    <span>•</span>
                    <span className="text-rose-600">Filtered: {matchResponse.filter_stats.removed_merchants} Merchants, {matchResponse.filter_stats.removed_affiliate_bots} Spam Bots</span>
                    <span>•</span>
                    <span className="text-emerald-700 font-semibold">{matchResponse.filter_stats.scored} Qualified</span>
                  </div>
                )}
              </div>
            )}

            {/* 2. FILTER BAR (Spec 6.2: Clean Non-Overlapping Role & Sub-Style Filters) */}
            <div className="bg-white border border-slate-200/90 rounded-3xl p-4 shadow-xs space-y-3">
              {/* Level 1: Primary Role Tabs (ทั้งหมด / 🧠 KOL / 🛍️ KOC / 🚫 กรองออก) */}
              <div className="flex items-center space-x-2 pb-2 border-b border-slate-100 flex-wrap gap-y-1.5 text-xs">
                <span className="text-slate-500 font-bold text-[11px] uppercase tracking-wider mr-1">บทบาทหลัก:</span>
                <button
                  type="button"
                  onClick={() => {
                    setRoleFilter('All');
                    if (activeTab === 'excluded') setActiveTab('all');
                  }}
                  className={`px-3 py-1.5 rounded-xl transition cursor-pointer font-semibold flex items-center space-x-1.5 ${
                    roleFilter === 'All' && activeTab !== 'excluded'
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  <span>ทั้งหมด (All Matches)</span>
                  {matchResponse && (
                    <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                      roleFilter === 'All' && activeTab !== 'excluded' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-800'
                    }`}>
                      {matchResponse.ranked_kols.length}
                    </span>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setRoleFilter('KOL');
                    if (activeTab === 'hardsell' || activeTab === 'everyday' || activeTab === 'excluded') {
                      setActiveTab('all');
                    }
                  }}
                  className={`px-3 py-1.5 rounded-xl transition cursor-pointer font-semibold flex items-center space-x-1.5 ${
                    roleFilter === 'KOL' && activeTab !== 'excluded'
                      ? 'bg-[#0536d2] text-white shadow-xs'
                      : 'bg-blue-50 text-[#0536d2] border border-blue-200 hover:bg-blue-100'
                  }`}
                >
                  <span>🧠 KOL (Key Opinion Leader)</span>
                  {matchResponse && (
                    <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                      roleFilter === 'KOL' && activeTab !== 'excluded' ? 'bg-white/20 text-white' : 'bg-blue-100 text-[#0536d2]'
                    }`}>
                      {matchResponse.ranked_kols.filter(k => k.kol.funnel_role === 'KOL').length}
                    </span>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setRoleFilter('KOC');
                    if (activeTab === 'guru' || activeTab === 'lifestyle' || activeTab === 'excluded') {
                      setActiveTab('all');
                    }
                  }}
                  className={`px-3 py-1.5 rounded-xl transition cursor-pointer font-semibold flex items-center space-x-1.5 ${
                    roleFilter === 'KOC' && activeTab !== 'excluded'
                      ? 'bg-emerald-700 text-white shadow-xs'
                      : 'bg-emerald-50 text-emerald-900 border border-emerald-200 hover:bg-emerald-100'
                  }`}
                >
                  <span>🛍️ KOC (Key Opinion Consumer)</span>
                  {matchResponse && (
                    <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                      roleFilter === 'KOC' && activeTab !== 'excluded' ? 'bg-white/20 text-white' : 'bg-emerald-100 text-emerald-900'
                    }`}>
                      {matchResponse.ranked_kols.filter(k => k.kol.funnel_role === 'KOC').length}
                    </span>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('excluded')}
                  className={`px-3 py-1.5 rounded-xl transition cursor-pointer font-semibold flex items-center space-x-1.5 ml-auto ${
                    activeTab === 'excluded'
                      ? 'bg-rose-600 text-white shadow-xs'
                      : 'bg-rose-50 text-rose-800 border border-rose-200 hover:bg-rose-100'
                  }`}
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>กรองออก (Filtered Out)</span>
                  {matchResponse && (
                    <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                      activeTab === 'excluded' ? 'bg-white/20 text-white' : 'bg-rose-100 text-rose-800'
                    }`}>
                      {matchResponse.excluded_creators?.length || 0}
                    </span>
                  )}
                </button>
              </div>

              {/* Level 2: Contextual Sub-Style Filter Pills (แสดงเฉพาะสไตล์ที่สัมพันธ์กับ Role ที่เลือก ไม่ซ้ำซ้อน ไม่ตีกัน) */}
              {activeTab !== 'excluded' && (
                <div className="flex items-center space-x-1.5 border-b border-slate-100 pb-2.5 overflow-x-auto text-xs font-semibold">
                  <span className="text-slate-500 font-medium text-[11px] mr-1 whitespace-nowrap">สไตล์คอนเทนต์:</span>
                  <button
                    type="button"
                    onClick={() => setActiveTab('all')}
                    className={`px-2.5 py-1 rounded-lg transition cursor-pointer whitespace-nowrap flex items-center space-x-1 ${
                      activeTab === 'all'
                        ? 'bg-slate-800 text-white shadow-2xs font-bold'
                        : 'text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200'
                    }`}
                  >
                    <span>{roleFilter === 'All' ? 'ทุกสไตล์' : roleFilter === 'KOL' ? 'ทุกสไตล์ KOL' : 'ทุกสไตล์ KOC'}</span>
                  </button>

                  {(roleFilter === 'All' || roleFilter === 'KOL') && (
                    <>
                      <button
                        type="button"
                        onClick={() => setActiveTab('guru')}
                        className={`px-2.5 py-1 rounded-lg transition cursor-pointer whitespace-nowrap flex items-center space-x-1 ${
                          activeTab === 'guru'
                            ? 'bg-indigo-600 text-white shadow-2xs font-bold'
                            : 'text-indigo-900 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200/80'
                        }`}
                      >
                        <span>🎓 KOL: Expert / Guru</span>
                        {matchResponse && (
                          <span className="ml-1 text-[10px] opacity-80">
                            ({matchResponse.ranked_kols.filter(k => k.kol.sub_style === 'KOL - Expert / Guru').length})
                          </span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => setActiveTab('lifestyle')}
                        className={`px-2.5 py-1 rounded-lg transition cursor-pointer whitespace-nowrap flex items-center space-x-1 ${
                          activeTab === 'lifestyle'
                            ? 'bg-teal-600 text-white shadow-2xs font-bold'
                            : 'text-teal-900 bg-teal-50 hover:bg-teal-100 border border-teal-200/80'
                        }`}
                      >
                        <span>✨ KOL: Lifestyle</span>
                        {matchResponse && (
                          <span className="ml-1 text-[10px] opacity-80">
                            ({matchResponse.ranked_kols.filter(k => k.kol.sub_style === 'KOL - Lifestyle / Aesthetic').length})
                          </span>
                        )}
                      </button>
                    </>
                  )}

                  {(roleFilter === 'All' || roleFilter === 'KOC') && (
                    <>
                      <button
                        type="button"
                        onClick={() => setActiveTab('hardsell')}
                        className={`px-2.5 py-1 rounded-lg transition cursor-pointer whitespace-nowrap flex items-center space-x-1 ${
                          activeTab === 'hardsell'
                            ? 'bg-purple-600 text-white shadow-2xs font-bold'
                            : 'text-purple-900 bg-purple-50 hover:bg-purple-100 border border-purple-200/80'
                        }`}
                      >
                        <span>🛍️ KOC: Hard-Sell Reviewer</span>
                        {matchResponse && (
                          <span className="ml-1 text-[10px] opacity-80">
                            ({matchResponse.ranked_kols.filter(k => k.kol.sub_style === 'KOC - Hard-Sell Reviewer').length})
                          </span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => setActiveTab('everyday')}
                        className={`px-2.5 py-1 rounded-lg transition cursor-pointer whitespace-nowrap flex items-center space-x-1 ${
                          activeTab === 'everyday'
                            ? 'bg-amber-600 text-white shadow-2xs font-bold'
                            : 'text-amber-900 bg-amber-50 hover:bg-amber-100 border border-amber-200/80'
                        }`}
                      >
                        <span>🤳 KOC: Everyday Vlog</span>
                        {matchResponse && (
                          <span className="ml-1 text-[10px] opacity-80">
                            ({matchResponse.ranked_kols.filter(k => k.kol.sub_style === 'KOC - Everyday User / Vlog').length})
                          </span>
                        )}
                      </button>
                    </>
                  )}
                </div>
              )}

              {/* Level 2: Search, Tier, Sort, Top-K & Export CSV */}
              <div className="flex flex-wrap items-center justify-between gap-2.5 pt-0.5">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search creator, bio..."
                    className="bg-white border border-slate-200 rounded-2xl pl-8.5 pr-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0536d2] w-36 sm:w-48 transition"
                  />
                </div>

                <div className="flex items-center space-x-2 flex-wrap">
                  {/* Follower Tier Filter */}
                  <select
                    value={tierFilter}
                    onChange={e => setTierFilter(e.target.value)}
                    className="bg-white border border-slate-200 rounded-2xl px-3 py-2 text-slate-800 text-xs focus:outline-none focus:border-[#0536d2]"
                  >
                    <option value="All">All Tiers</option>
                    <option value="Nano">Nano (1K-10K)</option>
                    <option value="Micro">Micro (10K-100K)</option>
                    <option value="Mid-Tier">Mid-Tier (100K-500K)</option>
                    <option value="Macro">Macro (500K+)</option>
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
                    className="bg-white border border-slate-200 rounded-2xl px-3 py-2 text-[#0536d2] font-semibold text-xs focus:outline-none"
                  >
                    <option value={10}>Top 10</option>
                    <option value={20}>Top 20</option>
                    <option value={30}>Top 30</option>
                  </select>

                  {matchResponse && (
                    <button
                      onClick={exportToCSV}
                      className="px-3 py-2 rounded-2xl bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 transition flex items-center space-x-1.5 cursor-pointer shadow-xs"
                      title="Export recommendations to CSV"
                    >
                      <Download className="w-3.5 h-3.5 text-[#0536d2]" />
                      <span>CSV</span>
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Live Progress Stepper */}
            {(isMatching || (isAnalyzing && !matchResponse)) && (
              <div className="bg-white border-2 border-[#597ef3]/40 rounded-3xl p-6 sm:p-7 space-y-5 shadow-lg shadow-blue-500/5 animate-in fade-in duration-300">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <span className="flex items-center space-x-2 text-xs font-extrabold text-[#0536d2] uppercase tracking-wider">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#03e78b] animate-ping" />
                    <span>{isMatching ? 'Stage 2-4 Live Pipeline' : 'Stage 1 Brand Analysis'}</span>
                  </span>
                  <div className="flex items-baseline space-x-1">
                    <span className="text-2xl font-black text-[#0536d2] font-mono">{progressPercent}%</span>
                    <span className="text-xs text-slate-400 font-mono">({elapsedSeconds}s)</span>
                  </div>
                </div>

                <div className="w-full h-3.5 rounded-full bg-slate-100 border border-slate-200 p-0.5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#0536d2] via-[#597ef3] to-[#03e78b] transition-all duration-300 ease-out"
                    style={{ width: `${Math.max(4, progressPercent)}%` }}
                  />
                </div>

                <div className="space-y-1 bg-blue-50/60 p-3.5 rounded-2xl border border-blue-200/80">
                  <h4 className="text-xs sm:text-sm font-bold text-slate-900 flex items-center space-x-2">
                    <RefreshCw className="w-3.5 h-3.5 text-[#0536d2] animate-spin" />
                    <span>{progressStageTitle}</span>
                  </h4>
                  <p className="text-xs text-slate-600 pl-5">{progressStageDesc}</p>
                </div>

                {liveLogs.length > 0 && (
                  <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 font-mono text-[11px] text-slate-300 space-y-1 max-h-28 overflow-y-auto" ref={logsContainerRef}>
                    {liveLogs.map((log, idx) => (
                      <div key={idx} className="flex items-start space-x-2">
                        <span className="text-[#03e78b] select-none">›</span>
                        <span className={log.includes('Success') ? 'text-emerald-400 font-bold' : 'text-slate-200'}>
                          {log}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Empty State */}
            {!isMatching && !isAnalyzing && !matchResponse && !apiError && (
              <div className="bg-white border border-slate-200/90 rounded-3xl p-12 text-center space-y-3 shadow-xs">
                <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto text-[#0536d2]">
                  <Search className="w-7 h-7 text-[#597ef3]" />
                </div>
                <h4 className="text-base font-bold text-slate-900">พร้อมค้นหาครีเอเตอร์ที่สร้างยอดขายได้จริง</h4>
                <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
                  เลือกแบรนด์ตัวอย่างจากชุด 6 Industry ด้านบน หรือกรอกข้อมูลแบรนด์ของคุณทางซ้าย แล้วกดปุ่ม <strong>"1-Click Auto Match"</strong> เพื่อเริ่มวิเคราะห์และค้นหาครีเอเตอร์สดทันที
                </p>
              </div>
            )}

            {/* 3. EXPLAINABLE CREATOR CARDS (Spec 5.3 #3) */}
            {!isMatching && !isAnalyzing && matchResponse && activeTab !== 'excluded' && activeTab !== 'trace' && (
              <div className="space-y-4">
                {filteredRankedKOLs.map(item => {
                  const isExpanded = expandedKOLId === item.kol.id;
                  const isCopied = copiedHookId === item.kol.id;

                  return (
                    <div
                      key={item.kol.id}
                      className="bg-white border border-slate-200/90 hover:border-[#597ef3]/50 rounded-3xl p-5 sm:p-6 shadow-xs transition space-y-4"
                    >
                      {/* Top Header: Rank, Names, Badges & Score */}
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start space-x-3.5">
                          {/* Avatar */}
                          <div className="relative shrink-0">
                            {item.kol.avatar_url ? (
                              <img
                                src={item.kol.avatar_url}
                                alt={item.kol.display_name}
                                className="w-13 h-13 rounded-2xl bg-slate-100 border-2 border-slate-200 object-cover"
                              />
                            ) : (
                              <div className="w-13 h-13 rounded-2xl bg-gradient-to-br from-[#0536d2] to-[#597ef3] border-2 border-blue-400 text-white font-bold text-lg flex items-center justify-center uppercase">
                                {(item.kol.display_name || item.kol.handle).slice(0, 1)}
                              </div>
                            )}
                            <span className="absolute -top-1.5 -left-1.5 flex items-center justify-center w-5 h-5 rounded-full bg-[#0536d2] text-white font-black text-[10px] shadow border border-[#597ef3]">
                              #{item.rank}
                            </span>
                          </div>

                          <div>
                            <div className="flex items-center space-x-2 flex-wrap">
                              <h4 className="font-bold text-slate-900 text-base">
                                {item.kol.display_name}
                              </h4>
                              {/* Direct TikTok profile link */}
                              <a
                                href={item.kol.tiktok_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center space-x-1 text-xs text-[#0536d2] hover:underline font-mono bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200 transition"
                              >
                                <span>@{item.kol.handle}</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            </div>

                            <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed">
                              {item.kol.bio}
                            </p>

                            {/* Badge row: Role, Sub-Style, Work-Ready, Tier */}
                            <div className="flex items-center space-x-2 text-xs text-slate-500 mt-2 flex-wrap gap-y-1">
                              {/* Main Role badge (Spec 6.2) */}
                              <span className={`inline-flex items-center space-x-1 font-bold text-[11px] px-2.5 py-0.5 rounded-lg border ${
                                item.kol.funnel_role === 'KOL'
                                  ? 'bg-blue-100 text-[#0536d2] border-blue-300'
                                  : 'bg-emerald-100 text-emerald-900 border-emerald-300'
                              }`}>
                                <span>{item.kol.funnel_role === 'KOL' ? '🧠 KOL' : '🛍️ KOC'}</span>
                              </span>

                              {/* Sub-style badge */}
                              {item.kol.sub_style && (
                                <span className={`inline-flex items-center space-x-1 font-bold text-[11px] px-2.5 py-0.5 rounded-lg border ${
                                  item.kol.sub_style.includes('Expert')
                                    ? 'bg-indigo-50 text-indigo-900 border-indigo-200'
                                    : item.kol.sub_style.includes('Lifestyle')
                                    ? 'bg-teal-50 text-teal-900 border-teal-200'
                                    : item.kol.sub_style.includes('Hard-Sell')
                                    ? 'bg-purple-50 text-purple-900 border-purple-200'
                                    : 'bg-amber-50 text-amber-900 border-amber-200'
                                }`}>
                                  <Award className="w-3 h-3" />
                                  <span>{item.kol.sub_style}</span>
                                </span>
                              )}

                              {/* Work-Ready badge */}
                              {item.kol.is_work_ready && (
                                <span className="inline-flex items-center space-x-1 font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-200 text-[11px]">
                                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                  <span>✅ Open for Work</span>
                                </span>
                              )}

                              <span className="text-slate-800 font-semibold px-2 py-0.5 rounded-lg bg-slate-100 border border-slate-200 text-[11px]">
                                {item.kol.tier} ({item.kol.follower_count.toLocaleString()})
                              </span>

                              {item.kol.signals.basket_ratio > 0 && (
                                <span className="inline-flex items-center space-x-1 text-[11px] text-amber-800 bg-amber-50 px-2 py-0.5 rounded-lg border border-amber-200 font-mono">
                                  <ShoppingBag className="w-3 h-3 text-amber-600" />
                                  <span>ตะกร้า {Math.round(item.kol.signals.basket_ratio * 100)}%</span>
                                </span>
                              )}
                            </div>

                            {/* Key Performance Metrics Bar (Spec 6.2: Followers, Median Views, ER%, Save Rate%) */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 text-center font-mono">
                              <div className="bg-slate-50 border border-slate-200/80 rounded-2xl py-2 px-2.5">
                                <span className="text-[10px] text-slate-500 block uppercase font-sans font-medium">Followers</span>
                                <span className="text-xs font-bold text-slate-800">{item.kol.follower_count.toLocaleString()}</span>
                              </div>
                              <div className="bg-slate-50 border border-slate-200/80 rounded-2xl py-2 px-2.5">
                                <span className="text-[10px] text-slate-500 block uppercase font-sans font-medium">Median Views</span>
                                <span className="text-xs font-bold text-slate-800">
                                  {item.kol.signals.median_views > 0
                                    ? Math.round(item.kol.signals.median_views).toLocaleString()
                                    : Math.round(item.kol.recent_videos.reduce((a, b) => a + b.views, 0) / Math.max(item.kol.recent_videos.length, 1)).toLocaleString()}
                                </span>
                              </div>
                              <div className="bg-slate-50 border border-slate-200/80 rounded-2xl py-2 px-2.5">
                                <span className="text-[10px] text-slate-500 block uppercase font-sans font-medium">Median ER%</span>
                                <span className="text-xs font-bold text-[#0536d2]">
                                  {(item.score_breakdown.median_engagement_rate * 100).toFixed(1)}%
                                </span>
                              </div>
                              <div className="bg-slate-50 border border-slate-200/80 rounded-2xl py-2 px-2.5">
                                <span className="text-[10px] text-slate-500 block uppercase font-sans font-medium">Save Rate%</span>
                                <span className="text-xs font-bold text-emerald-700">
                                  {(item.kol.signals.save_rate * 100).toFixed(2)}%
                                </span>
                              </div>
                            </div>

                            {/* Competitor Warning / Comparison Badge */}
                            {item.kol.competitor_flags && item.kol.competitor_flags.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1.5">
                                {item.kol.competitor_flags.map((flag, idx) => (
                                  <div
                                    key={idx}
                                    className={`px-3 py-1 rounded-xl text-xs font-semibold flex items-center space-x-1.5 border ${
                                      flag.type === 'conflict'
                                        ? 'bg-rose-50 text-rose-800 border-rose-200'
                                        : 'bg-indigo-50 text-indigo-800 border-indigo-200'
                                    }`}
                                  >
                                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                                    <span>{flag.label}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Match Score Badge */}
                        <div className="flex flex-col items-end space-y-1 shrink-0">
                          <div className="inline-flex items-baseline space-x-1 px-3.5 py-1.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 font-black text-lg shadow-xs">
                            <span>{item.total_match_score.toFixed(1)}</span>
                            <span className="text-[10px] text-emerald-600 font-semibold">/100</span>
                          </div>
                        </div>
                      </div>

                      {/* 1-Sentence Strategic Fit Rationale (Spec 4.1 Gate 2 & 5.3) */}
                      {item.kol.why_it_fits && (
                        <div className="p-3 rounded-2xl bg-blue-50/70 border border-blue-200 text-xs text-slate-800 leading-relaxed">
                          <strong className="text-[#0536d2] font-bold block mb-0.5">
                            💡 Strategic Brand Fit (Why this creator):
                          </strong>
                          {item.kol.why_it_fits}
                        </div>
                      )}

                      {/* 3-DIMENSION SCORE BREAKDOWN BARS (Spec 4.3: 40 / 35 / 25) */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs">
                        {/* 1. Relevance (40) */}
                        <div className="space-y-1.5">
                          <div className="flex justify-between items-center text-[11px]">
                            <span className="text-slate-600 font-semibold">1. Brand Relevance (40)</span>
                            <span className="font-bold text-slate-900 font-mono">
                              {item.score_breakdown.relevance_total.toFixed(1)} / 40
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-[#0536d2] to-[#597ef3] rounded-full transition-all"
                              style={{ width: `${(item.score_breakdown.relevance_total / 40) * 100}%` }}
                            />
                          </div>
                          <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                            <span>Semantic+LLM: {item.score_breakdown.semantic_llm_points.toFixed(1)}/30</span>
                            <span>Niche/Work: {item.score_breakdown.subniche_workready_points.toFixed(1)}/10</span>
                          </div>
                        </div>

                        {/* 2. Engagement Quality (35) */}
                        <div className="space-y-1.5">
                          <div className="flex justify-between items-center text-[11px]">
                            <span className="text-slate-600 font-semibold">2. Engagement Quality (35)</span>
                            <span className="font-bold text-slate-900 font-mono">
                              {item.score_breakdown.engagement_total.toFixed(1)} / 35
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-[#0536d2] to-emerald-500 rounded-full transition-all"
                              style={{ width: `${(item.score_breakdown.engagement_total / 35) * 100}%` }}
                            />
                          </div>
                          <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                            <span>Median ER: {(item.score_breakdown.median_engagement_rate * 100).toFixed(1)}%</span>
                            <span>Utility: {(item.score_breakdown.utility_score * 100).toFixed(1)}%</span>
                          </div>
                        </div>

                        {/* 3. Audience Proxy (25) */}
                        <div className="space-y-1.5">
                          <div className="flex justify-between items-center text-[11px]">
                            <span className="text-slate-600 font-semibold">3. Audience Proxy (25)</span>
                            <span className="font-bold text-slate-900 font-mono">
                              {item.score_breakdown.audience_total.toFixed(1)} / 25
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                            <div
                              className="h-full bg-emerald-500 rounded-full transition-all"
                              style={{ width: `${(item.score_breakdown.audience_total / 25) * 100}%` }}
                            />
                          </div>
                          <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                            <span>Thai: {item.score_breakdown.thai_authenticity_points.toFixed(1)}/10</span>
                            <span>Intent: {item.score_breakdown.buyer_intent_points.toFixed(1)}/10</span>
                          </div>
                        </div>
                      </div>

                      {/* 3-SECOND CAMPAIGN PITCH HOOK (Spec 5.2 & 5.3) */}
                      {item.pitch_hook && (
                        <div className="p-3.5 rounded-2xl bg-amber-50/60 border border-amber-200 flex items-start justify-between gap-3 text-xs">
                          <div className="space-y-1">
                            <span className="text-[10px] font-black uppercase tracking-wider text-amber-900 flex items-center space-x-1.5">
                              <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                              <span>3-Sec Role-Adaptive Pitch Hook ({item.kol.sub_style})</span>
                            </span>
                            <p className="text-slate-900 font-semibold italic text-xs leading-relaxed">
                              "{item.pitch_hook}"
                            </p>
                          </div>

                          <button
                            onClick={() => handleCopyHook(item.kol.id, item.pitch_hook)}
                            className="px-3 py-1.5 rounded-xl bg-white hover:bg-amber-100 border border-amber-300 text-amber-900 text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer shrink-0"
                          >
                            {isCopied ? (
                              <>
                                <Check className="w-3.5 h-3.5 text-emerald-600" />
                                <span className="text-emerald-700">Copied!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3.5 h-3.5 text-amber-700" />
                                <span>Copy Hook</span>
                              </>
                            )}
                          </button>
                        </div>
                      )}

                      {/* Audited Video Telemetry Drawer */}
                      {item.kol.recent_videos && item.kol.recent_videos.length > 0 && (
                        <div className="pt-1 border-t border-slate-100">
                          <button
                            onClick={() => setExpandedKOLId(isExpanded ? null : item.kol.id)}
                            className="w-full py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-xs text-slate-700 font-semibold transition flex items-center justify-center space-x-2 cursor-pointer border border-slate-200"
                          >
                            <BarChart3 className="w-3.5 h-3.5 text-[#0536d2]" />
                            <span>
                              {isExpanded
                                ? 'Hide Audited Video Telemetry'
                                : `Inspect Audited Videos (${item.kol.recent_videos.length}) & Intent Signals`}
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                            )}
                          </button>

                          {isExpanded && (
                            <div className="mt-3 space-y-3 bg-slate-50 p-4 rounded-2xl border border-slate-200 text-xs animate-in fade-in duration-200">
                              <h5 className="font-bold text-slate-900 text-xs flex items-center space-x-2">
                                <Eye className="w-3.5 h-3.5 text-[#0536d2]" />
                                <span>Audited Videos Telemetry (Median ER & Utility calculation):</span>
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
                                          <span>ตะกร้า</span>
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
                                      {vid.query_origin && (
                                        <>
                                          <span>•</span>
                                          <span className="text-indigo-700 bg-indigo-50 px-1.5 py-0.2 rounded font-sans text-[10px]">
                                            {vid.query_origin}
                                          </span>
                                        </>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>

                              {/* Real Comments if scraped */}
                              {item.kol.real_comments && item.kol.real_comments.length > 0 && (
                                <div className="pt-2 border-t border-slate-200">
                                  <h5 className="font-bold text-slate-900 text-xs mb-1.5 flex items-center space-x-1.5">
                                    <MessageSquare className="w-3.5 h-3.5 text-emerald-600" />
                                    <span>Tier-2 Scraped Comments (Buyer Intent Analysis):</span>
                                  </h5>
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {item.kol.real_comments.slice(0, 6).map((c, ci) => (
                                      <div key={ci} className="p-2 rounded-xl bg-white border border-slate-200 text-slate-700 text-[11px] italic">
                                        "{c}"
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

            {/* TAB: EXCLUDED CREATORS (Transparency on Gate 1 & 2 Filters) */}
            {activeTab === 'excluded' && matchResponse && (
              <div className="space-y-4">
                <div className="p-4 rounded-3xl bg-rose-50 border border-rose-200 text-rose-950 text-xs space-y-1.5">
                  <div className="flex items-center space-x-2 font-bold text-rose-800 text-sm">
                    <ShieldAlert className="w-4 h-4 text-rose-600" />
                    <span>Two-Stage Entity Exclusion Transparency</span>
                  </div>
                  <p className="leading-relaxed text-rose-900">
                    แสดงรายชื่อบัญชีที่ถูกตัดออกผ่าน <strong>Gate 1 (ร้านค้า/โรงงาน, Official Store, Smart Spam Bot)</strong> หรือ <strong>Gate 2 (ช่องข่าว/มีมตลก/คำพ้องรูปหลุดหมวด)</strong> เพื่อความโปร่งใสและปกป้องงบประมาณโฆษณา
                  </p>
                </div>

                {matchResponse.excluded_creators.map((c, i) => (
                  <div
                    key={i}
                    className="bg-white border border-rose-200 rounded-3xl p-5 shadow-xs space-y-2"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 font-bold text-[10px] uppercase font-mono">
                            {c.stage.replace('_', ' ')}
                          </span>
                          <h4 className="font-bold text-slate-900 text-base">{c.display_name}</h4>
                          <a
                            href={c.tiktok_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-[#0536d2] hover:underline font-mono"
                          >
                            @{c.handle}
                          </a>
                        </div>
                        <p className="text-xs text-slate-500 mt-1 line-clamp-1">{c.bio}</p>
                      </div>

                      <span className="text-xs text-slate-400 font-mono">
                        {c.follower_count.toLocaleString()} fans
                      </span>
                    </div>

                    <div className="p-3 rounded-2xl bg-rose-50/70 border border-rose-200 text-xs text-rose-900">
                      <strong>Exclusion Reason:</strong> {c.reason}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
