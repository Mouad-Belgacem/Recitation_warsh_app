const fs = require("fs");
const path = require("path");
const { ph1T } = require("./track_phase1");
const { processPhoneticText } = require("./track_phonetize");

const RANK_SAMPLE_K = 64;

function phonetize(aya, attachLawasiq = false, cfg = null) {
  aya = "$" + aya + "$";
  const [transformed, track1] = ph1T(aya, { attachLawasiq });
  const [final_, track2] = processPhoneticText(transformed, track1, cfg);
  const track = track2.map(i => i - 1);
  return [final_, track];
}

function mapFromCondense(script) {
  const compressed = [];
  const correspondence = [];
  let i = 0;
  while (i < script.length) {
    compressed.push(script[i]);
    correspondence.push(i);
    let j = i + 1;
    while (j < script.length && script[j] === script[i]) j++;
    i = j;
  }
  correspondence.push(script.length);
  return [compressed.join(""), correspondence];
}

function condense(script) {
  let result = "";
  for (let i = 0; i < script.length; i++) {
    if (i === 0 || script[i] !== script[i - 1]) result += script[i];
  }
  return result;
}

function dscore(x, px) {
  x = px === x ? 0 : x;
  return x > 0 ? 0.6 * x : 0.2 * x;
}

function rankC(c, i, bwt, occCk, k, nBlocks) {
  const b = Math.floor((i + 1) / k);
  let cnt = occCk[c * nBlocks + b];
  for (let j = b * k; j <= i; j++) {
    if (bwt[j] === c) cnt++;
  }
  return cnt;
}

function backwardSearchC(P, C, bwt, occCk, k, n) {
  const nBlocks = Math.floor(bwt.length / k) + 1;
  const p = P.length;
  let i = p - 1;
  let c = P[i];
  let First = C[c];
  let Last = c < C.length - 1 ? C[c + 1] - 1 : n - 1;

  while (First <= Last && i >= 1) {
    c = P[i - 1];
    First = C[c] + (First > 0 ? rankC(c, First - 1, bwt, occCk, k, nBlocks) : 0);
    Last = C[c] + rankC(c, Last, bwt, occCk, k, nBlocks) - 1;
    i--;
  }
  if (Last < First) return [-1, -1];
  return [First, Last];
}

class ModifiedMatcher {
  constructor(a, b, minD = 2, minLength = 4) {
    this.a = a || "";
    this.b = b || "";
    this.minD = minD;
    this.minLength = minLength;
    this.matchingBlocks = null;
    this.b2j = null;
  }

  setSeq1(a) {
    this.a = a;
    this.matchingBlocks = null;
    this.b2j = null;
  }

  setSeq2(b) {
    this.b = b;
    this.matchingBlocks = null;
    this.b2j = null;
  }

  _chainB() {
    const [bCondensed] = mapFromCondense(this.b);
    this.b2j = {};
    for (let i = 0; i < bCondensed.length; i++) {
      const ch = bCondensed[i];
      if (!this.b2j[ch]) this.b2j[ch] = [];
      this.b2j[ch].push(i);
    }
  }

