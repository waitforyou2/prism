#!/usr/bin/env node
/**
 * Defuddle-powered full-text content fetcher.
 *
 * Reads a JSON array of search results from stdin or --in.
 * If an item contains htmlPath, parse the local HTML file with Defuddle.
 * Otherwise, fall back to downloading the page in Node first.
 */

process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

import { Defuddle } from 'defuddle/node';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import os from 'os';
import path from 'path';

const args = process.argv.slice(2);
const MIN_RELEVANCE = parseInt(getArg(args, '--min-relevance') ?? '70', 10);
const CONCURRENCY = parseInt(getArg(args, '--concurrency') ?? '3', 10);
const TIMEOUT_MS = parseInt(getArg(args, '--timeout') ?? '25000', 10);

const SKIP_SOURCES = new Set(['bilibili', 'weibo']);
const MIN_FULL_TEXT_WORDS = 100;

function getArg(argv, flag) {
  const idx = argv.indexOf(flag);
  return idx !== -1 ? argv[idx + 1] : null;
}

function isSogouLink(item) {
  return item.source === 'sogou' && item.url.includes('sogou.com/link');
}

function log(...msg) {
  process.stderr.write(msg.join(' ') + '\n');
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function summarizeResult(result) {
  const content = result.content ?? '';
  const wordCount = content.split(/\s+/).filter(Boolean).length;
  const isFullText = wordCount >= MIN_FULL_TEXT_WORDS;
  return {
    title: result.title ?? '',
    fullContent: content,
    author: result.author ?? null,
    publishedAt: result.published ?? null,
    wordCount,
    fetchStatus: isFullText ? 'ok' : 'ok_low_content',
  };
}

export async function extractContentFromHtml(htmlPath, url) {
  const html = fs.readFileSync(htmlPath, 'utf8');
  const dom = new JSDOM(html, { url });
  const result = await Defuddle(dom.window.document, url, {
    markdown: true,
    debug: false,
  });
  return summarizeResult(result);
}

function decodeBingUrl(url) {
  try {
    const parsed = new URL(url);
    const u = parsed.searchParams.get('u');
    if (!u) return url;
    const b64 = u.startsWith('a1') ? u.slice(2) : u;
    const decoded = Buffer.from(b64, 'base64').toString('utf-8');
    new URL(decoded);
    return decoded;
  } catch {
    return url;
  }
}

async function resolveUrl(url) {
  if (url.includes('bing.com/ck/')) {
    const resolved = decodeBingUrl(url);
    if (resolved !== url) {
      log(`  Bing URL decoded -> ${resolved.slice(0, 80)}`);
      return resolved;
    }
  }

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
        log(`  Sogou redirect -> ${res.url.slice(0, 80)}`);
        return res.url;
      }
    } catch {
      // Fall through.
    }
  }

  return url;
}

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

async function extractContent(originalUrl) {
  const url = await resolveUrl(originalUrl);
  const html = await fetchWithTimeout(url, TIMEOUT_MS);
  const tmpPath = path.join(
    os.tmpdir(),
    `prism-defuddle-${Date.now()}-${Math.random().toString(16).slice(2)}.html`
  );
  fs.writeFileSync(tmpPath, html, 'utf8');
  try {
    const parsed = await extractContentFromHtml(tmpPath, url);
    return {
      ...parsed,
      resolvedUrl: url !== originalUrl ? url : undefined,
    };
  } finally {
    try {
      fs.unlinkSync(tmpPath);
    } catch {
      // Best-effort cleanup.
    }
  }
}

