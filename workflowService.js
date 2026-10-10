import { v4 as uuidv4 } from 'uuid';
import db from '../database/index.js';
import { executeAgent, executeParallel, reviewerFeedbackLoop } from './agentService.js';
import { incrementRunCount } from '../middleware/rateLimit.js';

// ============================================================
// WORKFLOW SERVICE — orchestrates the weekly content workflow
//
// Flow (PRD section 6, 7):
// 1. User enters one prompt (goal)
// 2. Strategist decomposes goal into task list
// 3. Independent tasks run in parallel (Creator, Designer, Reply Drafter)
// 4. Reviewer validates all outputs
// 5. Failing assets are sent back to Creator for revision
// 6. Deliverables: 7-day calendar, post kits, reply bank, review report
// ============================================================

export async function runWeeklyWorkflow(accountId, goal, profile, constraints = {}) {
  // Create the workflow run record
  const runId = uuidv4();
  db.prepare(`
    INSERT INTO workflow_runs (id, account_id, goal, constraints, status, workflow_type, started_at)
    VALUES (?, ?, ?, ?, 'running', 'weekly', datetime('now'))
  `).run(runId, accountId, goal, JSON.stringify(constraints));

  // Increment run count
  incrementRunCount(accountId);

  const runTrace = [];

  try {
    // --- Step 1: Strategist decomposes the goal ---
    runTrace.push({ step: 1, agent: 'Strategist', status: 'started', timestamp: new Date().toISOString() });
    const strategistResult = await executeAgent('strategist', {
      goal,
      profile,
      constraints,
      task: 'Decompose the goal into a task list and decide which workflows to run',
    }, runId);

    runTrace.push({ step: 1, agent: 'Strategist', status: 'completed', output: strategistResult.output });

    const taskPlan = strategistResult.output;
    const tasks = taskPlan.tasks || [];
    const workflows = taskPlan.workflows || ['weekly'];

    // --- Step 2: Run parallel tasks ---
    // Identify independent tasks (no dependencies)
    const independentTasks = tasks.filter(t => t.parallel && (!t.dependsOn || t.dependsOn.length === 0));
    const dependentTasks = tasks.filter(t => !t.parallel || (t.dependsOn && t.dependsOn.length > 0));

    runTrace.push({ step: 2, agent: 'Parallel', status: 'started', tasks: independentTasks.map(t => `${t.agent}: ${t.task}`) });

    const parallelResults = await executeParallel(
      independentTasks.map(t => ({ role: mapAgentRole(t.agent), input: { ...t, profile, goal, constraints }, runId }))
    );

    runTrace.push({ step: 2, agent: 'Parallel', status: 'completed', results: parallelResults });

    // Collect outputs
    let calendar = null;
    let briefs = null;
    let replies = null;
    let campaignPlan = null;

    for (const result of parallelResults) {
      if (result.task.agent === 'Creator' || result.role === 'creator') {
        calendar = result.output?.calendar || null;
      } else if (result.task.agent === 'Designer' || result.role === 'designer') {
        briefs = result.output?.briefs || null;
      } else if (result.task.agent === 'Reply Drafter' || result.role === 'reply_drafter') {
        replies = result.output?.replies || null;
      } else if (result.task.agent === 'Campaign Planner' || result.role === 'campaign_planner') {
        campaignPlan = result.output || null;
      }
    }

    // --- Step 3: Reviewer validates ---
    const reviewTask = tasks.find(t => t.agent === 'Reviewer') || { agent: 'Reviewer' };
    runTrace.push({ step: 3, agent: 'Reviewer', status: 'started' });

    const reviewInput = {
      task: 'Validate all outputs against the checklist',
      calendar,
      briefs,
      replies,
      campaignPlan,
      profile,
      constraints,
    };

    const reviewResult = await executeAgent('reviewer', reviewInput, runId);
    runTrace.push({ step: 3, agent: 'Reviewer', status: 'completed', output: reviewResult.output });

    // --- Step 4: Handle failing assets (PRD K4, L3) ---
    if (reviewResult.output?.issues && reviewResult.output.issues.length > 0) {
      runTrace.push({ step: 4, agent: 'Reviewer→Creator', status: 'feedback_loop_started', issues: reviewResult.output.issues.length });
      const feedbackResult = await reviewerFeedbackLoop(reviewResult.output, { calendar, briefs, replies }, runId);
      runTrace.push({ step: 4, agent: 'Reviewer→Creator', status: 'completed', fixes: feedbackResult.fixes.length, needsManualReview: feedbackResult.needsManualReview.length });
    }

    // --- Step 5: Persist deliverables ---

    // Save content plan + posts
    let contentPlanId = null;
    if (calendar) {
      contentPlanId = uuidv4();
      const today = new Date();
      const weekEnd = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
      db.prepare(`
        INSERT INTO content_plans (id, run_id, account_id, week_start, week_end, platforms)
        VALUES (?, ?, ?, ?, ?, ?)
      `).run(
        contentPlanId, runId, accountId,
        today.toISOString().split('T')[0],
        weekEnd.toISOString().split('T')[0],
        JSON.stringify(profile.platforms || [])
      );

      // Save each post
      const insertPost = db.prepare(`
        INSERT INTO posts (
          id, content_plan_id, account_id, day_of_week, date, platform, post_type,
          caption, hook, video_script, shot_list, hashtags, design_brief,
          carousel_slides, on_screen_text, call_to_action, status, versions,
          source_link, is_placeholder
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', '[]', ?, ?)
      `);

      for (const post of calendar) {
        insertPost.run(
          uuidv4(), contentPlanId, accountId,
          post.day, post.date || null, post.platform, post.postType,
          post.caption || null, post.hook || null, post.videoScript || null,
          JSON.stringify(post.shotList || []), JSON.stringify(post.hashtags || []),
          post.designBrief || null, JSON.stringify(post.slides || post.carouselSlides || []),
          post.onScreenText || null, post.callToAction || null,
          post.sourceLink || null, post.isPlaceholder ? 1 : 0
        );
      }
    }

    // Save reply drafts
    if (replies) {
      const insertReply = db.prepare(`
        INSERT INTO reply_drafts (id, run_id, account_id, question_type, question_text, reply_text, platform)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `);
      for (const reply of replies) {
        insertReply.run(uuidv4(), runId, accountId, reply.questionType, reply.questionText, reply.replyText, reply.platform || null);
      }
    }

    // Save campaign if generated
    if (campaignPlan && workflows.includes('campaign')) {
      const campaignId = uuidv4();
      db.prepare(`
        INSERT INTO campaigns (
          id, run_id, account_id, business_goal, phases, plan_type, status, target_audience, offer, tone
        ) VALUES (?, ?, ?, ?, ?, ?, 'ready', ?, ?, ?)
      `).run(
        campaignId, runId, accountId, goal,
        JSON.stringify(campaignPlan.phases || []),
        campaignPlan.planType || 'organic',
        profile.targetAudience || null,
        campaignPlan.assumptions ? JSON.stringify(campaignPlan.assumptions) : null,
        profile.brandVoice || null
      );

      if (campaignPlan.assets) {
        const insertAsset = db.prepare(`
          INSERT INTO campaign_assets (
            id, campaign_id, account_id, asset_type, title, content, slides, script,
            shot_list, on_screen_text, caption, call_to_action, design_brief,
            source_link, is_placeholder, phase, status, versions
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', '[]')
        `);
        for (const asset of campaignPlan.assets) {
          insertAsset.run(
            uuidv4(), campaignId, accountId, asset.type,
            asset.title || null, asset.content || null,
            JSON.stringify(asset.slides || []),
            asset.script || null, JSON.stringify(asset.shotList || []),
            asset.onScreenText || null, asset.caption || null,
            asset.callToAction || null, asset.designBrief || null,
            asset.sourceLink || null, asset.isPlaceholder ? 1 : 0,
            asset.phase || null
          );
        }
      }
    }

    // --- Step 6: Mark complete ---
    const resultSummary = {
      contentPlanId,
      postCount: calendar ? calendar.length : 0,
      replyCount: replies ? replies.length : 0,
      reviewStatus: reviewResult.output?.status || 'unknown',
      issuesFound: reviewResult.output?.issues?.length || 0,
      fixesApplied: reviewResult.output?.fixes?.length || 0,
      campaignGenerated: !!campaignPlan,
    };

    db.prepare(`
      UPDATE workflow_runs SET status = 'completed', result_summary = ?, completed_at = datetime('now')
      WHERE id = ?
    `).run(JSON.stringify(resultSummary), runId);

    runTrace.push({ step: 6, agent: 'System', status: 'completed', summary: resultSummary });

    // Update the run's agent_steps with the full trace
    db.prepare('UPDATE workflow_runs SET agent_steps = ? WHERE id = ?').run(JSON.stringify(runTrace), runId);

    return {
      runId,
      status: 'completed',
      summary: resultSummary,
      trace: runTrace,
      contentPlanId,
    };

  } catch (err) {
    console.error('[Workflow] Failed:', err);
    db.prepare('UPDATE workflow_runs SET status = ?, completed_at = datetime(\'now\') WHERE id = ?')
      .run('failed', runId);
    db.prepare('UPDATE workflow_runs SET agent_steps = ? WHERE id = ?').run(JSON.stringify(runTrace), runId);
    throw err;
  }
}

