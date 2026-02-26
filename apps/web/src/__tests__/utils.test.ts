import { describe, it, expect } from 'vitest';
import { cn, generateId, formatRelativeTime } from '@/lib/utils';

describe('cn()', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles falsy values', () => {
    expect(cn('foo', undefined, false as any, null as any, 'bar')).toBe('foo bar');
  });

  it('resolves conflicting tailwind classes (last wins)', () => {
    expect(cn('p-4', 'p-8')).toBe('p-8');
  });

  it('handles empty input', () => {
    expect(cn()).toBe('');
  });

  it('handles conditional objects', () => {
    expect(cn({ 'text-red-500': true, 'text-blue-500': false })).toBe('text-red-500');
  });
});

describe('generateId()', () => {
  it('returns a non-empty string', () => {
    expect(typeof generateId()).toBe('string');
    expect(generateId().length).toBeGreaterThan(0);
  });

  it('generates unique ids across 100 calls', () => {
    const ids = new Set(Array.from({ length: 100 }, generateId));
    expect(ids.size).toBe(100);
  });

  it('contains a numeric timestamp prefix', () => {
    const before = Date.now();
    const id = generateId();
    const after = Date.now();
    const ts = parseInt(id.split('-')[0], 10);
    expect(ts).toBeGreaterThanOrEqual(before);
    expect(ts).toBeLessThanOrEqual(after);
  });
});

describe('formatRelativeTime()', () => {
  it('returns "just now" for 0–59 seconds ago', () => {
    const now = new Date();
    expect(formatRelativeTime(now)).toBe('just now');
    expect(formatRelativeTime(new Date(now.getTime() - 30_000))).toBe('just now');
    expect(formatRelativeTime(new Date(now.getTime() - 59_000))).toBe('just now');
  });

  it('returns "1m ago" at the 60-second boundary', () => {
    const now = new Date();
    expect(formatRelativeTime(new Date(now.getTime() - 60_000))).toBe('1m ago');
  });

  it('returns minutes for 1–59 minutes ago', () => {
    const now = new Date();
    expect(formatRelativeTime(new Date(now.getTime() - 5 * 60_000))).toBe('5m ago');
    expect(formatRelativeTime(new Date(now.getTime() - 59 * 60_000))).toBe('59m ago');
  });

  it('returns hours for 1–23 hours ago', () => {
    const now = new Date();
    expect(formatRelativeTime(new Date(now.getTime() - 3 * 3_600_000))).toBe('3h ago');
    expect(formatRelativeTime(new Date(now.getTime() - 23 * 3_600_000))).toBe('23h ago');
  });

  it('returns days for 1–6 days ago', () => {
    const now = new Date();
    expect(formatRelativeTime(new Date(now.getTime() - 2 * 86_400_000))).toBe('2d ago');
    expect(formatRelativeTime(new Date(now.getTime() - 6 * 86_400_000))).toBe('6d ago');
  });

  it('returns a localized date string for 7+ days ago', () => {
    const old = new Date(2020, 0, 1);
    const result = formatRelativeTime(old);
    expect(result).not.toMatch(/ago$/);
    expect(result.length).toBeGreaterThan(0);
  });
});