  findLongestMatch(alo = 0, ahi = null, blo = 0, bhi = null, match = [-1, "end"]) {
    if (!this.b2j) this._chainB();
    if (ahi === null) ahi = this.a.length;
    if (bhi === null) bhi = this.b.length;
    if (match[0] === -1) match = [this.a.length - 1, "end"];

    let bestI = alo, bestJ = blo, bestSize = 0;
    let bestIs = [bestI], bestJs = [bestJ], bestSizes = [0];

    let j2len = {};
    for (let i = alo; i < ahi; i++) {
      const newJ2len = {};
      const indices = this.b2j[this.a[i]] || [];
      for (const j of indices) {
        if (j < blo) continue;
        if (j >= bhi) break;
        const length = (j2len[j - 1] || 0) + 1;
        newJ2len[j] = length;

        if (length > bestSize) {
          bestI = i - length + 1; bestJ = j - length + 1; bestSize = length;
          bestIs = [bestI]; bestJs = [bestJ]; bestSizes = [length];
        } else if (length === bestSize) {
          bestIs.push(i - length + 1);
          bestJs.push(j - length + 1);
          bestSizes.push(length);
        }
      }
      j2len = newJ2len;
    }

    let chosen;
    if (match[1] === "end") {
      chosen = 0;
      let minDist = Math.abs(bestIs[0] + bestSizes[0] - match[0]);
      for (let idx = 1; idx < bestIs.length; idx++) {
        const d = Math.abs(bestIs[idx] + bestSizes[idx] - match[0]);
        if (d < minDist) { minDist = d; chosen = idx; }
      }
    } else {
      chosen = 0;
      let minDist = Math.abs(bestIs[0] - match[0]);
      for (let idx = 1; idx < bestIs.length; idx++) {
        const d = Math.abs(bestIs[idx] - match[0]);
        if (d < minDist) { minDist = d; chosen = idx; }
      }
    }
    return [bestIs[chosen], bestJs[chosen], bestSizes[chosen]];
  }

  getMatchingBlocks(nSpan = 3, match = [-1, "end"]) {
    if (this.matchingBlocks !== null) return this.matchingBlocks;

    const aNC = this.a, bNC = this.b;
    let mapA, mapB;
    [this.a, mapA] = mapFromCondense(this.a);
    [this.b, mapB] = mapFromCondense(this.b);
    this.b2j = null;
    const la = this.a.length, lb = this.b.length;

    const queue = [[0, la, 0, lb, match]];
    let blocks = [];
    while (queue.length) {
      const [alo, ahi, blo, bhi, m] = queue.pop();
      const [i, j, k] = this.findLongestMatch(alo, ahi, blo, bhi, m);
      if (k) {
        blocks.push([i, j, k]);
        if (alo < i && blo < j) queue.push([alo, i, blo, j, [i, "end"]]);
        if (i + k < ahi && j + k < bhi) queue.push([i + k, ahi, j + k, bhi, [i + k, "start"]]);
      }
    }
    blocks.sort((a, b) => a[0] - b[0] || a[1] - b[1]);

    let i1 = 0, j1 = 0, k1 = 0;
    const nonAdj = [];
    for (const [i2, j2, k2] of blocks) {
      if (i1 + k1 === i2 && j1 + k1 === j2) {
        k1 += k2;
      } else {
        if (k1) nonAdj.push([i1, j1, k1]);
        i1 = i2; j1 = j2; k1 = k2;
      }
    }
    if (k1) nonAdj.push([i1, j1, k1]);
    blocks = nonAdj;

    const filtered = blocks.map(x => Math.round(x[2]) >= this.minLength ? 1 : 0);
    for (let s = 0; s < nSpan; s++) {
      for (let i = 0; i < blocks.length - 1; i++) {
        if (filtered[i] + filtered[i + 1] === 1) {
          const [i2, ,] = blocks[i + 1];
          const [i1b, , k1b] = blocks[i];
          if (i2 - (i1b + k1b) <= this.minD) filtered[i] = filtered[i + 1] = 1;
        }
      }
    }
    blocks = blocks.filter((_, i) => filtered[i] === 1);

    this.matchingBlocks = blocks.map(([i, j, k]) => [
      mapA[i], mapB[j], mapA[i + k] - mapA[i], mapB[j + k] - mapB[j],
    ]);
    this.a = aNC;
    this.b = bNC;
    this.b2j = null;
    return this.matchingBlocks;
  }

  ratio(borderPenalty = false) {
    const blocks = this.getMatchingBlocks();
    const matchesA = blocks.reduce((s, t) => s + t[2], 0);
    const matchesB = blocks.reduce((s, t) => s + t[3], 0);
    let mismatchesA, mismatchesB;
    if (borderPenalty) {
      mismatchesA = this.a.length - matchesA;
      mismatchesB = this.b.length - matchesB;
    } else {
      mismatchesA = 0; mismatchesB = 0;
      for (let i = 0; i < blocks.length - 1; i++) {
        mismatchesA += blocks[i + 1][0] - blocks[i][0] - blocks[i][2];
        mismatchesB += blocks[i + 1][1] - blocks[i][1] - blocks[i][3];
      }
    }
    return (matchesA + matchesB - mismatchesA - mismatchesB) / 16 / Math.sqrt(this.b.length);
  }
}

