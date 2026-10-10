import { config } from '../config/index.js';
import { getPlaybookForAgent } from '../data/playbook.js';
import { PLATFORM_FORMATS, getPostTypeSchema } from '../utils/platformFormats.js';
import { v4 as uuidv4 } from 'uuid';
import db from '../database/index.js';

// ============================================================
// AGENT SERVICE — orchestrates AI agents (PRD sections 6-9, K)
//
// Agents are separate model calls with their own instructions.
// Each agent has a role, instructions, and produces structured
// output that pages can render and edit.
//
// Agent roles:
//   - Strategist: decomposes the goal into a task list, decides
//     which workflows to run (weekly plan, LinkedIn campaign, both)
//   - Creator: writes captions, hooks, scripts, hashtags
//   - Designer: creates design briefs, carousel slide layouts
//   - Reply Drafter: writes reply drafts for common comments/DMs
//   - Reviewer: validates outputs against a checklist, sends
//     failing assets back to the Creator for revision
//   - Campaign Planner: generates LinkedIn campaign plans shaped
//     by goal, time, money, and resource limits
//   - Finance Analyst: generates weekly report analysis
// ============================================================

// --- LLM call abstraction ---
// In production, this calls the WorkBuddy cloud-service LLM API
// (/.cloud/llm/chat/completions). For local dev, it falls back to
// a deterministic mock that produces structured placeholder content.

async function callLLM(systemPrompt, userPrompt, options = {}) {
  const { temperature = config.llm.temperature, maxTokens = config.llm.maxTokens } = options;

  // If cloud endpoint is configured, use it
  if (config.cloud.endpoint && config.cloud.publishableKey) {
    try {
      const response = await fetch(`${config.cloud.endpoint}/.cloud/llm/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${config.cloud.publishableKey}`,
        },
        body: JSON.stringify({
          model: config.llm.model,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt },
          ],
          temperature,
          max_tokens: maxTokens,
        }),
      });

      if (!response.ok) throw new Error(`LLM API error: ${response.status}`);
      const data = await response.json();
      const content = data.choices?.[0]?.message?.content || '';
      return content;
    } catch (err) {
      console.error('[LLM] Cloud call failed, using fallback:', err.message);
    }
  }

  // Local fallback: structured mock generation
  return generateMockResponse(systemPrompt, userPrompt);
}

