import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { config } from './src/config/index.js';
import { errorHandler, notFoundHandler } from './src/middleware/errorHandler.js';

// Routes
import authRoutes from './src/routes/authRoutes.js';
import profileRoutes from './src/routes/profileRoutes.js';
import workflowRoutes from './src/routes/workflowRoutes.js';
import agentRoutes from './src/routes/agentRoutes.js';
import campaignRoutes from './src/routes/campaignRoutes.js';
import postRoutes from './src/routes/postRoutes.js';
import reportRoutes from './src/routes/reportRoutes.js';
import historyRoutes from './src/routes/historyRoutes.js';
import exportRoutes from './src/routes/exportRoutes.js';
import platformRoutes from './src/routes/platformRoutes.js';

const app = express();

// --- Security & middleware ---
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({ origin: config.cors.origin }));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// --- Health check ---
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'AI Social Media Manager API',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
  });
});

// --- API routes ---
app.use('/api/auth', authRoutes);
app.use('/api/profile', profileRoutes);
app.use('/api/workflow', workflowRoutes);
app.use('/api/agent', agentRoutes);
app.use('/api/campaigns', campaignRoutes);
app.use('/api/posts', postRoutes);
app.use('/api/reports', reportRoutes);
app.use('/api/history', historyRoutes);
app.use('/api/export', exportRoutes);
app.use('/api/platforms', platformRoutes);

// --- 404 & Error handling ---
app.use(notFoundHandler);
app.use(errorHandler);

// --- Start server ---
const PORT = config.port;
app.listen(PORT, () => {
  console.log('');
  console.log('┌─────────────────────────────────────────────┐');
  console.log('│  AI Social Media Manager API                │');
  console.log('│  ─────────────────────────────────────────── │');
  console.log(`│  Server:     http://localhost:${PORT}          │`);
  console.log(`│  Environment: ${config.nodeEnv.padEnd(29)}│`);
  console.log(`│  Database:   ${config.dbPath.substring(0, 28).padEnd(29)}│`);
  console.log(`│  Cloud:      ${config.cloud.endpoint ? 'connected' : 'local mode (no cloud)'.padEnd(29)}│`);
  console.log(`│  Run limit:  ${config.limits.maxRunsPerDay}/day (demo: unlimited)${' '.repeat(Math.max(0, 8 - String(config.limits.maxRunsPerDay).length))}│`);
  console.log('└─────────────────────────────────────────────┘');
  console.log('');
  console.log('Available routes:');
  console.log('  POST   /api/auth/signup');
  console.log('  POST   /api/auth/login');
  console.log('  GET    /api/auth/me');
  console.log('  POST   /api/auth/verify-email');
  console.log('  POST   /api/auth/enable-2fa');
  console.log('  POST   /api/auth/verify-2fa');
  console.log('  POST   /api/auth/password-reset/request');
  console.log('  POST   /api/auth/password-reset/confirm');
  console.log('  GET    /api/profile');
  console.log('  POST   /api/profile');
  console.log('  PUT    /api/profile');
  console.log('  POST   /api/workflow/run         (start weekly workflow)');
  console.log('  GET    /api/workflow/runs         (list past runs)');
  console.log('  GET    /api/workflow/runs/:runId  (run details)');
  console.log('  GET    /api/workflow/runs/:runId/trace');
  console.log('  POST   /api/agent/run            (one-prompt agentic run)');
  console.log('  GET    /api/agent/run/:runId/status');
  console.log('  POST   /api/campaigns            (create LinkedIn campaign)');
  console.log('  GET    /api/campaigns             (list campaigns)');
  console.log('  GET    /api/campaigns/:id        (campaign details)');
  console.log('  PUT    /api/campaigns/:id/assets/:assetId  (edit asset)');
  console.log('  POST   /api/campaigns/:id/assets/:assetId/regenerate');
  console.log('  GET    /api/campaigns/:id/assets/:assetId/versions');
  console.log('  PUT    /api/campaigns/:id/assets/:assetId/status');
  console.log('  POST   /api/posts/:id/edit       (edit post fields)');
  console.log('  POST   /api/posts/:id/regenerate (regenerate with instruction)');
  console.log('  GET    /api/posts/:id/versions    (list versions)');
  console.log('  POST   /api/posts/:id/restore     (restore version)');
  console.log('  PUT    /api/posts/:id/status      (draft/ready/posted)');
  console.log('  POST   /api/reports/weekly        (create weekly report)');
  console.log('  GET    /api/reports/weekly        (list reports)');
  console.log('  GET    /api/reports/weekly/:id    (report details)');
  console.log('  POST   /api/reports/periodic      (monthly/quarterly/annual)');
  console.log('  GET    /api/reports/periodic');
  console.log('  GET    /api/history               (list past runs+campaigns)');
  console.log('  GET    /api/history/:runId        (reopen a run)');
  console.log('  GET    /api/history/:runId/validation');
  console.log('  POST   /api/export/calendar       (CSV calendar)');
  console.log('  POST   /api/export/posts          (CSV/JSON posts)');
  console.log('  POST   /api/export/campaign       (CSV/JSON campaign)');
  console.log('  GET    /api/export/report/:reportId');
  console.log('  GET    /api/platforms/formats     (platform-native formats)');
  console.log('');
  console.log(`Demo login: ${config.limits.demoEmail} / ${config.limits.demoPassword}`);
  console.log('');
});