function searchSorted(arr, value, side = "right") {
  let lo = 0, hi = arr.length;
  if (side === "right") {
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (arr[mid] <= value) lo = mid + 1; else hi = mid;
    }
  } else {
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (arr[mid] < value) lo = mid + 1; else hi = mid;
    }
  }
  return lo;
}

function groupBy(str) {
  const groups = [];
  if (!str.length) return groups;
  let cur = str[0], cnt = 1;
  for (let i = 1; i < str.length; i++) {
    if (str[i] === cur) cnt++;
    else { groups.push([cur, cnt]); cur = str[i]; cnt = 1; }
  }
  groups.push([cur, cnt]);
  return groups;
}

function writeInt32(filePath, arr) {
  const buf = Buffer.from(arr.buffer, arr.byteOffset, arr.byteLength);
  fs.writeFileSync(filePath, buf);
}

function readInt32(filePath) {
  const buf = fs.readFileSync(filePath);
  return new Int32Array(buf.buffer, buf.byteOffset, buf.length / 4);
}

function writeUint8(filePath, arr) {
  fs.writeFileSync(filePath, Buffer.from(arr.buffer, arr.byteOffset, arr.byteLength));
}

function readUint8(filePath) {
  const buf = fs.readFileSync(filePath);
  return new Uint8Array(buf.buffer, buf.byteOffset, buf.length);
}

function writeUint16(filePath, arr) {
  const buf = Buffer.from(arr.buffer, arr.byteOffset, arr.byteLength);
  fs.writeFileSync(filePath, buf);
}

function readUint16(filePath) {
  const buf = fs.readFileSync(filePath);
  return new Uint16Array(buf.buffer, buf.byteOffset, buf.length / 2);
}

class Finder {
  constructor(moshafLocation = "quran.json", dataLocation = "Data_for_quran_search", widthFactor = 2) {
    this.dataLocation = dataLocation;
    this.widthFactor = widthFactor;

    const data = JSON.parse(fs.readFileSync(moshafLocation, "utf-8"));
    this.quran = {};
    this._quranKeys = [];
    for (let i = 0; i < data.length; i++) {
      const surah = data[i];
      const ayahs = surah.ayahs || [];
      for (let j = 0; j < ayahs.length; j++) {
        const key = `${i + 1},${j + 1}`;
        this.quran[key] = ayahs[j].trim();
        this._quranKeys.push(key);
      }
    }

    this._init();
  }

  _init() {
    const d = this.dataLocation;
    const requiredFiles = [
      "bwt.bin", "occ_ck.bin", "C.bin",
      "row_to_ayaid.bin", "ayaid_to_verse.bin",
      "aya_starts_uthmani.bin", "spaces.bin",
      "one_string_quran.txt", "one_string_uthmani.txt",
      "aya_to_index.json", "aya_to_index_uthmani.json",
      "vocab.txt",
    ];
    const ready = fs.existsSync(d) &&
      requiredFiles.every(f => fs.existsSync(path.join(d, f)));

    if (ready) {
      this._loadPrecomputed();
    } else {
      this._buildAll();
    }
  }