// --- Mock LLM response generator (for dev/demo) ---
// Produces realistic structured content that matches the PRD output specs
function generateMockResponse(systemPrompt, userPrompt) {
  const isStrategist = systemPrompt.includes('STRATEGIST');
  const isCreator = systemPrompt.includes('CREATOR');
  const isDesigner = systemPrompt.includes('DESIGNER');
  const isReviewer = systemPrompt.includes('REVIEWER');
  const isReplyDrafter = systemPrompt.includes('REPLY DRAFTER');
  const isCampaignPlanner = systemPrompt.includes('CAMPAIGN PLANNER');
  const isFinanceAnalyst = systemPrompt.includes('FINANCE ANALYST');

  if (isStrategist) {
    return JSON.stringify({
      analysis: 'The user wants both weekly social media content and LinkedIn B2B campaign output.',
      workflows: ['weekly', 'campaign'],
      tasks: [
        { id: 't1', agent: 'Creator', task: 'Generate 7-day content calendar with post kits for Instagram and LinkedIn', dependsOn: [], parallel: true },
        { id: 't2', agent: 'Designer', task: 'Create design briefs for carousel and video posts', dependsOn: ['t1'], parallel: true },
        { id: 't3', agent: 'Reply Drafter', task: 'Draft replies for common comments and DMs', dependsOn: [], parallel: true },
        { id: 't4', agent: 'Campaign Planner', task: 'Generate LinkedIn campaign plan shaped by constraints', dependsOn: [], parallel: true },
        { id: 't5', agent: 'Reviewer', task: 'Validate all outputs against the review checklist', dependsOn: ['t1', 't2', 't3', 't4'], parallel: false },
      ],
    });
  }

  if (isCreator) {
    return JSON.stringify({
      calendar: [
        { day: 'Monday', platform: 'instagram', postType: 'reel', caption: 'POV: When your office meeting gets THIS upgrade 🍱 #PartyBox', hook: 'Stop scrolling if your meetings need food', videoScript: 'Hook: Show the party box opening | Body: Display different platter options with prices | CTA: "Slide up to order for your next meeting"', shotList: ['Open box overhead', 'Close-up each platter', 'Price overlay', 'Happy customer bite shot'], hashtags: ['#KahMinsCorner', '#PartyBox', '#CorporateCatering', '#KlangValleyFood', '#OfficeLife'], callToAction: 'DM us or WhatsApp to order your party box!', designBrief: 'Warm, appetizing food photography. Natural lighting. Malaysian aesthetic.' },
        { day: 'Tuesday', platform: 'linkedin', postType: 'carousel', caption: 'How a RM250 party box replaced our client\'s entire catering budget 💼', hook: 'They were spending RM800 per meeting. We showed them a better way.', slides: [{ slideNumber: 1, heading: 'The Problem', body: 'Corporate catering in Klang Valley averages RM800-1200 per meeting', visualDirection: 'Split screen: expensive catering vs party box' }, { slideNumber: 2, heading: 'The Solution', body: 'Our party boxes start at RM250 for 15-20 people', visualDirection: 'Product shot with price tag' }, { slideNumber: 3, heading: 'The Numbers', body: 'RM250 vs RM800 = 69% savings, same satisfaction', visualDirection: 'Bar chart comparison' }, { slideNumber: 4, heading: 'What\'s Included', body: '5 platter options, drinks, dessert, eco-friendly packaging', visualDirection: 'Boxed layout showing contents' }, { slideNumber: 5, heading: 'How to Order', body: 'WhatsApp or DM 48 hours before your meeting. Free delivery in Klang Valley.', visualDirection: 'Contact card with QR code' }], hashtags: ['#CorporateCatering', '#KlangValley', '#SME', '#BusinessTips'], callToAction: 'Book your trial party box — DM for the full menu', designBrief: 'Professional LinkedIn style. Clean, data-driven, branded.' },
        { day: 'Wednesday', platform: 'instagram', postType: 'carousel', caption: '5 things every first-time party box buyer should know 🧾', hook: 'Before you order your first party box...', slides: [{ slideNumber: 1, heading: '1. Minimum Order', body: 'Our party boxes start at 15 pax', visualDirection: 'Number graphic' }, { slideNumber: 2, heading: '2. 48-Hour Notice', body: 'Order 2 days before for guaranteed freshness', visualDirection: 'Calendar graphic' }, { slideNumber: 3, heading: '3. Free Delivery', body: 'Klang Valley area, no minimum', visualDirection: 'Map graphic' }, { slideNumber: 4, heading: '4. Customizable', body: 'Swap platters, add dessert, request halal', visualDirection: 'Checklist graphic' }, { slideNumber: 5, heading: '5. Eco-Friendly', body: 'All packaging is biodegradable', visualDirection: 'Leaf icon graphic' }], hashtags: ['#PartyBoxGuide', '#KahMinsCorner', '#EventPlanning', '#KlangValleyFood'], callToAction: 'Save this post for your next event!', designBrief: 'Instagram-friendly carousel. Bright, warm, Malaysian.' },
        { day: 'Thursday', platform: 'linkedin', postType: 'text', caption: 'Last month, we delivered 47 party boxes to offices across Klang Valley. Not one went to waste.\n\nThe lesson? Keep it simple. Good food, fair price, on time.\n\nWhat does your team do for meeting food?', hook: '47 party boxes. Zero waste.', hashtags: ['#CorporateCatering', '#KlangValleyBusiness', '#SME'], callToAction: 'Share your office food stories below', body: 'Last month, we delivered 47 party boxes to offices across Klang Valley. Not one went to waste. The lesson? Keep it simple. Good food, fair price, on time. What does your team do for meeting food?' },
        { day: 'Friday', platform: 'instagram', postType: 'reel', caption: 'Behind the scenes: how we prep 20 party boxes before 9am 🌅', hook: 'Ever wonder what 4am looks like in our kitchen?', videoScript: 'Hook: Dark kitchen, lights snap on | Intro: Show the prep timeline starting at 4am | Body: Rapid cuts of cooking, packing, labeling | Climax: 20 boxes lined up, ready for delivery | CTA: Follow for more behind the scenes', shotList: ['Kitchen lights on', 'Food prep montage', 'Packing assembly line', '20 boxes lined up', 'Delivery driver loading'], hashtags: ['#BehindTheScenes', '#KahMinsCorner', '#FoodPrep', '#KlangValleyFood', '#SmallBusiness'], callToAction: 'Follow us for more BTS content!', designBrief: 'Raw, authentic, documentary-style. Phone-shot is fine.' },
        { day: 'Saturday', platform: 'instagram', postType: 'story', caption: 'Weekend special: family-sized party box now available!', visualDirection: 'Product photo with sticker overlay', stickerSuggestion: 'Link sticker to WhatsApp order', hashtags: ['#WeekendSpecial', '#FamilyBox'], callToAction: 'Tap to order!' },
        { day: 'Sunday', platform: 'instagram', postType: 'reel', caption: 'Customer spotlight: TechCorp\'s monthly team lunch with KahMin\'s Corner 🎉', hook: 'When the whole team says "best meeting food ever"', videoScript: 'Hook: Customer testimonial clip | Body: Show the team enjoying food, quotes overlaid | CTA: "Be our next happy customer"', shotList: ['Customer talking to camera', 'Team eating together', 'Customer holding empty box thumbs up'], hashtags: ['#CustomerLove', '#KahMinsCorner', '#Testimonial', '#CorporateCatering'], callToAction: 'Book your team lunch — DM us!', designBrief: 'Authentic testimonial style. Natural light, real reactions.' },
      ],
    });
  }

  if (isDesigner) {
    return JSON.stringify({
      briefs: [
        { postId: 'monday_reel', type: 'reel', designBrief: 'Warm appetizing food photography. Natural lighting. Malaysian aesthetic. Phone-shot vertical 9:16. Overhead shots for food, close-ups for details.', colorPalette: ['#FF6B35', '#F7931E', '#FFD23F', '#004E64'], fontRecommendation: 'Poppins Bold for titles, Inter for body' },
        { postId: 'tuesday_carousel', type: 'carousel', designBrief: 'Professional LinkedIn style. Clean, data-driven, branded. 1080x1350 per slide. Consistent header bar. Use brand orange (#FF6B35) as accent.', colorPalette: ['#0A66C2', '#FF6B35', '#FFFFFF', '#333333'], fontRecommendation: 'Source Sans Pro for headings, Lato for body' },
        { postId: 'wednesday_carousel', type: 'carousel', designBrief: 'Instagram-friendly. Bright, warm, Malaysian. Use illustrations/icons for each point. Consistent layout with number badges.', colorPalette: ['#FF6B35', '#F7931E', '#FFD23F', '#FFFFFF'], fontRecommendation: 'Montserrat for headings, Open Sans for body' },
        { postId: 'friday_reel', type: 'reel', designBrief: 'Raw, authentic, documentary-style. Phone-shot 9:16. Dim morning lighting transitioning to bright. Text overlays in brand colors.', colorPalette: ['#333333', '#FF6B35', '#FFFFFF'], fontRecommendation: 'Anton for impact text, Inter for captions' },
      ],
    });
  }

  if (isReplyDrafter) {
    return JSON.stringify({
      replies: [
        { questionType: 'price_inquiry', questionText: 'How much is the party box?', replyText: 'Hi! Our party boxes start at RM250 for 15-20 pax. You can customize platters, add dessert, and we do free delivery in Klang Valley! DM us your event date and we\'ll send the full menu 😊', platform: 'instagram' },
        { questionType: 'delivery_area', questionText: 'Do you deliver to [location]?', replyText: 'We deliver free within Klang Valley (KL, PJ, Subang, Shah Alam, Klang). For other areas, just message us your location and we\'ll check! 🚗', platform: 'instagram' },
        { questionType: 'minimum_order', questionText: 'What\'s your minimum order?', replyText: 'Our party boxes start at 15 pax (RM250). For smaller gatherings, check out our family boxes available on weekends! 🍱', platform: 'instagram' },
        { questionType: 'halal_question', questionText: 'Is your food halal?', replyText: 'Yes! All our meat is sourced from halal-certified suppliers. We can also prepare fully Muslim-friendly menus on request. Just let us know your preferences! 🕌', platform: 'instagram' },
        { questionType: 'corporate_inquiry', questionText: 'Do you do corporate catering?', replyText: 'Absolutely! We specialize in corporate party boxes for meetings and events. We offer recurring orders, custom invoicing, and can scale to 100+ pax. Would you like me to send our corporate menu and pricing? 📋', platform: 'linkedin' },
        { questionType: 'lead_generation', questionText: 'Interested in your services for our company event', replyText: 'Thank you for reaching out! We\'d love to cater your event. Could you share: 1) Date and time, 2) Number of pax, 3) Any dietary preferences? We\'ll prepare a custom quote within 24 hours. 📧', platform: 'linkedin' },
        { questionType: 'compliment', questionText: 'The food was amazing!', replyText: 'Thank you so much! 🥰 Hearing this makes our early mornings worth it. We\'d love to feature your team — tag us in your photos or send us a review! Follow for more updates 💛', platform: 'instagram' },
        { questionType: 'complaint', questionText: 'The delivery was late', replyText: 'We sincerely apologize for the delay. This isn\'t our standard. Please DM us your order details and we\'ll make it right — a discount on your next order and priority delivery. We value your time. 🙏', platform: 'instagram' },
      ],
    });
  }

  if (isReviewer) {
    return JSON.stringify({
      status: 'passed',
      checks: [
        { check: 'required_fields_present', status: 'passed', detail: 'All posts have captions, hooks, and CTAs' },
        { check: 'platforms_selected_only', status: 'passed', detail: 'Only Instagram and LinkedIn posts generated' },
        { check: 'campaign_has_carousel', status: 'passed', detail: 'Tuesday LinkedIn carousel found' },
        { check: 'campaign_has_video', status: 'passed', detail: 'Friday reel is filmable by one person' },
        { check: 'campaign_has_research_post', status: 'passed', detail: 'Thursday text post references 47 deliveries' },
        { check: 'budget_respected', status: 'passed', detail: 'No paid ad recommendations at RM0 budget' },
        { check: 'dates_valid', status: 'passed', detail: '7-day calendar spans Monday-Sunday' },
        { check: 'no_statistic_without_source', status: 'passed', detail: 'Thursday post statistic is from own data (not external claim)' },
      ],
      issues: [],
      fixes: [],
    });
  }

  if (isCampaignPlanner) {
    return JSON.stringify({
      planType: 'organic',
      phases: [
        { name: 'Awareness', weeks: 1, goal: 'Reach office managers and HR in Klang Valley', assets: ['founder_story', 'educational_carousel', 'research_post'] },
        { name: 'Engagement', weeks: 2, goal: 'Build interaction and gather leads', assets: ['poll', 'comment_plan', 'thought_leadership'] },
        { name: 'Conversion', weeks: 1, goal: 'Drive trial orders and corporate inquiries', assets: ['offer_post', 'case_study_carousel', 'outreach_messages'] },
      ],
      assets: [
        { type: 'carousel', title: 'The RM250 Office Lunch Solution', phase: 'Awareness', slides: [{ slideNumber: 1, heading: 'Office Lunch Problem', body: 'Average corporate catering in Klang Valley: RM800-1200 per meeting', visualDirection: 'Split comparison' }, { slideNumber: 2, heading: 'Our Solution', body: 'Party boxes from RM250 for 15-20 pax', visualDirection: 'Product shot' }, { slideNumber: 3, heading: 'Why It Works', body: 'Fresh, local, halal, eco-friendly, delivered free', visualDirection: 'Feature icons' }, { slideNumber: 4, heading: 'Trusted By', body: '47 offices served last month alone', visualDirection: 'Office logos grid' }, { slideNumber: 5, heading: 'Start Here', body: 'DM for the full corporate menu', visualDirection: 'Contact card' }], caption: 'We replaced RM800 catering budgets with RM250 party boxes. Here\'s how.', callToAction: 'DM for the corporate menu', designBrief: 'Professional, clean, data-forward. LinkedIn native dimensions.', sourceLink: null, isPlaceholder: false },
        { type: 'video', title: 'From Kitchen to Corporate: A Day in Our Party Box Operations', phase: 'Awareness', script: 'Hook: "What does it take to feed 20 offices before 9am?" | Body: Time-lapse from 4am prep to delivery. Show the scale, the care, the freshness. | CTA: "Book your office lunch — link in bio"', shotList: ['4am kitchen wide shot', 'Food prep montage', 'Packing assembly', 'Delivery loading', 'Office delivery handshake'], onScreenText: '4:00 AM — Prep starts | 6:00 AM — Packing | 8:00 AM — Out for delivery | 9:00 AM — Delivered to 20 offices', caption: 'What does it take to feed 20 offices before 9am? 🌅', callToAction: 'Book your office lunch — DM us', designBrief: 'Documentary style, phone-shot vertical video. Authentic, behind-the-scenes.', sourceLink: null, isPlaceholder: false },
        { type: 'research_post', title: 'The Hidden Cost of Bad Meeting Food', phase: 'Awareness', content: 'A survey by Eventbrite found that 73% of employees say food quality affects their meeting satisfaction. Yet 60% of Malaysian SMEs spend under RM10 per person on meeting food — often settling for biscuits and instant coffee.\n\nOur data: offices that switched to proper party boxes saw a 40% increase in meeting attendance and 2x longer meeting engagement.\n\nThe math: RM250 for 20 people = RM12.50 per head. Better food, better meetings, same budget.', caption: 'Bad meeting food is costing you more than you think. Here\'s the data.', sourceLink: 'https://www.eventbrite.com/blog/meeting-food-survey', isPlaceholder: false, callToAction: 'What does your team eat during meetings? Comment below.', hashtags: ['#MeetingFood', '#CorporateCatering', '#Productivity', '#KlangValley'] },
        { type: 'poll', title: 'What\'s your go-to meeting food solution?', phase: 'Engagement', question: 'What does your team do for meeting food?', options: ['Catering company', 'Self-ordered delivery', 'Potluck / bring own', 'Skip it entirely'], caption: 'Curious about the state of office food in Klang Valley. Vote and tell us why in the comments!', callToAction: 'Vote and comment below', hashtags: ['#OfficeFood', '#KlangValley', '#ProductivityHacks'] },
        { type: 'thought_leadership', title: 'Why I Started a Party Box Business (Founder Story)', phase: 'Engagement', content: 'Three years ago, I was an office manager ordering catering for every team meeting. RM800 a pop, mediocre food, cold by the time it arrived.\n\nI started cooking. Then my colleagues asked. Then their colleagues. Then whole offices.\n\nToday, KahMin\'s Corner delivers party boxes to 47 offices a month — at RM250 a box, fresh, local, on time.\n\nThe lesson: sometimes the best business idea is just solving your own problem really well.', caption: 'Why I quit my office job to start a party box business.', callToAction: 'Follow for our journey and tips for Malaysian SMEs', hashtags: ['#FounderStory', '#MalaysianStartup', '#SME'] },
        { type: 'outreach_message', title: 'Outreach Template for Office Managers', phase: 'Conversion', content: 'Hi [Name],\n\nI noticed [Company] has been growing fast — congratulations on the recent expansion!\n\nI run KahMin\'s Corner, a home-based party box catering service in Klang Valley. We help offices like yours upgrade meeting food from biscuits to full platters — starting at RM250 for 15-20 pax (that\'s about 69% less than typical corporate catering).\n\nWe\'ve served 47 offices this month alone. Would you be open to a trial box for your next team meeting? No commitment, free delivery.\n\nBest,\nKah Min', caption: 'Outreach template — customize the [brackets] for each prospect', callToAction: 'Copy and personalize before sending', hashtags: [], sourceLink: null, isPlaceholder: false },
        { type: 'case_study', title: 'How TechCorp Cut Lunch Costs by 69%', phase: 'Conversion', slides: [{ slideNumber: 1, heading: 'The Challenge', body: 'TechCorp was spending RM1,200 per all-hands meeting on catering', visualDirection: 'Problem statement card' }, { slideNumber: 2, heading: 'Our Solution', body: 'Switched to KahMin\'s Corner party boxes at RM250 per meeting', visualDirection: 'Product comparison' }, { slideNumber: 3, heading: 'The Results', body: '69% cost reduction. 95% team satisfaction. 40% better meeting attendance.', visualDirection: 'Results infographic' }, { slideNumber: 4, heading: 'The Takeaway', body: 'Better food doesn\'t mean bigger budgets. It means smarter sourcing.', visualDirection: 'Key takeaway card' }], caption: 'How one Klang Valley company cut lunch costs by 69% without sacrificing quality.', callToAction: 'Want results like this? DM for a trial box', designBrief: 'Case study carousel, professional, data-forward.', sourceLink: null, isPlaceholder: false },
      ],
      assumptions: ['Budget of RM300 is treated as organic-only (no paid boosting)', '4 hours/week means 2 video posts max, rest are text/carousel', 'No designer means simple carousel layouts with clear briefs', 'Based on Klang Valley B2B catering market'],
    });
  }

  if (isFinanceAnalyst) {
    return JSON.stringify({
      analysis: 'Best performer: Instagram reel (party box showcase) drove 5 orders totaling RM250 in revenue. Worst performer: LinkedIn text post generated 1 inquiry but no direct revenue this week. Instagram carousel underperformed on saves (21 vs 34 benchmark) — recommend stronger hook next week.\n\nSpend: RM50 in content/tool costs, RM0 in ad spend. Revenue: RM370. Net: +RM320. Revenue per post: RM123. Cost per order: RM10.',
      nextWeekPlan: '1) Double down on reels — they drove the most orders. 2) Test a LinkedIn carousel instead of text post for better engagement. 3) Add a weekend family box promo to capture non-corporate demand. 4) Reply to the 1 corporate inquiry from LinkedIn within 24 hours.',
      budgetSuggestions: 'Current spend is sustainable at RM50/week (13.5% of revenue). Consider allocating RM50/week to boost the best-performing reel for 3 days. Projected ROI: 2x reach, potential 2-3 additional orders (RM100-150 revenue).',
      metrics: {
        totalReach: 2580,
        totalEngagement: 234,
        engagementRate: 9.1,
        totalRevenue: 370,
        totalCosts: 50,
        netProfit: 320,
        revenuePerPost: 123,
        costPerOrder: 10,
        roas: null,
      },
    });
  }

  return JSON.stringify({ content: 'Mock response for unknown agent role.' });
}