// Map PRD agent names to internal role names
function mapAgentRole(name) {
  const map = {
    'Strategist': 'strategist',
    'Creator': 'creator',
    'Designer': 'designer',
    'Reply Drafter': 'reply_drafter',
    'Reviewer': 'reviewer',
    'Campaign Planner': 'campaign_planner',
    'Finance Analyst': 'finance_analyst',
  };
  return map[name] || name.toLowerCase().replace(/\s+/g, '_');
}

// Get workflow run details
export function getWorkflowRun(runId, accountId) {
  const run = db.prepare('SELECT * FROM workflow_runs WHERE id = ? AND account_id = ?').get(runId, accountId);
  if (!run) return null;

  const steps = db.prepare('SELECT * FROM agent_steps WHERE run_id = ? ORDER BY created_at').all(runId);
  const contentPlan = db.prepare('SELECT * FROM content_plans WHERE run_id = ?').get(runId);
  const posts = contentPlan
    ? db.prepare('SELECT * FROM posts WHERE content_plan_id = ? ORDER BY created_at').all(contentPlan.id)
    : [];
  const replies = db.prepare('SELECT * FROM reply_drafts WHERE run_id = ?').all(runId);
  const reviewLogs = db.prepare('SELECT * FROM review_logs WHERE run_id = ?').all(runId);
  const campaigns = db.prepare('SELECT * FROM campaigns WHERE run_id = ?').all(runId);

  return {
    run: parseRun(run),
    steps: steps.map(parseStep),
    contentPlan: contentPlan ? parseContentPlan(contentPlan) : null,
    posts: posts.map(parsePost),
    replies: replies.map(parseReply),
    reviewLogs: reviewLogs.map(parseReviewLog),
    campaigns: campaigns.map(parseCampaignSummary),
  };
}

