#!/usr/bin/env node
/**
 * fetch_content.js — Defuddle-powered full-text content fetcher
 *
 * Reads a JSON array of search results from stdin (with relevance scores),
 * fetches full content for items with relevance >= MIN_RELEVANCE using Defuddle,
 * and writes enriched JSON array to stdout.
 *
 * Usage:
 *   echo '[{"url":"https://...","relevance":85,...}]' | node fetch_content.js
 *   cat filtered.json | node fetch_content.js --min-relevance 75
 *   cat filtered.json | node fetch_content.js --concurrency 2
 *
 * Outputs JSON array to stdout; progress/errors go to stderr.
 */

import { Defuddle } from 'defuddle/node';
import { JSDOM } from 'jsdom';

// ── Config ────────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const MIN_RELEVANCE = parseInt(getArg(args, '--min-relevance') ?? '70', 10);
const CONCURRENCY   = parseInt(getArg(args, '--concurrency') ?? '3', 10);
const TIMEOUT_MS    = parseInt(getArg(args, '--timeout') ?? '25000', 10);

// Sources Defuddle cannot meaningfully extract (short-circuit these)
const SKIP_SOURCES = new Set(['bilibili', 'weibo']);

// Minimum words to consider a fetch "full-text" quality
// Below this threshold the item is flagged as signal-quality
const MIN_FULL_TEXT_WORDS = 100;

// ── URL Pre-resolution ────────────────────────────────────────────────────────

/**
 * Decode a Bing redirect URL to the real destination.
 * Bing wraps results as: bing.com/ck/a?...&u=a1{base64url}&...
 * The 'u' param has a '"a1' prefix before the base64 content.
 */
function decodeBingUrl(url) {
  try {
    const parsed = new URL(url);
    const u = parsed.searchParams.get('u');
    if (!u) return url;
    // Strip 'a1' prefix that Bing prepends
    const b64 = u.startsWith('a1') ? u.slice(2) : u;
    const decoded = Buffer.from(b64, 'base64').toString('utf-8');
    // Validate it's a real URL
    new URL(decoded);
    return decoded;
  } catch {
    return url;
  }
}

/**
 * Resolve search engine redirect URLs to their final destinations.
 * Handles: Bing (ck/a?), Sogou (sogou.com/link?)
 */
async function resolveUrl(url) {
  // Bing: decode base64 directly (no HTTP round-trip needed)
  if (url.includes('bing.com/ck/')) {
    const resolved = decodeBingUrl(url);
    if (resolved !== url) {
      log(`  🔗 Bing URL decoded → ${resolved.slice(0, 80)}`);
      return resolved;
    }
  }

  // Sogou: follow HTTP redirect (302) to get real URL
  if (url.includes('sogou.com/link')) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);
      const res = await fetch(url, {
        method: 'HEAD',
        redirect: 'follow',
        signal: controller.signal,
        headers: { 'User-Agent': 'Mozilla/5.0' },
      });
      clearTimeout(timer);
      if (res.url && res.url !== url) {
        log(`  🔗 Sogou redirect → ${res.url.slice(0, 80)}`);
        return res.url;
      }
    } catch {
      // Fall through to original URL
    }
  }

  return url;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getArg(args, flag) {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : null;
}

