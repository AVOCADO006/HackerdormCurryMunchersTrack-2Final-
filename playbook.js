// ============================================================
// MARKETING PLAYBOOK (PRD Appendix section 16)
// Stored as structured data, used by agents at run time.
// ============================================================

export const PLAYBOOK = {
  contentPillars: [
    { name: 'Product Showcase', description: 'Show the product in use, highlight features and benefits' },
    { name: 'Behind the Scenes', description: 'Show the process, the kitchen, the team, the making' },
    { name: 'Customer Stories', description: 'Testimonials, UGC, before/after, event photos' },
    { name: 'Educational', description: 'Tips, how-to, ingredient spotlight, industry insights' },
    { name: 'Community & Culture', description: 'Local events, festive content, collaborations' },
  ],

  hookFormulas: [
    'Question hook: "Ever wondered why [problem]?"',
    'Contrast hook: "Most people think X, but actually Y"',
    'Number hook: "5 things nobody tells you about [topic]"',
    'Story hook: "Last week, something happened that changed everything..."',
    'Direct hook: "Stop scrolling if you [relatable situation]"',
    'Curiosity hook: "This one change doubled our orders..."',
    'Pain point hook: "Tired of [problem]? Here\'s how we solved it"',
  ],

  storyStructures: [
    { name: 'AIDA', stages: ['Attention (hook)', 'Interest (problem/solution)', 'Desire (benefits/proof)', 'Action (CTA)'] },
    { name: 'Before-After-Bridge', stages: ['Before (pain)', 'After (desired state)', 'Bridge (how to get there)'] },
    { name: 'Problem-Agitate-Solve', stages: ['Problem', 'Agitate (make it worse)', 'Solve (your solution)'] },
    { name: 'Hero\'s Journey (mini)', stages: ['Call to adventure', 'Challenge', 'Transformation', 'Return with gift'] },
  ],

  shortVideoStructure: {
    hook: '0-3 seconds: Grab attention with a visual or verbal hook',
    intro: '3-5 seconds: Establish context',
    body: '5-20 seconds: Deliver the core value (demo, story, tip)',
    climax: '20-25 seconds: Peak moment or payoff',
    cta: '25-30 seconds: Call to action (follow, order, save)',
  },

  weeklyCadence: {
    instagram: { postCount: '4-5 per week', types: ['reel', 'carousel', 'story'] },
    linkedin: { postCount: '3-4 per week', types: ['carousel', 'text', 'poll'] },
    x: { postCount: '5-7 per week', types: ['short_post', 'thread'] },
    threads: { postCount: '3-5 per week', types: ['conversational_post'] },
  },

  festiveCalendar: [
    { event: 'Chinese New Year', month: 'Jan-Feb', tips: 'Reunion dinner themes, prosperity menu, red/gold colors' },
    { event: 'Ramadan & Raya', month: 'Mar-Apr', tips: 'Buka puasa specials, Raya hampers, festive menu' },
    { event: 'Deepavali', month: 'Oct-Nov', tips: 'Festive sweets, colorful themes, celebration platters' },
    { event: '11.11 Sale', month: 'November', tips: 'Bulk order discounts, limited-time bundles' },
    { event: 'Payday Sales', month: 'Monthly', tips: 'End-of-month promotions targeting office workers' },
    { event: 'Christmas', month: 'December', tips: 'Party boxes, corporate gifts, festive platters' },
  ],

  linkedinFormats: {
    carousel: {
      structure: 'Slide 1: Hook/title | Slides 2-N: Key points (one per slide) | Last slide: CTA',
      tips: 'Use data, keep to 8-10 slides, clear visuals, one idea per slide',
    },
    founderStory: {
      structure: 'Personal narrative with lessons learned, tied to business value',
      tips: 'Authentic voice, vulnerable moments, professional insight',
    },
    researchPost: {
      structure: 'Stat/insight → context → what it means → takeaway for the reader',
      rules: 'Every statistic must have a source link. If no verified source, mark as placeholder.',
    },
    poll: {
      structure: 'Question → 2-4 options → caption explaining why you\'re asking',
      tips: 'Spark discussion, keep options clear and distinct',
    },
    outreachMessage: {
      structure: 'Personalized opening → value proposition → soft ask → easy yes',
      tips: 'Research the prospect, reference their company, keep under 150 words',
    },
  },

  b2bFunnel: [
    { stage: 'Awareness', goal: 'Reach and educate the target audience', assets: ['founder story', 'research post', 'educational carousel'] },
    { stage: 'Engagement', goal: 'Build interest and interaction', assets: ['poll', 'comment plan', 'thought leadership'] },
    { stage: 'Conversion', goal: 'Drive inquiries and orders', assets: ['offer post', 'case study', 'outreach message'] },
  ],

  metricsGlossary: {
    reach: 'Number of unique accounts that saw your post',
    impressions: 'Total number of times your post was seen',
    engagement_rate: '(Likes + Comments + Saves + Shares) / Reach × 100',
    click_through_rate: 'Clicks / Impressions × 100',
    conversion_rate: 'Orders or leads / Clicks × 100',
    revenue_per_post: 'Revenue from this post / 1',
    cost_per_order: 'Total costs / Orders from this period',
    roas: 'Revenue / Ad spend (if any)',
  },

  hashtagStrategy: {
    instagram: 'Use 8-15 hashtags: 3 broad, 5 niche, 3-7 branded/community',
    linkedin: 'Use 3-5 hashtags: 1-2 broad, 2-3 niche',
    x: 'Use 1-3 hashtags maximum',
    threads: 'Use 1-2 hashtags or none',
  },
};

// Get playbook section for an agent
export function getPlaybookForAgent(role) {
  const sections = {
    strategist: { contentPillars: PLAYBOOK.contentPillars, weeklyCadence: PLAYBOOK.weeklyCadence, b2bFunnel: PLAYBOOK.b2bFunnel },
    creator: { contentPillars: PLAYBOOK.contentPillars, hookFormulas: PLAYBOOK.hookFormulas, storyStructures: PLAYBOOK.storyStructures, hashtagStrategy: PLAYBOOK.hashtagStrategy, festiveCalendar: PLAYBOOK.festiveCalendar },
    designer: { linkedinFormats: PLAYBOOK.linkedinFormats, shortVideoStructure: PLAYBOOK.shortVideoStructure },
    reviewer: { linkedinFormats: PLAYBOOK.linkedinFormats, metricsGlossary: PLAYBOOK.metricsGlossary },
    reply_drafter: { metricsGlossary: PLAYBOOK.metricsGlossary },
    campaign_planner: { b2bFunnel: PLAYBOOK.b2bFunnel, linkedinFormats: PLAYBOOK.linkedinFormats, festiveCalendar: PLAYBOOK.festiveCalendar },
    finance_analyst: { metricsGlossary: PLAYBOOK.metricsGlossary },
  };
  return sections[role] || {};
}