// Get run trace (PRD J5: run trace page shows real agent steps, never an animation)
export function getRunTrace(runId, accountId) {
  const run = db.prepare('SELECT agent_steps, status FROM workflow_runs WHERE id = ? AND account_id = ?').get(runId, accountId);
  if (!run) return null;

  const steps = db.prepare('SELECT * FROM agent_steps WHERE run_id = ? ORDER BY created_at').all(runId);

  return {
    runStatus: run.status,
    trace: run.agent_steps ? JSON.parse(run.agent_steps) : [],
    detailedSteps: steps.map(parseStep),
  };
}

// List past workflow runs (PRD H1)
export function listWorkflowRuns(accountId, limit = 20, offset = 0) {
  const runs = db.prepare('SELECT * FROM workflow_runs WHERE account_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?').all(accountId, limit, offset);
  return runs.map(parseRun);
}

// --- Parsers ---
function parseRun(r) {
  return {
    id: r.id,
    accountId: r.account_id,
    goal: r.goal,
    constraints: JSON.parse(r.constraints || '{}'),
    status: r.status,
    workflowType: r.workflow_type,
    agentSteps: r.agent_steps ? JSON.parse(r.agent_steps) : [],
    resultSummary: r.result_summary ? JSON.parse(r.result_summary) : null,
    startedAt: r.started_at,
    completedAt: r.completed_at,
    createdAt: r.created_at,
  };
}

function parseStep(s) {
  return {
    id: s.id,
    runId: s.run_id,
    agentRole: s.agent_role,
    task: s.task,
    status: s.status,
    input: s.input ? JSON.parse(s.input) : null,
    output: s.output ? JSON.parse(s.output) : null,
    attempts: s.attempts,
    error: s.error,
    startedAt: s.started_at,
    completedAt: s.completed_at,
    createdAt: s.created_at,
  };
}

function parseContentPlan(p) {
  return {
    id: p.id,
    runId: p.run_id,
    accountId: p.account_id,
    weekStart: p.week_start,
    weekEnd: p.week_end,
    platforms: JSON.parse(p.platforms || '[]'),
    createdAt: p.created_at,
  };
}

function parsePost(p) {
  return {
    id: p.id,
    contentPlanId: p.content_plan_id,
    accountId: p.account_id,
    dayOfWeek: p.day_of_week,
    date: p.date,
    platform: p.platform,
    postType: p.post_type,
    caption: p.caption,
    hook: p.hook,
    videoScript: p.video_script,
    shotList: JSON.parse(p.shot_list || '[]'),
    hashtags: JSON.parse(p.hashtags || '[]'),
    designBrief: p.design_brief,
    carouselSlides: JSON.parse(p.carousel_slides || '[]'),
    onScreenText: p.on_screen_text,
    callToAction: p.call_to_action,
    status: p.status,
    versions: JSON.parse(p.versions || '[]'),
    currentVersion: p.current_version,
    sourceLink: p.source_link,
    isPlaceholder: !!p.is_placeholder,
    createdAt: p.created_at,
    updatedAt: p.updated_at,
  };
}

function parseReply(r) {
  return {
    id: r.id,
    runId: r.run_id,
    accountId: r.account_id,
    questionType: r.question_type,
    questionText: r.question_text,
    replyText: r.reply_text,
    platform: r.platform,
    status: r.status,
    versions: JSON.parse(r.versions || '[]'),
    createdAt: r.created_at,
  };
}

function parseReviewLog(r) {
  return {
    id: r.id,
    runId: r.run_id,
    reviewerAgent: r.reviewer_agent,
    assetType: r.asset_type,
    assetId: r.asset_id,
    issue: r.issue,
    fix: r.fix ? JSON.parse(r.fix) : null,
    status: r.status,
    createdAt: r.created_at,
  };
}

function parseCampaignSummary(c) {
  return {
    id: c.id,
    runId: c.run_id,
    accountId: c.account_id,
    businessGoal: c.business_goal,
    durationWeeks: c.duration_weeks,
    budget: c.budget,
    planType: c.plan_type,
    status: c.status,
    createdAt: c.created_at,
  };
}

// Export parsers for use by other controllers
export { parsePost, parseCampaignSummary };