function log(...msg) {
  process.stderr.write(msg.join(' ') + '\n');
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

/**
 * Fetch a URL with timeout. Returns response text or throws.
 */
async function fetchWithTimeout(url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5,zh-CN;q=0.3',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.text();
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Extract full content from a URL using Defuddle.
 * Automatically resolves search engine redirect URLs first.
 * Returns { title, content, author, publishedAt, wordCount, fetchStatus, resolvedUrl }
 */
async function extractContent(originalUrl) {
  // Pre-resolve redirect URLs before fetching
  const url = await resolveUrl(originalUrl);

  const html = await fetchWithTimeout(url, TIMEOUT_MS);
  const dom = new JSDOM(html, { url });

  const result = await Defuddle(dom.window.document, url, {
    markdown: true,
    debug: false,
  });

  const content = result.content ?? '';
  const wordCount = content.split(/\s+/).filter(Boolean).length;

  // Flag low-content fetches — likely still a redirect page or paywall
  const isFullText = wordCount >= MIN_FULL_TEXT_WORDS;

  return {
    title: result.title ?? '',
    fullContent: content,
    author: result.author ?? null,
    publishedAt: result.published ?? null,
    wordCount,
    resolvedUrl: url !== originalUrl ? url : undefined,
    fetchStatus: isFullText ? 'ok' : 'ok_low_content',
  };
}

/**
 * Process a single search result item.
 */
async function processItem(item, index, total) {
  const prefix = `[${index + 1}/${total}]`;

  // Skip low-relevance items
  if ((item.relevance ?? 0) < MIN_RELEVANCE) {
    log(`${prefix} ⏭  Skipped (relevance ${item.relevance} < ${MIN_RELEVANCE}): ${item.title?.slice(0, 60)}`);
    return { ...item, fetchStatus: 'skipped_low_relevance' };
  }

  // Skip sources without meaningful extractors
  if (SKIP_SOURCES.has(item.source)) {
    log(`${prefix} ⏭  Skipped (no extractor for ${item.source}): ${item.title?.slice(0, 60)}`);
    return { ...item, fetchStatus: 'skipped_no_extractor', fullContent: item.content ?? '', wordCount: 0 };
  }

  log(`${prefix} 🔍 Fetching [${item.source}]: ${item.url}`);

  try {
    const extracted = await extractContent(item.url);
    const flag = extracted.fetchStatus === 'ok_low_content' ? ' ⚠️ low-content' : '';
    log(`${prefix} ✅ ${extracted.wordCount}w${flag}: ${item.title?.slice(0, 50)}`);
    return {
      ...item,
      ...extracted,
      title: extracted.title || item.title,
    };
  } catch (err) {
    log(`${prefix} ❌ Failed (${err.message?.slice(0, 80)}): ${item.url}`);
    return {
      ...item,
      fullContent: item.content ?? '',
      wordCount: 0,
      fetchStatus: 'failed',
      fetchError: err.message?.slice(0, 200),
    };
  }
}

/**
 * Process items in batches to limit concurrency.
 */
async function processBatch(items) {
  const results = [];
  for (let i = 0; i < items.length; i += CONCURRENCY) {
    const batch = items.slice(i, i + CONCURRENCY);
    const batchResults = await Promise.all(
      batch.map((item, j) => processItem(item, i + j, items.length))
    );
    results.push(...batchResults);
    // Small delay between batches to be polite
    if (i + CONCURRENCY < items.length) await sleep(1000);
  }
  return results;
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  // Read JSON from stdin
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;

  let items;
  try {
    items = JSON.parse(raw);
    if (!Array.isArray(items)) throw new Error('Expected JSON array');
  } catch (err) {
    process.stderr.write(`❌ Failed to parse stdin JSON: ${err.message}\n`);
    process.exit(1);
  }

  const eligible = items.filter(i => (i.relevance ?? 0) >= MIN_RELEVANCE && !SKIP_SOURCES.has(i.source));
  const skipped  = items.filter(i => (i.relevance ?? 0) < MIN_RELEVANCE || SKIP_SOURCES.has(i.source));

  log(`\n📥 ${items.length} items received`);
  log(`🎯 ${eligible.length} eligible for full fetch (relevance ≥ ${MIN_RELEVANCE}, source not in skip list)`);
  log(`⏭  ${skipped.length} will be passed through without fetching\n`);

  const enrichedEligible = await processBatch(eligible);
  const passthrough = skipped.map(i => ({
    ...i,
    fetchStatus: (i.relevance ?? 0) < MIN_RELEVANCE ? 'skipped_low_relevance' : 'skipped_no_extractor',
    fullContent: i.content ?? '',
    wordCount: 0,
  }));

  // Merge and preserve original order
  const indexMap = new Map(enrichedEligible.map(i => [i.url, i]));
  const output = items.map(i => indexMap.get(i.url) ?? passthrough.find(p => p.url === i.url) ?? i);

  const okCount = output.filter(i => i.fetchStatus === 'ok').length;
  const failCount = output.filter(i => i.fetchStatus === 'failed').length;
  log(`\n✨ Done: ${okCount} ok, ${failCount} failed, ${items.length - okCount - failCount} skipped`);

  process.stdout.write(JSON.stringify(output, null, 2) + '\n');
}

main().catch(err => {
  process.stderr.write(`Fatal: ${err.message}\n`);
  process.exit(1);
});