  _loadPrecomputed() {
    const d = this.dataLocation;
    this.oneStringQuran = fs.readFileSync(path.join(d, "one_string_quran.txt"), "utf-8");

    this.ayaToIndex = JSON.parse(fs.readFileSync(path.join(d, "aya_to_index.json"), "utf-8"));

    const vocabStr = fs.readFileSync(path.join(d, "vocab.txt"), "utf-8");
    this.vocab = Array.from(vocabStr).sort();
    this.vocabToIndex = {};
    for (let i = 0; i < this.vocab.length; i++) this.vocabToIndex[this.vocab[i]] = i;
    this.n = this.oneStringQuran.length + 1;

    this.bwt = readUint8(path.join(d, "bwt.bin"));
    this.occCk = readInt32(path.join(d, "occ_ck.bin"));
    this._occCkCols = Math.floor(this.bwt.length / RANK_SAMPLE_K) + 1;
    this.C = readInt32(path.join(d, "C.bin"));
    this.rowToAyaid = readUint16(path.join(d, "row_to_ayaid.bin"));

    const ayaidFlat = readInt32(path.join(d, "ayaid_to_verse.bin"));
    this.ayaidToVerse = [];
    for (let i = 0; i < ayaidFlat.length / 2; i++) {
      this.ayaidToVerse.push([ayaidFlat[i * 2], ayaidFlat[i * 2 + 1]]);
    }

    this.oneStringUthmani = fs.readFileSync(path.join(d, "one_string_uthmani.txt"), "utf-8");
    this.ayaToIndexUthmani = JSON.parse(fs.readFileSync(path.join(d, "aya_to_index_uthmani.json"), "utf-8"));
    this.ayaStartsUthmani = readInt32(path.join(d, "aya_starts_uthmani.bin"));
    this.spaces = readInt32(path.join(d, "spaces.bin"));
  }

  _buildAll() {
    const d = this.dataLocation;
    fs.mkdirSync(d, { recursive: true });

    this._initPhoneticVariables();
    this._initVocab();
    const sa = this._buildSuffixArray();
    this._initRank(sa);
    this._initC(sa);
    this._initRowToAya(sa);
    this._initUthmaniVariables();
    this._initAyaStartsUthmani();
    this._initWordBoundaries();
  }

  _initPhoneticVariables() {
    const d = this.dataLocation;
    let oneStringQuran = "";
    const ayaToIndex = {};
    let idx = 0;
    for (const key of this._quranKeys) {
      const aya = this.quran[key];
      const [ph] = phonetize(aya);
      const phc = condense(ph);
      oneStringQuran += phc;
      ayaToIndex[key] = [idx, idx + phc.length];
      idx += phc.length;
    }
    this.oneStringQuran = oneStringQuran;
    this.ayaToIndex = ayaToIndex;
    this.n = oneStringQuran.length + 1;

    fs.writeFileSync(path.join(d, "one_string_quran.txt"), oneStringQuran, "utf-8");
    fs.writeFileSync(path.join(d, "aya_to_index.json"), JSON.stringify(ayaToIndex), "utf-8");
  }

  _initVocab() {
    const d = this.dataLocation;
    const text = this.oneStringQuran + "#";
    this.vocab = Array.from(new Set(text)).sort();
    this.vocabToIndex = {};
    for (let i = 0; i < this.vocab.length; i++) this.vocabToIndex[this.vocab[i]] = i;
    fs.writeFileSync(path.join(d, "vocab.txt"), this.vocab.join(""), "utf-8");
  }

  _buildSuffixArray() {
    const text = this.oneStringQuran + "#";
    const n = text.length;
    let k = 1;
    const rank = new Int32Array(n);
    for (let i = 0; i < n - 1; i++) rank[i] = text.charCodeAt(i);
    rank[n - 1] = 0;
    const tmp = new Int32Array(n);
    const sa = new Int32Array(n);
    for (let i = 0; i < n; i++) sa[i] = i;

    while (k < n) {
      const kk = k;
      const rankSnap = rank.slice();
      sa.sort((a, b) => {
        if (rankSnap[a] !== rankSnap[b]) return rankSnap[a] - rankSnap[b];
        const ra = a + kk < n ? rankSnap[a + kk] : -1;
        const rb = b + kk < n ? rankSnap[b + kk] : -1;
        return ra - rb;
      });
      tmp[sa[0]] = 0;
      for (let i = 1; i < n; i++) {
        const prev = sa[i - 1], curr = sa[i];
        const sameFirst = rankSnap[prev] === rankSnap[curr];
        const rp = prev + kk < n ? rankSnap[prev + kk] : -1;
        const rc = curr + kk < n ? rankSnap[curr + kk] : -1;
        tmp[curr] = tmp[prev] + (sameFirst && rp === rc ? 0 : 1);
      }
      rank.set(tmp);
      k *= 2;
    }
    return sa;
  }