async function processItem(item, index, total) {
  const prefix = `[${index + 1}/${total}]`;

  if ((item.relevance ?? 0) < MIN_RELEVANCE) {
    log(`${prefix} Skipped (relevance ${item.relevance} < ${MIN_RELEVANCE}): ${item.title?.slice(0, 60)}`);
    return { ...item, fetchStatus: 'skipped_low_relevance' };
  }

  if (SKIP_SOURCES.has(item.source) || isSogouLink(item)) {
    log(`${prefix} Skipped (no extractor for ${item.source} or sogou redirect): ${item.title?.slice(0, 60)}`);
    return { ...item, fetchStatus: 'skipped_no_extractor', fullContent: item.content ?? '', wordCount: 0 };
  }

  log(`${prefix} Parsing [${item.source}]: ${item.url}`);

  try {
    const extracted = item.htmlPath
      ? await extractContentFromHtml(item.htmlPath, item.fetchedUrl || item.url)
      : await extractContent(item.url);
    const flag = extracted.fetchStatus === 'ok_low_content' ? ' low-content' : '';
    log(`${prefix} OK ${extracted.wordCount}w${flag}: ${item.title?.slice(0, 50)}`);
    return {
      ...item,
      ...extracted,
      title: extracted.title || item.title,
    };
  } catch (err) {
    log(`${prefix} Failed (${err.message?.slice(0, 80)}): ${item.url}`);
    return {
      ...item,
      fullContent: item.content ?? '',
      wordCount: 0,
      fetchStatus: 'failed',
      fetchError: err.message?.slice(0, 200),
    };
  }
}

async function processBatch(items) {
  const results = [];
  for (let i = 0; i < items.length; i += CONCURRENCY) {
    const batch = items.slice(i, i + CONCURRENCY);
    const batchResults = await Promise.all(
      batch.map((item, j) => processItem(item, i + j, items.length))
    );
    results.push(...batchResults);
    if (i + CONCURRENCY < items.length) {
      await sleep(1000);
    }
  }
  return results;
}

async function main() {
  const inFile = getArg(args, '--in');
  const outFile = getArg(args, '--out');

  let raw = '';
  if (inFile) {
    raw = fs.readFileSync(inFile, 'utf8');
  } else {
    for await (const chunk of process.stdin) raw += chunk;
  }

  let items;
  try {
    items = JSON.parse(raw);
    if (!Array.isArray(items)) throw new Error('Expected JSON array');
  } catch (err) {
    process.stderr.write(`Failed to parse input JSON: ${err.message}\n`);
    process.exit(1);
  }

  const eligible = items.filter(
    (item) => (item.relevance ?? 0) >= MIN_RELEVANCE && !SKIP_SOURCES.has(item.source) && !isSogouLink(item)
  );
  const skipped = items.filter(
    (item) => (item.relevance ?? 0) < MIN_RELEVANCE || SKIP_SOURCES.has(item.source) || isSogouLink(item)
  );

  log(`\n${items.length} items received`);
  log(`${eligible.length} eligible for Defuddle parsing`);
  log(`${skipped.length} skipped before parsing\n`);

  const enrichedEligible = await processBatch(eligible);
  const passthrough = skipped.map((item) => ({
    ...item,
    fetchStatus: (item.relevance ?? 0) < MIN_RELEVANCE ? 'skipped_low_relevance' : 'skipped_no_extractor',
    fullContent: item.content ?? '',
    wordCount: 0,
  }));

  const indexMap = new Map(enrichedEligible.map((item) => [item.url, item]));
  const output = items.map((item) => indexMap.get(item.url) ?? passthrough.find((p) => p.url === item.url) ?? item);

  const okCount = output.filter((item) => item.fetchStatus === 'ok').length;
  const failCount = output.filter((item) => item.fetchStatus === 'failed').length;
  log(`\nDone: ${okCount} ok, ${failCount} failed, ${items.length - okCount - failCount} skipped`);

  if (outFile) {
    fs.writeFileSync(outFile, JSON.stringify(output, null, 2) + '\n', 'utf8');
    log(`Saved to ${outFile}`);
  } else {
    process.stdout.write(JSON.stringify(output, null, 2) + '\n');
  }
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err.message}\n`);
  process.exit(1);
});