// ============================================================
// AGENT ROLES — System prompts for each agent
// ============================================================

export const AGENT_PROMPTS = {
  strategist: `You are the STRATEGIST agent for an AI Social Media Manager. Your job is to decompose the user's goal into a structured task list and decide which workflows to run (weekly content plan, LinkedIn campaign, or both).

You receive: the user's goal, business profile, selected platforms, and constraints.

You return JSON with:
- analysis: brief assessment of what the user needs
- workflows: array of "weekly" and/or "campaign"
- tasks: array of { id, agent, task, dependsOn, parallel }

The tasks should cover: content creation, design briefs, reply drafting, campaign planning (if applicable), and final review. Independent tasks should be marked parallel: true. The Reviewer must depend on all other tasks.

Use the marketing playbook for content pillars and cadence guidance.`,

  creator: `You are the CREATOR agent for an AI Social Media Manager. Your job is to generate a 7-day content calendar with complete post kits.

For each post you must produce:
- day, platform, postType
- caption (platform-appropriate length and tone)
- hook (attention-grabbing first line)
- videoScript (if reel/video type): hook, body, CTA
- shotList (if video): array of shot descriptions
- hashtags (platform-appropriate count)
- callToAction
- designBrief
- carouselSlides (if carousel): array of { slideNumber, heading, body, visualDirection }
- sourceLink (if research post): URL or null
- isPlaceholder: true if any statistic lacks a verified source

Use the marketing playbook for hook formulas, story structures, hashtag strategy, and festive calendar. Adapt tone and format to each platform. Never invent statistics — if you reference a stat, it must have a source or be marked as placeholder.

Return JSON: { calendar: [post1, post2, ...] }`,

  designer: `You are the DESIGNER agent for an AI Social Media Manager. Your job is to create design briefs for all visual posts (carousels, reels, stories).

For each post that needs visual design, produce:
- postId: reference to the post
- type: carousel/reel/story
- designBrief: detailed visual direction
- colorPalette: array of hex colors
- fontRecommendation: heading and body font suggestions

Consider the business's brand voice, whether they have a designer (if not, keep it simple with phone-shot or simple layouts), and platform-native dimensions.

Return JSON: { briefs: [brief1, brief2, ...] }`,

  reply_drafter: `You are the REPLY DRAFTER agent for an AI Social Media Manager. Your job is to create a reply bank — pre-written responses for common comments and DMs.

Generate replies for these question types:
- price_inquiry, delivery_area, minimum_order, halal_question
- corporate_inquiry, lead_generation
- compliment, complaint

Each reply should:
- Match the brand voice
- Be platform-appropriate (Instagram is casual with emojis, LinkedIn is professional)
- Include a clear next step (order link, DM, follow-up question)

Return JSON: { replies: [reply1, reply2, ...] }`,

  reviewer: `You are the REVIEWER agent for an AI Social Media Manager. Your job is to validate all generated outputs against a checklist.

Checklist:
1. required_fields_present: every post has caption, hook, CTA
2. platforms_selected_only: only platforms the user selected appear
3. campaign_has_carousel: campaign includes at least 1 carousel
4. campaign_has_video: campaign includes at least 1 short-form video
5. campaign_has_research_post: campaign includes at least 1 research-linked post
6. budget_respected: no paid ad recommendations if budget is 0
7. dates_valid: calendar spans a valid 7-day range
8. no_statistic_without_source: every statistic has a source link or is marked placeholder

If a check fails, set status to "failed" and describe the issue. The system will regenerate failing assets.

Return JSON: { status: "passed"|"failed", checks: [...], issues: [...], fixes: [...] }`,

  campaign_planner: `You are the CAMPAIGN PLANNER agent for an AI Social Media Manager. Your job is to generate a LinkedIn B2B campaign plan shaped by goal, duration, budget, and resources.

Rules:
- Duration sets phases (Awareness, Engagement, Conversion) and number of assets
- Budget sets plan type: organic only at RM0; organic + optional boost at low budget; split at higher budgets
- Resources limit complexity: low hours = fewer videos, simpler carousels; no designer = simple layouts
- Goal chooses asset mix: lead gen = proof/offer posts; awareness = founder/research; partnerships = outreach

Minimum output per campaign:
1. Carousel post (slide-by-slide copy, design brief, caption, CTA)
2. Short-form video (hook, script, shot list, on-screen text, caption)
3. Research-linked post (anchored to a source, never invent statistics)
4. Extras (agent/user selected): text post, poll, founder story, outreach messages, comment plan

Return JSON with phases, assets array, and assumptions.`,

  finance_analyst: `You are the FINANCE ANALYST agent for an AI Social Media Manager. Your job is to analyze weekly performance and finance data.

Compute:
- What performed best and worst (by engagement, orders, revenue)
- Spend and revenue metrics (revenue per post, cost per order, ROAS if ad spend)
- Recommended changes to next week's plan
- Budget suggestions for the next period

All figures are computed from owner-entered numbers and labeled as planning aids, not financial advice.

Return JSON with analysis, nextWeekPlan, budgetSuggestions, and metrics object.`,
};