  _initRank(sa) {
    const d = this.dataLocation;
    const text = this.oneStringQuran + "#";
    const sigma = this.vocab.length;

    const bwt = new Uint8Array(sa.length);
    for (let i = 0; i < sa.length; i++) {
      bwt[i] = this.vocabToIndex[text[sa[i] === 0 ? text.length - 1 : sa[i] - 1]];
    }
    this.bwt = bwt;

    const nBlocks = Math.floor(bwt.length / RANK_SAMPLE_K) + 1;
    const occCk = new Int32Array(sigma * nBlocks);
    for (let b = 1; b < nBlocks; b++) {
      for (let c = 0; c < sigma; c++) {
        occCk[c * nBlocks + b] = occCk[c * nBlocks + (b - 1)];
      }
      const blockStart = (b - 1) * RANK_SAMPLE_K;
      const blockEnd = Math.min(b * RANK_SAMPLE_K, bwt.length);
      for (let j = blockStart; j < blockEnd; j++) {
        occCk[bwt[j] * nBlocks + b]++;
      }
    }
    this.occCk = occCk;
    this._occCkCols = nBlocks;

    writeUint8(path.join(d, "bwt.bin"), bwt);
    writeInt32(path.join(d, "occ_ck.bin"), occCk);
  }

  _initC(sa) {
    const d = this.dataLocation;
    const text = this.oneStringQuran + "#";
    const F = new Array(sa.length);
    for (let i = 0; i < sa.length; i++) F[i] = text[sa[i]];

    const C = new Int32Array(this.vocab.length);
    for (let c = 0; c < this.vocab.length; c++) {
      C[c] = F.indexOf(this.vocab[c]);
    }
    this.C = C;
    writeInt32(path.join(d, "C.bin"), C);
  }

  _initRowToAya(sa) {
    const d = this.dataLocation;
    const nq = this.oneStringQuran.length;

    const keys = this._quranKeys;
    const starts = new Int32Array(keys.length);
    for (let i = 0; i < keys.length; i++) {
      starts[i] = this.ayaToIndex[keys[i]][0];
    }

    const posToAyaid = new Uint16Array(this.n);
    for (let p = 0; p < nq; p++) {
      posToAyaid[p] = searchSorted(starts, p, "right") - 1;
    }
    posToAyaid[nq] = posToAyaid[nq - 1];

    const rowToAyaid = new Uint16Array(sa.length);
    for (let i = 0; i < sa.length; i++) {
      rowToAyaid[i] = posToAyaid[sa[i]];
    }
    this.rowToAyaid = rowToAyaid;

    const ayaidToVerse = new Int32Array(keys.length * 2);
    this.ayaidToVerse = [];
    for (let i = 0; i < keys.length; i++) {
      const [s, a] = keys[i].split(",").map(Number);
      ayaidToVerse[i * 2] = s;
      ayaidToVerse[i * 2 + 1] = a;
      this.ayaidToVerse.push([s, a]);
    }

    writeUint16(path.join(d, "row_to_ayaid.bin"), rowToAyaid);
    writeInt32(path.join(d, "ayaid_to_verse.bin"), ayaidToVerse);
  }

  _initUthmaniVariables() {
    const d = this.dataLocation;
    let oneStringUthmani = "";
    const ayaToIndexUthmani = {};
    let idx = 0;
    for (const key of this._quranKeys) {
      const aya = this.quran[key];
      oneStringUthmani += aya + " ";
      ayaToIndexUthmani[key] = [idx, idx + aya.length];
      idx += aya.length + 1;
    }
    oneStringUthmani = oneStringUthmani.slice(0, -1);
    this.oneStringUthmani = oneStringUthmani;
    this.ayaToIndexUthmani = ayaToIndexUthmani;

    fs.writeFileSync(path.join(d, "one_string_uthmani.txt"), oneStringUthmani, "utf-8");
    fs.writeFileSync(path.join(d, "aya_to_index_uthmani.json"), JSON.stringify(ayaToIndexUthmani), "utf-8");
  }

