// Given an array of {areaCode, richness} for ONE family, returns each row
// annotated with average rank, dense rank, tie label, and pct-above-average.
// Mirrors sr.rank(method='average'), sr.rank(method='dense'), and
// (sr - sr.mean()) / sr.mean() from the Python loader — computed per-family,
// on demand, instead of precomputed for every family up front.
export function rankFamily(entries) {
  const n = entries.length;
  if (n === 0) return [];

  const mean = entries.reduce((sum, d) => sum + d.richness, 0) / n;
  const sorted = [...entries].sort((a, b) => b.richness - a.richness);

  const out = new Array(n);
  let i = 0;
  let denseRank = 0;

  while (i < n) {
    let j = i;
    while (j < n && sorted[j].richness === sorted[i].richness) j++;

    const groupSize = j - i;
    const avgRank = (i + 1 + j) / 2;
    denseRank += 1;
    const tieLabel = groupSize > 1
      ? `${denseRank} (${groupSize}-way tie)`
      : `${denseRank}`;

    for (let k = i; k < j; k++) {
      const row = sorted[k];
      // An all-zero family has no meaningful percentage above its mean.
      const pct = mean === 0 ? null : (row.richness - mean) / mean;
      out[k] = {
        ...row,
        rank: avgRank,
        denseRank,
        tieCount: groupSize,
        tieLabel,
        pctAboveAvg: pct < 0 ? null : pct
      };
    }
    i = j;
  }
  return out;
}