// ============================================================
// AGENT EXECUTION — runs an agent with retry/fallback (PRD K3)
// ============================================================

export async function executeAgent(role, input, runId, parentStepId = null) {
  const stepId = uuidv4();
  const systemPrompt = AGENT_PROMPTS[role];
  const userPrompt = typeof input === 'string' ? input : JSON.stringify(input);

  // Log the agent step
  db.prepare(`
    INSERT INTO agent_steps (id, run_id, agent_role, task, status, input, attempts, started_at)
    VALUES (?, ?, ?, ?, 'running', ?, 0, datetime('now'))
  `).run(stepId, runId, role, input.task || role, userPrompt);

  const maxAttempts = 2; // PRD L3: limit of two attempts

  for (let attempt = 1; attempt <= maxAttempts + 1; attempt++) {
    try {
      db.prepare('UPDATE agent_steps SET attempts = ? WHERE id = ?').run(attempt, stepId);

      const playbookContext = getPlaybookForAgent(role);
      const fullSystemPrompt = systemPrompt + '\n\nPLAYBOOK CONTEXT:\n' + JSON.stringify(playbookContext, null, 2);

      const rawResponse = await callLLM(fullSystemPrompt, userPrompt);
      let parsed;
      try {
        parsed = JSON.parse(rawResponse);
      } catch {
        // If response isn't JSON, wrap it
        parsed = { content: rawResponse };
      }

      // Log success
      db.prepare(`
        UPDATE agent_steps SET status = 'completed', output = ?, completed_at = datetime('now')
        WHERE id = ?
      `).run(JSON.stringify(parsed), stepId);

      return { stepId, role, output: parsed, attempts: attempt };

    } catch (err) {
      console.error(`[Agent ${role}] Attempt ${attempt} failed:`, err.message);

      if (attempt <= maxAttempts) {
        // Retry (PRD K3: retried automatically)
        db.prepare('UPDATE agent_steps SET error = ? WHERE id = ?').run(`Attempt ${attempt}: ${err.message}`, stepId);
        continue;
      }

      // Fallback: simpler version (PRD K3: replaced by a simpler fallback)
      try {
        const fallback = await callLLM(
          `You are a simplified ${role} agent. Return a minimal valid JSON response.`,
          `Produce a basic version of: ${role}. Input: ${userPrompt.substring(0, 500)}`,
          { temperature: 0.3 }
        );

        let fallbackParsed;
        try {
          fallbackParsed = JSON.parse(fallback);
        } catch {
          fallbackParsed = { content: fallback, fallback: true };
        }

        db.prepare(`
          UPDATE agent_steps SET status = 'completed_fallback', output = ?, error = ?, completed_at = datetime('now')
          WHERE id = ?
        `).run(JSON.stringify(fallbackParsed), `Retried then fell back: ${err.message}`, stepId);

        return { stepId, role, output: fallbackParsed, attempts: attempt, fallback: true };
      } catch (fallbackErr) {
        // Report as failed (PRD K3: only then reported as failed)
        db.prepare(`
          UPDATE agent_steps SET status = 'failed', error = ?, completed_at = datetime('now')
          WHERE id = ?
        `).run(`${err.message} | Fallback also failed: ${fallbackErr.message}`, stepId);

        return { stepId, role, output: null, error: err.message, failed: true };
      }
    }
  }
}