  _initAyaStartsUthmani() {
    const d = this.dataLocation;
    const keys = this._quranKeys;
    const starts = new Int32Array(keys.length);
    for (let i = 0; i < keys.length; i++) {
      starts[i] = this.ayaToIndexUthmani[keys[i]][0];
    }
    this.ayaStartsUthmani = starts;
    writeInt32(path.join(d, "aya_starts_uthmani.bin"), starts);
  }

  _initWordBoundaries() {
    const d = this.dataLocation;
    const spaceIndices = [];
    for (let i = 0; i < this.oneStringUthmani.length; i++) {
      if (this.oneStringUthmani[i] === " ") spaceIndices.push(i);
    }
    this.spaces = new Int32Array(spaceIndices);
    writeInt32(path.join(d, "spaces.bin"), this.spaces);
  }

  getIndices(P) {
    return Array.from(P).map(ch => this.vocabToIndex[ch]);
  }

  backwardSearch(P) {
    const indices = this.getIndices(P);
    return backwardSearchC(indices, this.C, this.bwt, this.occCk, RANK_SAMPLE_K, this.n);
  }

  getCandidatAyas(P, k = 30, l = 10) {
    P = condense(P);
    const indices = this.getIndices(P);
    l = Math.min(l, indices.length);
    if (l < 1) return [];

    const counts = {};
    for (let start = 0; start + l <= indices.length; start += l) {
      const window = indices.slice(start, start + l);
      const [first, last] = backwardSearchC(window, this.C, this.bwt, this.occCk, RANK_SAMPLE_K, this.n);
      if (first < 0) continue;
      for (let r = first; r <= last; r++) {
        const aid = this.rowToAyaid[r];
        counts[aid] = (counts[aid] || 0) + 1;
      }
    }

    const entries = Object.entries(counts).map(([aid, cnt]) => [Number(aid), cnt]);
    entries.sort((a, b) => b[1] - a[1] || a[0] - b[0]);
    const top = entries.slice(0, k);
    return top.map(([aid]) => this.ayaidToVerse[aid]);
  }

  getAya(P, l = 10) {
    let candidats = [0];
    while (candidats.length < 2 && l > 4) {
      candidats = this.getCandidatAyas(P, 30, l);
      l -= 2;
    }
    if (!candidats.length) return [null, 0, 0];

    const sm = new ModifiedMatcher(null, P);
    const ratios = [];
    for (const cand of candidats) {
      const key = `${cand[0]},${cand[1]}`;
      const [s, e] = this.ayaToIndex[key];
      const text = this.oneStringQuran.slice(s, e);
      sm.setSeq1(text);
      ratios.push(sm.ratio());
    }
    const indices = ratios.map((v, i) => i).sort((a, b) => ratios[a] - ratios[b]);
    const best = indices[indices.length - 1];
    const second = indices.length > 2 ? indices[indices.length - 2] : best - 1;
    return [candidats[best], ratios[best], ratios[best] - (ratios[second] || 0)];
  }

  verseToCursor(verse) {
    const key = `${verse[0]},${verse[1]}`;
    const [start, end] = this.ayaToIndexUthmani[key];
    return Math.floor((start + end) / 2);
  }

  ayaAtUthmani(p) {
    const aid = searchSorted(this.ayaStartsUthmani, p, "right") - 1;
    return this.ayaidToVerse[Math.max(aid, 0)];
  }

  startWord(p) {
    const j = searchSorted(this.spaces, p, "right");
    return j === 0 ? 0 : this.spaces[j - 1] + 1;
  }

  endWord(p) {
    const j = searchSorted(this.spaces, p, "left");
    if (j === this.spaces.length) return this.oneStringUthmani.length - 1;
    return this.spaces[j] - 1;
  }

