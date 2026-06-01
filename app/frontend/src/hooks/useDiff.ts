/**
 * Simple LCS-based text diff hook
 *
 * Returns an array of diff segments: { text, type: 'same' | 'added' | 'removed' }
 */

export interface DiffSegment {
  text: string;
  type: 'same' | 'added' | 'removed';
}

function lcs(a: string[], b: string[]): string[] {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to find LCS
  const result: string[] = [];
  let i = m, j = n;
  while (i > 0 && j > 0) {
    if (a[i - 1] === b[j - 1]) {
      result.unshift(a[i - 1]);
      i--;
      j--;
    } else if (dp[i - 1][j] > dp[i][j - 1]) {
      i--;
    } else {
      j--;
    }
  }

  return result;
}

export function computeDiff(textA: string, textB: string): DiffSegment[] {
  const wordsA = textA.split(/(\s+)/);
  const wordsB = textB.split(/(\s+)/);
  const common = lcs(wordsA, wordsB);

  const segments: DiffSegment[] = [];
  let ai = 0, bi = 0, ci = 0;

  while (ci < common.length) {
    // Collect removed words (in A but not in common)
    while (ai < wordsA.length && wordsA[ai] !== common[ci]) {
      segments.push({ text: wordsA[ai], type: 'removed' });
      ai++;
    }
    // Collect added words (in B but not in common)
    while (bi < wordsB.length && wordsB[bi] !== common[ci]) {
      segments.push({ text: wordsB[bi], type: 'added' });
      bi++;
    }
    // Common word
    segments.push({ text: common[ci], type: 'same' });
    ai++;
    bi++;
    ci++;
  }

  // Remaining words
  while (ai < wordsA.length) {
    segments.push({ text: wordsA[ai], type: 'removed' });
    ai++;
  }
  while (bi < wordsB.length) {
    segments.push({ text: wordsB[bi], type: 'added' });
    bi++;
  }

  return segments;
}

export function useDiff(textA: string, textB: string): DiffSegment[] {
  return computeDiff(textA, textB);
}