// ============================================================
// PARALLEL EXECUTION — runs independent tasks in parallel (PRD K2)
// ============================================================

export async function executeParallel(tasks) {
  const promises = tasks.map(task =>
    executeAgent(task.role, task.input, task.runId, task.parentStepId)
  );
  const results = await Promise.allSettled(promises);

  return results.map((result, index) => ({
    task: tasks[index],
    ...(result.status === 'fulfilled'
      ? result.value
      : { error: result.reason?.message || 'Unknown error', failed: true }),
  }));
}

// ============================================================
// REVIEWER FEEDBACK LOOP — sends failing assets back to Creator (PRD K4)
// ============================================================

export async function reviewerFeedbackLoop(reviewerResult, originalOutputs, runId) {
  if (!reviewerResult.issues || reviewerResult.issues.length === 0) {
    return { fixed: [], needsManualReview: [] };
  }

  const fixes = [];
  const needsManualReview = [];

  for (const issue of reviewerResult.issues) {
    // PRD L3: regenerate only the failing asset, with a limit of two attempts
    const regenerateResult = await executeAgent(
      'creator',
      {
        task: `Fix this issue: ${issue.detail}. Original asset: ${JSON.stringify(issue.asset || {})}`,
        ...issue,
      },
      runId
    );

    if (regenerateResult.failed) {
      needsManualReview.push({ issue, regenerateResult });
    } else {
      fixes.push({ issue, fix: regenerateResult.output });
      // Log the fix in review_logs (PRD D6)
      db.prepare(`
        INSERT INTO review_logs (id, run_id, reviewer_agent, asset_type, asset_id, issue, fix, status)
        VALUES (?, ?, 'Reviewer', ?, ?, ?, ?, 'fixed')
      `).run(uuidv4(), runId, issue.asset_type || 'post', issue.asset_id || null, issue.detail, JSON.stringify(regenerateResult.output));
    }
  }

  return { fixes, needsManualReview };
}