  getFragment(cursor, width, pushToVerse = true) {
    const m = this.oneStringUthmani.length;
    const begin = cursor - Math.floor(width * 0.7);
    const finish = cursor + Math.floor(width * 0.5);
    let startIdx, endIdx;
    if (pushToVerse) {
      const sv = this.ayaAtUthmani(Math.max(begin, 0));
      const ev = this.ayaAtUthmani(Math.min(finish, m - 1));
      startIdx = this.ayaToIndexUthmani[`${sv[0]},${sv[1]}`][0];
      endIdx = this.ayaToIndexUthmani[`${ev[0]},${ev[1]}`][1] - 1;
    } else {
      startIdx = this.startWord(Math.max(begin, 0));
      endIdx = this.endWord(Math.min(finish, m - 1));
    }
    return [startIdx, endIdx];
  }

  refinedUthmani(tilawa, cursor, width, refCursor = null, pushToVerse = true) {
    if (refCursor === null) refCursor = cursor;
    const [start, end] = this.getFragment(cursor, width, pushToVerse);
    const localCursor = refCursor - start;
    const uthmaniText = this.oneStringUthmani.slice(start, end + 1);
    const [phoneticScript, track] = phonetize(uthmaniText);

    let minDist = Infinity, index = 0;
    for (let i = 0; i < track.length; i++) {
      const d = Math.abs(track[i] - localCursor);
      if (d < minDist || (d === minDist && i > index)) { minDist = d; index = i; }
    }

    const sm = new ModifiedMatcher(phoneticScript, tilawa);
    const matchingBlocks = sm.getMatchingBlocks(0, [index, "start"]);

    if (!matchingBlocks.length) return [start, end];

    const firstMatch = matchingBlocks[0][0];
    const lastMatch = matchingBlocks[matchingBlocks.length - 1][0] + matchingBlocks[matchingBlocks.length - 1][2] - 1;

    const wordStart = this.startWord(start + track[firstMatch]);
    const wordEnd = this.endWord(start + track[firstMatch]);
    const penetration = (wordEnd - start - track[firstMatch]) / (wordEnd - wordStart || 1);

    const firstUthmaniWord = penetration > 0.5 ? wordStart : wordEnd + 1;
    const lastUthmaniWord = this.endWord(start + track[lastMatch]);

    return [firstUthmaniWord, lastUthmaniWord];
  }

  find(tilawa) {
    const [ayaIdc] = this.getAya(tilawa);
    if (!ayaIdc) return "";
    const cursor = this.verseToCursor(ayaIdc);
    const [start, end] = this.refinedUthmani(tilawa, cursor, Math.floor(this.widthFactor * tilawa.length));
    return this.oneStringUthmani.slice(start, end + 1);
  }
}

class Corrector {
  constructor(finder, cursor = 0, attachLawasiq = false, offset = 1) {
    this.finder = finder;
    this.cursor = cursor;
    this.refCursor = 0;
    this.settled = false;
    this.stops = 0;
    this.score = 2;
    this.previousScore = 0;
    this.localScore = 0;
    this.attachLawasiq = attachLawasiq;
    this.previousTilawa = "";
    this.previousResults = ["", [], []];
    this.offset = offset;
  }

  correct(tilawa, wasl = false, attachLawasiq = false, threshold = 3) {
    const width = Math.floor(this.finder.widthFactor * (tilawa.length + 5));

    const w = Math.floor((10 * Math.exp(-this.score) + this.offset) * width);
    let [start, end] = this.finder.refinedUthmani(tilawa, this.cursor, w, this.refCursor, false);
    let uthmaniText = this.finder.oneStringUthmani.slice(start, end + 1).trim();
    let [phoneticScript, track] = phonetize(uthmaniText, attachLawasiq);
    const sm = new ModifiedMatcher(phoneticScript, tilawa);

    if (!this.settled) {
      const cursorRatio = sm.ratio(true);
      const [ayaIdc, score, gap] = this.finder.getAya(tilawa);

      if (ayaIdc && (gap >= 0.2 || tilawa.length >= 40)) {
        const cursorT = this.finder.verseToCursor(ayaIdc);
        const [startT, endT] = this.finder.refinedUthmani(tilawa, cursorT, width);
        const uthmaniTextT = this.finder.oneStringUthmani.slice(startT, endT + 1).trim();
        const [phoneticScriptT, trackT] = phonetize(uthmaniTextT, attachLawasiq);
        sm.setSeq1(phoneticScriptT);

        const globalScore = sm.ratio(true);
        if (cursorRatio < globalScore) {
          start = startT; end = endT;
          uthmaniText = uthmaniTextT;
          phoneticScript = phoneticScriptT; track = trackT;
        } else {
          sm.setSeq1(phoneticScript);
        }
      }
    }

    this.cursor = end;
    const r = sm.ratio(true);
    if ((!wasl || tilawa.length > 40) && r > 0) {
      this.refCursor = end;
    } else if (!this.settled || r < 0) {
      this.cursor = this.refCursor;
    }

    this.previousScore = this.score;
    const increment = dscore(r, this.localScore);
    this.score = Math.min(2 * threshold, this.score + increment);
    this.score = Math.max(0, this.score);

    if (!wasl && increment > 0.1) this.stops++;
    else if (increment > 0.1) {
      this.stops += Math.max(0, Math.floor(tilawa.length / 70) - Math.floor(this.previousTilawa.length / 70));
    }

    if (this.score >= threshold) this.settled = true;
    else if (this.stops < 3) this.settled = false;

    if (r < 0) return ["", [], []];

    this.localScore = r;

    const colors = [];
    const additions = [];
    let a0 = 0, b0 = 0;
    let ai = 0, sizeA = 0, sizeB = 0;

    for (const [blockAi, blockBj, blockSA, blockSB] of sm.getMatchingBlocks()) {
      ai = blockAi; sizeA = blockSA; sizeB = blockSB;
      if (a0 < ai) {
        for (let x = 0; x < ai - a0; x++) colors.push(-1);
      }
      if (b0 < blockBj) additions.push(track[a0]);

      const repA = groupBy(sm.a.slice(ai, ai + sizeA)).map(g => g[1]);
      const repB = groupBy(sm.b.slice(blockBj, blockBj + sizeB)).map(g => g[1]);
      for (let ind = 0; ind < repA.length; ind++) {
        const c = ind < repB.length && repA[ind] <= repB[ind] ? 1 : 0;
        for (let x = 0; x < repA[ind]; x++) colors.push(c);
      }
      a0 = ai + sizeA;
      b0 = blockBj + sizeB;
    }

    if (ai + sizeA !== phoneticScript.length) {
      const remaining = phoneticScript.length - ai - sizeA;
      const c = wasl ? 2 : -1;
      for (let x = 0; x < remaining; x++) colors.push(c);
    }

    const uthColors = new Array(uthmaniText.length).fill(3);
    for (let i = 0; i < colors.length; i++) {
      uthColors[track[i]] = Math.min(uthColors[track[i]], colors[i]);
    }

    let idx = 0;
    const groups = [];
    while (idx < uthColors.length) {
      const val = uthColors[idx];
      let cnt = 1;
      while (idx + cnt < uthColors.length && uthColors[idx + cnt] === val) cnt++;
      groups.push([val, idx, cnt]);
      idx += cnt;
    }
    for (const [val, gStart, gLen] of groups) {
      if (val === 3) {
        const prev = gStart === 0 ? -1 : uthColors[gStart - 1];
        const next = gStart + gLen === uthColors.length ? -1 : uthColors[gStart + gLen];
        const fill = Math.max(prev, next);
        for (let x = gStart; x < gStart + gLen; x++) uthColors[x] = fill;
      }
    }

    this.previousTilawa = tilawa;
    this.previousResults = [uthmaniText, uthColors, additions];
    return [uthmaniText, uthColors, additions];
  }

  getAya(tilawa) {
    if (this.settled) {
      const verse = this.finder.ayaAtUthmani(this.cursor);
      return [[verse[0], verse[1]], this.score];
    }
    return this.finder.getAya(tilawa);
  }
}

module.exports = {
  phonetize, mapFromCondense, condense, dscore,
  ModifiedMatcher, Finder, Corrector,
  RANK_SAMPLE_K,
};
