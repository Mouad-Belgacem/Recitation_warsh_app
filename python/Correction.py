import os
import json
import numpy as np
from numba import njit, prange
from itertools import groupby
from collections import namedtuple as _namedtuple
Match = _namedtuple('Match', 'a b size')

# Text comparison
from difflib import SequenceMatcher

# Phonetization
from track_phase1 import ph1T
from track_phonetize import process_phonetic_text

RANK_SAMPLE_K = 64   # rank checkpoint spacing, in BWT positions

def phonetize(aya, attach_lawasiq=False):

    aya = "$" + aya + "$"
    transformed, track = ph1T(aya, attach_lawasiq=attach_lawasiq)
    final, track = process_phonetic_text(transformed, track)
    track = [i-1 for i in track]

    return final, track

def map_from_condense(script):
    compressed = []
    correspondence = []

    i = 0
    while i < len(script):
        compressed.append(script[i])
        correspondence.append(i)

        j = i + 1
        while j < len(script) and script[j] == script[i]:
            j += 1
        i = j
    correspondence.append(len(script))

    return "".join(compressed), correspondence

# A useful function to update the trust
def dscore(x, px):
    # px for past x.
    # if px == x then probably the reciter didn't speak and it's
    # the algorithm feeding the same audio. In such situation we don't
    # update
    x = 0 if px == x else x
    return .6*x if x>0 else .2*x


# To improve performance we use numba.jit to compile some search functions. 
# Since compiling doesn't work well inside a class we define some function outside the 
# class definition

@njit(inline="always")
def rank_c(c, i, bwt, occ_ck, k):
    """Number of occurrences of symbol c in bwt[0..i], inclusive.
    occ_ck[c, b] is the EXCLUSIVE count over bwt[0 .. b*k-1], so
    occ_ck[:, 0] == 0. Scans at most k-1 bytes after the checkpoint."""
    b = (i + 1) // k
    cnt = occ_ck[c, b]
    for j in range(b * k, i + 1):
        if bwt[j] == c:
            cnt += 1
    return cnt

# We use the same names as the paper
@njit
def backward_search_c(P, C, bwt, occ_ck, k, n) -> tuple[int, int]: # _c for compiled
    p = len(P)
    i = p-1
    c = P[i]
    if c < C.size - 1:
        First, Last = C[c], C[c+1]-1
    else:
        First, Last = C[c], n-1
    while First <= Last and i>=1:
        c = P[i-1]
        # rank_c(c, First-1, ...) returns 0 when First == 0, which is the right
        # answer for an empty prefix. The dense table this replaces indexed
        # occ[c, -1] there and silently returned the TOTAL count of c; it never
        # fired only because "#" sorts first, so C[c] >= 1 for every real symbol
        # and First was therefore never 0. That landmine is now gone.
        First = C[c] + rank_c(c, First - 1, bwt, occ_ck, k)
        Last  = C[c] + rank_c(c, Last,      bwt, occ_ck, k) - 1
        i -= 1
    if Last < First :
        return (-1, -1)
    return (First, Last)

@njit(parallel=True)
def batch_backward_search(Ps, C, bwt, occ_ck, k, n):
    m = Ps.shape[0]
    out_first = np.zeros(m, dtype=np.int32)
    out_last  = np.zeros(m, dtype=np.int32)

    for idx in prange(m):
        out_first[idx], out_last[idx] = backward_search_c(
            Ps[idx,:], C, bwt, occ_ck, k, n)

    return out_first, out_last

def condense(script):
    "This function remove consecutif repetion in a string"
    return ''.join(k for k, _ in groupby(script))

# We modify the method "get_matching_blocks" in difflib to become more adapted to our problem
class ModifiedMatcher(SequenceMatcher):
    def __init__(self, *args, min_d=2, min_length=4, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_d = min_d
        self.min_length = min_length
        self.bpopular = set()
        self.bjunk = set()
        # self.horof_mad = "اےۥ"

    def _SequenceMatcher__chain_b(self):
        b = map_from_condense(self.b)[0]
        self.b2j = b2j = {}

        for i, elt in enumerate(b):
            indices = b2j.setdefault(elt, [])
            indices.append(i)

    def find_longest_match(self, alo=0, ahi=None, blo=0, bhi=None, match=(-1,"end")):
        '''Documentation in the original function inside difflib.SequenceMatcher'''

        a, b, b2j, isbjunk = self.a, self.b, self.b2j, self.bjunk.__contains__
        if ahi is None:
            ahi = len(a)
        if bhi is None:
            bhi = len(b)
        if match[0] == -1:
            match = (len(a)-1, "end")
        besti, bestj, bestrealsize = alo, blo, 0
        bestis = [besti]
        bestjs = [bestj]
        bestrealsizes = [0]

        j2len = {}
        nothing = []
        for i in range(alo, ahi):
            j2lenget = j2len.get
            newj2len = {}
            for j in b2j.get(a[i], nothing):
                if j < blo:
                    continue
                if j >= bhi:
                    break
                length= j2lenget(j-1, 0)
                # increment = 1/4 if a[i] in self.horof_mad else 1
                length = length + 1 #, pseudo_length + increment
                newj2len[j] = length #, pseudo_length
                
                if length > bestrealsize:
                    besti, bestj, bestrealsize = i-length+1, j-length+1, length
                    bestis = [besti]
                    bestjs = [bestj]
                    bestrealsizes = [length]

                elif length == bestrealsize:
                    bestis.append(i-length+1)
                    bestjs.append(j-length+1)
                    bestrealsizes.append(length)

            j2len = newj2len
        
        if match[1] == "end":
            index = min(range(len(bestis)), key=lambda i: abs(bestis[i] + bestrealsizes[i] - match[0]))
        else:
            index = min(range(len(bestis)), key=lambda i: abs(bestis[i] - match[0]))

        return Match(bestis[index], bestjs[index], bestrealsizes[index])

    def get_matching_blocks(self, n_span=3, match=(-1,"end")):

        if self.matching_blocks is not None:
            return self.matching_blocks
        a_nc, b_nc = self.a, self.b  # nc for non compressed
        self.a, map_a = map_from_condense(self.a)
        self.b, map_b = map_from_condense(self.b)
        la, lb = len(self.a), len(self.b)

        # This is most naturally expressed as a recursive algorithm, but
        # at least one user bumped into extreme use cases that exceeded
        # the recursion limit on their box.  So, now we maintain a list
        # ('queue`) of blocks we still need to look at, and append partial
        # results to `matching_blocks` in a loop; the matches are sorted
        # at the end.
        queue = [(0, la, 0, lb, match)]
        matching_blocks = []
        while queue:
            alo, ahi, blo, bhi, match = queue.pop()
            (i, j, k) = x = self.find_longest_match(alo, ahi, blo, bhi, match)
            if k: 
                matching_blocks.append(x)
                if alo < i and blo < j:
                    queue.append((alo, i, blo, j, (i, "end")))
                if i+k < ahi and j+k < bhi:
                    queue.append((i+k, ahi, j+k, bhi, (i+k, "start")))
        matching_blocks.sort()

        # It's possible that we have adjacent equal blocks in the
        # matching_blocks list now.  Starting with 2.5, this code was added
        # to collapse them.
        i1 = j1 = k1 = 0
        non_adjacent = []
        for (i2, j2, k2) in matching_blocks:
            # Is this block adjacent to i1, j1, k1?
            if i1 + k1 == i2 and j1 + k1 == j2:
                # Yes, so collapse them -- this just increases the length of
                # the first block by the length of the second, and the first
                # block so lengthened remains the block to compare against.
                k1 += k2
            else:
                # Not adjacent.  Remember the first block (k1==0 means it's
                # the dummy we started with), and make the second block the
                # new block to compare against.
                if k1:
                    non_adjacent.append(Match(i1, j1, k1))
                i1, j1, k1 = i2, j2, k2
        if k1:
            non_adjacent.append(Match(i1, j1, k1))

        del matching_blocks
        matching_blocks = non_adjacent

        # Eliminating small and remote blocks
        filtered_blocks = [1 if round(x[2]) >= self.min_length else 0 for x in matching_blocks]
        for _ in range(n_span):
            for i, x in enumerate(matching_blocks[:-1]):
                if filtered_blocks[i] + filtered_blocks[i+1] == 1:
                    (i2, j2, k2) = matching_blocks[i+1]
                    (i1, j1, k1) = x
                    d = i2 - (i1+k1)
                    if d <= self.min_d:
                        filtered_blocks[i] = filtered_blocks[i+1] = 1
        
        matching_blocks = [x for i, x in enumerate(matching_blocks) if filtered_blocks[i]==1]

        # filtered_blocks = []
        # if len(matching_blocks) > 1:
        #     for index in range(len(matching_blocks)):
        #         (i1, j1, k1), l1 = matching_blocks[index]
        #         if index == 0:
        #             (i2, j2, k2), l2 = matching_blocks[index+1]
        #             remote = sum(1 for _ in groupby(self.a[i1+k1:i2])) > self.min_d and l1 < self.min_length and (i2 - i1 - k1) > 0
        #         elif index == len(matching_blocks)-1:
        #             (i3, j3, k3), l3 = matching_blocks[index-1]
        #             remote = sum(1 for _ in groupby(self.a[i3+k3:i1])) > self.min_d and l1 < self.min_length and (i1 - i3 - k3) > 0
        #         else:
        #             (i2, j2, k2), l2 = matching_blocks[index+1]
        #             remote1 = sum(1 for _ in groupby(self.a[i1+k1:i2])) > self.min_d and l1 < self.min_length and (i2 - i1 - k1) > 0
        #             (i3, j3, k3), l3 = matching_blocks[index-1]
        #             remote2 = sum(1 for _ in groupby(self.a[i3+k3:i1])) > self.min_d and l1 < self.min_length and (i1 - i3 - k3) > 0
        #             remote = remote1 and remote2

        #         if not remote:
        #             filtered_blocks.append(matching_blocks[index][0])
        # elif len(matching_blocks) == 1:
        #     filtered_blocks = [matching_blocks[0][0]]
        # else:
        #     filtered_blocks = []
        
        # del matching_blocks
        # matching_blocks = filtered_blocks

        # non_adjacent.append( (la, lb, 0) ) # We don't need a dummy block!
        self.matching_blocks = [(map_a[i], map_b[j], map_a[i+k]-map_a[i], map_b[j+k]-map_b[j]) for i, j, k in matching_blocks]
        self.a, self.b = a_nc, b_nc
        return self.matching_blocks
    
    def ratio(self, boarder_penalty=False):

        matching_blocks = self.get_matching_blocks()
        matches_a = sum(triple[2] for triple in matching_blocks)
        matches_b = sum(triple[3] for triple in matching_blocks)
        if boarder_penalty:
            mismatches_a = len(self.a) - matches_a
            mismatches_b = len(self.b) - matches_b
        else:
            mismatches_a = sum([matching_blocks[i+1][0] - matching_blocks[i][0] - matching_blocks[i][2] for i in range(len(matching_blocks)-1)])
            mismatches_b = sum([matching_blocks[i+1][1] - matching_blocks[i][1] - matching_blocks[i][3] for i in range(len(matching_blocks)-1)])
        return (matches_a + matches_b  - mismatches_a - mismatches_b) / 16 / np.sqrt(len(self.b))
    
class Finder:
    """
    The goal of this class is, given a tilawa string, to find the location of the tilawa in Quran.
    The search uses the FM-index algorithm, which suppose the precalculation of

    C:      first BWT row starting with each symbol, in vocab order.
    bwt:    the Burrows-Wheeler transform, as vocab indices (uint8).
    occ_ck: rank checkpoints, EXCLUSIVE counts every RANK_SAMPLE_K positions.
            Together with bwt this replaces the old dense (sigma x n) occ table:
            82.5 MB -> 1.8 MB, at the cost of scanning <=RANK_SAMPLE_K-1
            contiguous bytes per rank query. See rank_c.

    Also, to have a meaningful search in the hole Quran we needed to calculate the following variables

    ---Variables related to the search in the phonetics script-----
    one_string_quran:
    aya_to_index:
    row_to_ayaid:   BWT row -> global aya id. Replaces the suffix array and
                    index_to_aya, which were only ever used composed: 8.0 MB
                    -> 1.0 MB. The suffix array is now build-time only
                    (see _get_sa).
    ayaid_to_verse: global aya id -> (sura, aya).
    vocab_to_idex:

    ---Variables related to the search in uthmani script---
    one_string_uthmani:
    aya_to_index_uthmani:
    aya_starts_uthmani: start offset of each aya. Replaces index_to_aya_uthmani
                    (5.7 MB per-character map) - see aya_at_uthmani.
    spaces:         offset of each space. Replaces BOTH index_to_start_word and
                    index_to_end_word (5.7 MB each, int64) - see start_word and
                    end_word. All three of these tables were piecewise constant,
                    so only their breakpoints were ever information.
    """

    def __init__(self, moshaf_location="quran.json", data_location = "Data_for_quran_search", save=True, width_factor=2, recalculate=False):

        self.data_location = data_location
        self.save = save
        self.rec = recalculate
        self.width_factor = width_factor

        with open(moshaf_location, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.quran = {}
        for i, surah in enumerate(data, start=1):
            for j, aya in enumerate(surah.get("ayahs", []), start=1):
                self.quran[(i, j)] = aya.strip()
        
        self.one_string_quran, self.aya_to_index = self.init_phonetic_variables()
        self.vocab = self.init_vocab()
        self.vocab_to_idex = {self.vocab[i] : i for i in range(len(self.vocab))}
        self.n = len(self.one_string_quran) + 1

        # Sampled-rank FM-index: the BWT plus one checkpoint column every
        # RANK_SAMPLE_K positions, instead of a dense (sigma x n) table.
        # 82.5 MB -> 1.8 MB, paid for by scanning <=63 contiguous bytes per rank.
        self.bwt, self.occ_ck = self.init_rank()
        self.C = self.init_C()
        # sa and index_to_aya merged: the search only ever used sa to turn a BWT
        # row into a text position and index_to_aya to turn that position into an
        # aya - the position itself was discarded. 8.0 MB -> 1.0 MB.
        self.row_to_ayaid, self.ayaid_to_verse = self.init_row_to_aya()

        self.one_string_uthmani, self.aya_to_index_uthmani = self.init_uthmani_variables()
        # Three per-character tables (17.1 MB) replaced by their breakpoints
        # (0.35 MB): all three were piecewise constant, changing only at an aya
        # boundary or at a space. See aya_at_uthmani / start_word / end_word.
        self.aya_starts_uthmani = self.init_aya_starts_uthmani()
        self.spaces = self.init_word_boundaries()

    def init_phonetic_variables(self):
        # index_to_aya is neither built nor written any more. It was a
        # per-character map (10 MB of JSON) of something aya_to_index already
        # determines exactly - see _pos_to_ayaid_phonetic, which derives it in
        # one searchsorted.
        if not os.path.exists(self.data_location + "/one_string_quran.txt") \
        or not os.path.exists(self.data_location + "/aya_to_index.json") \
        or self.rec:

            one_string_quran = ""
            aya_to_index = {}
            idx = 0
            for key, aya in self.quran.items():
                # Append to the long string
                aya = aya.strip()
                ph, _ = phonetize(aya)
                ph = condense(ph)
                one_string_quran += ph
                aya_to_index[key] = (idx, idx+len(ph))
                idx += len(ph)

            if self.save:
                # First we initialize a directory
                os.makedirs(self.data_location, exist_ok=True)

                # We save the one_string_quran
                with open(self.data_location + "/one_string_quran.txt", "w", encoding="utf-8") as f:
                    f.write(one_string_quran)

                # Json doesn't accept tupls
                json_aya_to_index = {
                    json.dumps(k): json.dumps(v)
                    for k, v in aya_to_index.items()
                }
                with open(self.data_location + "/aya_to_index.json", "w") as f:
                    json.dump(json_aya_to_index, f)
        

        else:
            with open(self.data_location + "/one_string_quran.txt", "r", encoding="utf-8") as f:
                one_string_quran = f.read()
            
            with open(self.data_location + "/aya_to_index.json") as f:
                json_aya_to_index = json.load(f)

            aya_to_index = {
                tuple(json.loads(k)): tuple(json.loads(v))
                for k, v in json_aya_to_index.items()
            }

        return one_string_quran, aya_to_index

    def _pos_to_ayaid_phonetic(self):
        """position in one_string_quran -> global aya id, as an int array.

        Derived from aya_to_index, NOT read from index_to_aya.json. The ayas are
        concatenated with no separator and no gaps, so aya_to_index's 6,214
        (start, end) pairs already determine which aya every one of the 527,579
        positions belongs to - the 10 MB JSON was storing the same fact 85x over
        and has been deleted. Verified exact against it over every position.

        BUILD TIME ONLY: the sole consumer is init_row_to_aya, which composes
        this with the suffix array once and saves the result as row_to_ayaid.
        """
        keys = list(self.quran)
        starts = np.array([self.aya_to_index[k][0] for k in keys], dtype=np.int64)
        assert (np.diff(starts) > 0).all(), \
            "phonetic aya start offsets are not strictly ascending"
        pos = np.arange(len(self.one_string_quran))
        return np.searchsorted(starts, pos, side="right") - 1

    def _get_sa(self):
        """The suffix array, loaded (or built) lazily and cached.

        Nothing reads it at runtime any more - it is an input to init_rank,
        init_C and init_row_to_aya, all of which short-circuit to np.load when
        their artefacts already exist. So on a normal start sa.npy is never
        touched, and it can be left out of a deployment bundle."""
        if getattr(self, "_sa_cache", None) is None:
            self._sa_cache = self.init_sa()
        return self._sa_cache

    def init_sa(self):
        if not os.path.exists(self.data_location + "/sa.npy") or self.rec:
            text = self.one_string_quran + "#"

            # In the following code, we build the suffix array of the one_string_quran
            # The time complexity is O(n log^2 n) and for space it is O(n). The square in the log can be removed by using more advanced sorting algorithms.
            # The idea is to rank the suffixes by their first k characters, then double k until it exceeds n.
            n = len(text)
            k = 1
            rank = [ord(c) for c in text[:-1]] + [0]  # initial ranks. We need to make explicitly sure that # have the lowest rank
            tmp = [0] * n
            sa = list(range(n))  # suffix indices

            while k < n:
                # Sort by rank pairs (current rank, rank at k distance)
                sa.sort(key=lambda x: (rank[x], rank[x + k] if x + k < n else -1))

                tmp[sa[0]] = 0
                for i in range(1, n):
                    prev = sa[i-1]
                    curr = sa[i]
                    tmp[curr] = tmp[prev] + (rank[prev] != rank[curr] or
                                                (rank[prev + k] if prev + k < n else -1) != (rank[curr + k] if curr + k < n else -1))
                rank = tmp[:]
                k *= 2

            sa = np.array(sa)
            
            if self.save:
                os.makedirs(self.data_location, exist_ok=True)
                np.save(self.data_location + "/sa.npy", sa)
        
        else:
            sa = np.load(self.data_location + "/sa.npy")

        return sa

    def init_vocab(self):
        if not os.path.exists(self.data_location + "/vocab.txt") or self.rec:
            text = self.one_string_quran + "#"
            vocab = set(text)
            vocab = sorted(list(vocab))
            if self.save:
                os.makedirs(self.data_location, exist_ok=True)
                with open(self.data_location + "/vocab.txt", "w", encoding="utf-8") as f:
                    f.write("".join(vocab))
        else:
            with open(self.data_location + "/vocab.txt", "r", encoding="utf-8") as f:
                vocab = sorted(list(f.read()))
        
        return vocab

    def init_rank(self):
        """Sampled-rank replacement for the dense (sigma x n) occ table.

        Returns (bwt, occ_ck):
          bwt[i]      uint8, the VOCAB INDEX of the BWT symbol at row i - an
                      index, not a character, so rank_c compares integers.
          occ_ck[c,b] int32, EXCLUSIVE count of symbol c over
                      bwt[0 .. b*RANK_SAMPLE_K - 1]; column 0 is all zeros.

        rank(c, i) = occ_ck[c, (i+1)//k] + a scan of the <= k-1 bytes that follow
        the checkpoint. The dense table cost sigma*n*4 = 82.5 MB and every lookup
        was a random access into it, i.e. a guaranteed cache miss; this costs
        1.8 MB, which mostly lives in L3, and the scan is sequential.
        """
        bwt_path = self.data_location + "/bwt.npy"
        ck_path = self.data_location + "/occ_ck.npy"
        if os.path.exists(bwt_path) and os.path.exists(ck_path) and not self.rec:
            return np.load(bwt_path), np.load(ck_path)

        sa = self._get_sa()
        text = self.one_string_quran + "#"
        sigma = len(self.vocab)
        # Same L the old init_occ built. Its `if i != 0 else '#'` branch was
        # redundant - text[-1] is already the sentinel.
        bwt = np.fromiter((self.vocab_to_idex[text[i - 1]] for i in sa),
                          dtype=np.uint8, count=len(sa))
        assert sigma <= 256, f"sigma={sigma} no longer fits in uint8"

        n_blocks = len(bwt) // RANK_SAMPLE_K + 1
        occ_ck = np.zeros((sigma, n_blocks), dtype=np.int32)
        for b in range(1, n_blocks):
            block = bwt[(b - 1) * RANK_SAMPLE_K: b * RANK_SAMPLE_K]
            occ_ck[:, b] = occ_ck[:, b - 1] + np.bincount(block, minlength=sigma)

        if self.save:
            os.makedirs(self.data_location, exist_ok=True)
            np.save(bwt_path, bwt)
            np.save(ck_path, occ_ck)

        return bwt, occ_ck

    def init_C(self):
        """C[c] = first BWT row whose suffix starts with symbol c, in vocab order.

        Was a {char: int} dict in C.json that __init__ then reordered into an
        array; it is built directly in vocab order now, and saved as .npy so the
        whole index loads through np.load."""
        path = self.data_location + "/C.npy"
        if os.path.exists(path) and not self.rec:
            return np.load(path)

        text = self.one_string_quran + "#"
        F = [text[i] for i in self._get_sa()]
        C = np.zeros(len(self.vocab), dtype=np.int32)
        for i, char in enumerate(self.vocab):
            C[i] = F.index(char)

        if self.save:
            os.makedirs(self.data_location, exist_ok=True)
            np.save(path, C)

        return C

    def init_row_to_aya(self):
        """Merges the suffix array and index_to_aya into a single lookup.

        Returns (row_to_ayaid, ayaid_to_verse):
          row_to_ayaid[row]  uint16, global aya id (0..len(self.quran)-1, which
                             is 6213 for the bundled quran.json) of the position
                             that BWT row `row` points at.
          ayaid_to_verse[id] int32 (sura, aya) - the inverse, 50 KB.

        get_candidat_ayas did `self.index_to_aya[self.sa[rows]]` and threw the
        intermediate position away, so the composition is all that was ever
        needed: 4.0 MB of int64 suffix array + 4.0 MB of (n,2) int32 aya map
        become one 1.0 MB uint16 array, with one indirection instead of two.

        Ids are assigned in self.quran's own iteration order, which is
        sura-major/aya-minor. That makes ascending id equivalent to ascending
        (sura, aya), so np.unique over ids yields the candidates in exactly the
        order np.unique(..., axis=0) over (sura, aya) rows used to.
        """
        row_path = self.data_location + "/row_to_ayaid.npy"
        verse_path = self.data_location + "/ayaid_to_verse.npy"
        if os.path.exists(row_path) and os.path.exists(verse_path) and not self.rec:
            return np.load(row_path), np.load(verse_path)

        ayaid_to_verse = np.zeros((len(self.quran), 2), dtype=np.int32)
        for aid, key in enumerate(self.quran):
            ayaid_to_verse[aid] = key
        assert len(self.quran) <= np.iinfo(np.uint16).max, "too many ayas for uint16"

        nq = len(self.one_string_quran)
        pos_to_ayaid = np.empty(self.n, dtype=np.uint16)
        pos_to_ayaid[:nq] = self._pos_to_ayaid_phonetic()
        # Position nq is the "#" sentinel, which index_to_aya never covered (the
        # old array was nq long, so index_to_aya[nq] would have raised). It is
        # only reachable through BWT row 0, which no real pattern can select
        # because C[c] >= 1 for every non-sentinel symbol. Mirror the last real
        # position so the array is well formed either way.
        pos_to_ayaid[nq] = pos_to_ayaid[nq - 1]

        row_to_ayaid = pos_to_ayaid[self._get_sa()]

        if self.save:
            os.makedirs(self.data_location, exist_ok=True)
            np.save(row_path, row_to_ayaid)
            np.save(verse_path, ayaid_to_verse)

        return row_to_ayaid, ayaid_to_verse

    def init_uthmani_variables(self):
        # index_to_aya_uthmani is neither built nor written any more. It was a
        # per-character map (14 MB of JSON) of something aya_to_index_uthmani
        # already determines - see aya_at_uthmani, which answers it from 24 KB
        # of aya start offsets.
        if not os.path.exists(self.data_location + "/one_string_uthmani.txt") \
        or not os.path.exists(self.data_location + "/aya_to_index_uthmani.json") \
        or self.rec:
            one_string_uthmani = ""
            aya_to_index_uthmani = {}
            idx = 0
            for key, aya in self.quran.items():
                # Append to the long string
                one_string_uthmani += aya + " "
                aya_to_index_uthmani[key] = (idx, idx+len(aya))
                # +1 for the separating space, which the old per-character map
                # attributed to the aya it follows.
                idx += len(aya) + 1

            one_string_uthmani = one_string_uthmani[:-1]
            if self.save:
                os.makedirs(self.data_location, exist_ok=True)

                with open(self.data_location + "/one_string_uthmani.txt", "w", encoding="utf-8") as f:
                    f.write(one_string_uthmani)

                json_aya_to_index = {
                    json.dumps(k): json.dumps(v)
                    for k, v in aya_to_index_uthmani.items()
                }
                with open(self.data_location + "/aya_to_index_uthmani.json", "w") as f:
                    json.dump(json_aya_to_index, f)
        else:
            with open(self.data_location + "/one_string_uthmani.txt", "r", encoding="utf-8") as f:
                one_string_uthmani = f.read()

            with open(self.data_location + "/aya_to_index_uthmani.json") as f:
                json_aya_to_index = json.load(f)

            aya_to_index_uthmani = {
                tuple(json.loads(k)): tuple(json.loads(v))
                for k, v in json_aya_to_index.items()
            }

        return one_string_uthmani, aya_to_index_uthmani

    def init_aya_starts_uthmani(self):
        """Start offset of every aya in one_string_uthmani, ascending.

        Replaces index_to_aya_uthmani, a 742,026-entry per-character map (5.7 MB
        in RAM, 14 MB of JSON). It was piecewise constant, changing only at an
        aya boundary, and aya_to_index_uthmani already holds those boundaries -
        so the big table was storing the same information 120x over.
        """
        path = self.data_location + "/aya_starts_uthmani.npy"
        if os.path.exists(path) and not self.rec:
            return np.load(path)

        starts = np.array([self.aya_to_index_uthmani[key][0]
                           for key in self.quran], dtype=np.int32)
        # aya ids are assigned in self.quran order in init_row_to_aya, so these
        # offsets are in the same order and ascending - which is what lets
        # searchsorted map a position straight to an aya id.
        assert (np.diff(starts) > 0).all(), \
            "aya start offsets are not strictly ascending; searchsorted would lie"

        if self.save:
            os.makedirs(self.data_location, exist_ok=True)
            np.save(path, starts)
        return starts

    def init_word_boundaries(self):
        """Offsets of every space in one_string_uthmani, ascending.

        Replaces BOTH index_to_start_word and index_to_end_word (5.7 MB each,
        and stored as int64 for values under 2**20). Both were piecewise
        constant with exactly these breakpoints, so 11.4 MB becomes 0.32 MB.
        See start_word / end_word for how each is recovered.
        """
        path = self.data_location + "/spaces.npy"
        if os.path.exists(path) and not self.rec:
            return np.load(path)

        spaces = np.array([i for i, ch in enumerate(self.one_string_uthmani)
                           if ch == " "], dtype=np.int32)
        if self.save:
            os.makedirs(self.data_location, exist_ok=True)
            np.save(path, spaces)
        return spaces

    def aya_at_uthmani(self, p):
        """(sura, aya) of uthmani position p. Was index_to_aya_uthmani[p]."""
        aid = int(np.searchsorted(self.aya_starts_uthmani, p, side="right")) - 1
        return self.ayaid_to_verse[max(aid, 0)]

    def start_word(self, p):
        """First character of the word containing uthmani position p.
        Was index_to_start_word[p].

        side="right" counts a space AT p, so when p is itself a space this
        returns the following word's start - matching the original table, whose
        loop assigned start = i+1 before appending at a space."""
        j = int(np.searchsorted(self.spaces, p, side="right"))
        return 0 if j == 0 else int(self.spaces[j - 1]) + 1

    def end_word(self, p):
        """Last character of the word containing uthmani position p.
        Was index_to_end_word[p].

        side="left" does NOT count a space at p, so when p is itself a space
        this returns the preceding word's end - again matching the original,
        which walked the string in reverse and appended m-end-1."""
        j = int(np.searchsorted(self.spaces, p, side="left"))
        if j == len(self.spaces):
            return len(self.one_string_uthmani) - 1
        return int(self.spaces[j]) - 1

    def get_indices(self, P):
        return np.array([self.vocab_to_idex[p] for p in P], dtype=np.int32)
    
    def backward_search(self, P:str):
        return backward_search_c(self.get_indices(P), self.C, self.bwt,
                                 self.occ_ck, RANK_SAMPLE_K, self.n)

    def get_candidat_ayas(self, P, k=30, l=10):
        P = condense(P)
        P = self.get_indices(P)
        l = min(l, np.size(P))
        Ps = np.lib.stride_tricks.sliding_window_view(P, window_shape=l)
        Ps = Ps[::l]
        Firsts, Lasts = batch_backward_search(Ps, self.C, self.bwt, self.occ_ck,
                                             RANK_SAMPLE_K, self.n)
        Mt_rows = np.concatenate([np.arange(s, e + 1) for s, e in zip(Firsts, Lasts)])
        aya_ids = self.row_to_ayaid[Mt_rows]
        values, counts = np.unique(aya_ids, return_counts=True)
        # kind="stable" so that ayas tied on vote count keep ascending-id order.
        # np.argsort defaults to an unstable quicksort, which let the top-k set
        # drift between runs on ties - a real (pre-existing) nondeterminism, not
        # just a difference from the dense implementation.
        sorted_idx = np.argsort(-counts, kind="stable")
        top_ayas = sorted_idx[:min(k, len(values))]
        return self.ayaid_to_verse[values[top_ayas]]
    
    def get_aya(self, P, l=10):
        # Getting candidats
        candidats = [0] # dummy initiailisation
        while len(candidats) < 2 and l>4:
            candidats = self.get_candidat_ayas(P, l=l)
            l -= 2
        # intilizing the matcher
        sm = ModifiedMatcher(None, b=P)
        ratios = []
        for cand in candidats:
            text_indices = self.aya_to_index[tuple(cand)]
            text = self.one_string_quran[text_indices[0]:text_indices[1]]
            sm.set_seq1(text)
            ratios.append(sm.ratio())
        indices = np.argsort(ratios)
        best_match = indices[-1]
        second_best = indices[-2] if len(ratios)>2 else best_match - 1
        return candidats[best_match], ratios[best_match], ratios[best_match] - ratios[second_best]

    def verse_to_cursor(self, verse: tuple[int]):
        start, end = self.aya_to_index_uthmani[verse]
        return (start + end) // 2

    def get_fragment(self, cursor, width, push_to_verse=True):
        m = len(self.one_string_uthmani)
        begin, finish = cursor-int(width*0.7), cursor+int(width*0.5)
        if push_to_verse:
            starting_verse = self.aya_at_uthmani(max(begin, 0))
            ending_verse = self.aya_at_uthmani(min(finish, m-1))
            start_idx = self.aya_to_index_uthmani[tuple(starting_verse)][0]
            end_idx = self.aya_to_index_uthmani[tuple(ending_verse)][1]-1
        else:
            start_idx = self.start_word(max(begin, 0))
            end_idx = self.end_word(min(finish, m-1))
        return start_idx, end_idx

    def get_boundaries(self, sm: ModifiedMatcher, min_d: int=2, min_length: int=5):
        """
        After modifying the SequenceMatcher object, this function acts more like a second shield
        """
        # matching_blocks = sm.get_matching_blocks()

        # for i, (ai, bj, size) in enumerate(matching_blocks):
        #     if len(set(sm.a[ai:ai+size])) >= min_length:
        #         start = ai
        #         break
        #     try:
        #         ai_next = matching_blocks[i+1][0]
        #         if ai_next - (ai + size) <= min_d:
        #             start = ai
        #             break
        #     except:
        #         # We arrived to the last block, no other choice left
        #         start = matching_blocks[0][0]
            
        # for i, (ai, bj, size) in enumerate(matching_blocks[-2::-1], start=2):
        #     if len(set(sm.a[ai:ai+size])) >= min_length:
        #         end = ai + size - 1
        #         break
        #     try:
        #         ai_previous = matching_blocks[-i-1][0] + matching_blocks[-i-1][2]
        #         if ai - ai_previous <= min_d:
        #             end = ai + size - 1
        #             break
        #     except:
        #         # We arrived to the last block, no other choice left
        #         end = matching_blocks[-2][0] + matching_blocks[-2][2] - 1

        # return start, end
        pass

    def refined_uthmani(self, tilawa, cursor, width, ref_cursor=None, push_to_verse=True):
        if ref_cursor == None:
            ref_cursor = cursor
        # We compare using the diff library
        start, end = self.get_fragment(cursor, width, push_to_verse=push_to_verse)
        local_cursor = ref_cursor - start
        uthmani_text = self.one_string_uthmani[start:end+1]
        phonetic_script, track = phonetize(uthmani_text)
        index = min(range(len(track)), key=lambda i: (abs(track[i] - local_cursor), -i))
        

        sm = ModifiedMatcher(None, phonetic_script, tilawa)
        
        # matching_blocks = sm.get_matching_blocks()
        # first_match = matching_blocks[0][0]
        # # A word in which we detect one letter is probably not a word intended by the reciter
        # if matching_blocks[-2][2] == 1:
        #     last_match = matching_blocks[-3][0] + matching_blocks[-3][2] - 1
        # else:
        #     last_match = matching_blocks[-2][0] + matching_blocks[-2][2] - 1

        # first_match, last_match = self.get_boundaries(sm)

        matching_blocks = sm.get_matching_blocks(n_span=0, match=(index, "start"))

        if not matching_blocks:
            return start, end
        
        
        first_match, last_match = matching_blocks[0][0], matching_blocks[-1][0] + matching_blocks[-1][2] - 1

        # It is possible that the finder picks only the last haraka of the previous word
        word_start = self.start_word(start + track[first_match])
        word_end = self.end_word(start + track[first_match])
        penetration = (word_end - start - track[first_match]) / (word_end - word_start)

        first_uthmani_word = word_start if penetration > 0.5 else word_end + 1

        # Doing the same for the end
        last_word_start = self.start_word(start + track[last_match])
        last_word_end = self.end_word(start + track[last_match])
        last_penetration = (start + track[last_match] - last_word_start) / (last_word_end - last_word_start)

        last_uthmani_word = last_word_end if last_penetration > 0.4 else last_word_start + 1
        # last_uthmani_word = self.end_word(start + track[last_match])

        return first_uthmani_word, last_uthmani_word
    
    def __call__(self, tilawa):
        # This is the ultimate function that finds the verse in the quran
        aya_idc, _, _ = self.get_aya(tilawa)
        cursor = self.verse_to_cursor(tuple(aya_idc))
        start, end = self.refined_uthmani(tilawa, cursor, int(self.width_factor * len(tilawa)))
        return self.one_string_uthmani[start:end+1]
    
class Corrector:

    def __init__(self, finder=None, cursor=0, attach_lawasiq: bool=False, streaming=True, offset=1):
        if finder == None:
            finder == Finder()
        elif not isinstance(finder, Finder):
            print(f"Finder object expected. Got {type(finder)}.\nUsing default Finder")
            finder == Finder()
        self.finder = finder
        self.cursor = cursor
        self.ref_cursor = 0
        self.settled = False
        self.stops = 0
        self.score = 2
        self.previous_score = 0
        self.local_score = 0
        self.attach_lawasiq = attach_lawasiq
        self.previous_tilawa = ""
        self.previous_results = "", [], []
        self.offset = offset

    def get_color(self, phonetic_script, a0, ai):
        if len(set(phonetic_script[a0:ai])) != 1 or a0 == 0:
            return -1
        # we get rid of the headache of having a0=0 and ai=len(a)
        testing_script = f"{phonetic_script[a0]}" + phonetic_script + f"{phonetic_script[ai-1]}"
        if testing_script[a0] != testing_script[a0+1] and testing_script[ai] != testing_script[ai+1]:
            return -1
        else:
            return 0

    def correct(self, tilawa: str, wasl: bool=False, attach_lawasiq: bool=False, threshold=3):
        """
        the output is two lists: colors and additions.
        for colors : +1 --> correct
                    -1 --> mistake
                    0 --> no enough madd or ghonna
        self.cursor_t stands for temporary cursor
        """
        width = int(self.finder.width_factor * (len(tilawa) + 5)) # an offset is necessary

        ##########################################################################
        # Deciding on the cursor

        w = int((10*np.exp(-self.score) + self.offset)*width)
        start, end = self.finder.refined_uthmani(tilawa, self.cursor, w, self.ref_cursor, push_to_verse=False)
        uthmani_text = self.finder.one_string_uthmani[start:end+1].strip()
        phonetic_script, track = phonetize(uthmani_text, attach_lawasiq=attach_lawasiq)
        sm = ModifiedMatcher(None, phonetic_script, tilawa)

        if not self.settled:

            cursor_ratio = sm.ratio(boarder_penalty=True)

            ########################################################################
            # Global search result 
            aya_idc, score, gap = self.finder.get_aya(tilawa)
            if gap >= 0.2 or len(tilawa) >= 40:

                cursor_t = self.finder.verse_to_cursor(tuple(aya_idc))

                start_t, end_t = self.finder.refined_uthmani(tilawa, cursor_t, width)
                uthmani_text_t = self.finder.one_string_uthmani[start_t:end_t+1].strip()
                phonetic_script_t, track_t = phonetize(uthmani_text_t, attach_lawasiq=attach_lawasiq)
                sm.set_seq1(phonetic_script_t)

                global_score = sm.ratio(boarder_penalty=True)

                if cursor_ratio < global_score:
                    start, end = start_t, end_t
                    uthmani_text = uthmani_text_t
                    phonetic_script, track = phonetic_script_t, track_t
                else:
                    sm.set_seq1(phonetic_script)

        self.cursor = end
        r = sm.ratio(boarder_penalty=True)
        if (not wasl or len(tilawa) > 40) and r > 0:
            self.ref_cursor = end
        elif not self.settled or r < 0:
            self.cursor = self.ref_cursor 
            # uthmani_text = None

        self.previous_score = self.score
        increment = dscore(r, self.local_score)
        self.score = min(2*threshold, self.score + increment)
        self.score = max(0, self.score)
        
        if not wasl and increment>0.1:
            self.stops += 1
        elif increment>0.1:
            self.stops += max(0, len(tilawa) // 70 - len(self.previous_tilawa) // 70)

        if self.score >= threshold:
            self.settled = True
        elif self.stops < 3:
            self.settled = False

        if r < 0:
            return "", [], []

        self.local_score = r

        colors = []
        additions = []
        a0, b0 = 0, 0
        ai, sizea, sizeb = 0, 0, 0 # The dummy case where there is no matching blocks

        for ai, bj, sizea, sizeb in sm.get_matching_blocks():
            if a0 < ai :
                # colors += [self.get_color(phonetic_script, a0, ai)] * (ai-a0)
                colors += [-1] * (ai-a0)
            if b0 < bj :
                additions.append(track[a0])
            rep_a = [sum(1 for _ in g) for _, g in groupby(sm.a[ai:ai+sizea])]
            rep_b = [sum(1 for _ in g) for _, g in groupby(sm.b[bj:bj+sizeb])]
            colors += [
                int(rep_a[ind] <= rep_b[ind])
                for ind in range(len(rep_a))
                for _ in range(rep_a[ind])
            ]
            a0 = ai + sizea
            b0 = bj + sizeb
        if ai+sizea != len(phonetic_script):
            if wasl:
                colors += [2] * (len(phonetic_script)-ai-sizea)
            else:
                colors += [-1] * (len(phonetic_script)-ai-sizea)
        
        # Transforming phonetic correction into uthmani one
        uth_colors = [3] * len(uthmani_text)
        for i, color in enumerate(colors):
            uth_colors[track[i]] = min(uth_colors[track[i]], color)
        
        # Handling the letters that disapear in the phonetic script
        idx = 0
        for value, grp in groupby(uth_colors):
            grp_len = len(list(grp))
            next_idx = idx + grp_len
            if value == 3:
                previous = -1 if idx==0 else uth_colors[idx-1]
                next = -1 if next_idx==len(uth_colors) else uth_colors[next_idx]
                uth_colors[idx:next_idx] = [max(previous, next)] * (next_idx-idx)
            idx = next_idx

        self.previous_tilawa = tilawa
        self.previous_results = uthmani_text, uth_colors, additions

        return uthmani_text, uth_colors, additions
    
    def get_aya(self, tilawa):

        if self.settled:
            verse = self.finder.aya_at_uthmani(self.cursor)
            return np.array([int(verse[0]), int(verse[1])]), self.score
        
        return self.finder.get_aya(tilawa)
        
    
    def __call__(self, tilawa, wasl: bool=False, force=False):
        uthmani_text, colors, additions = self.correct(tilawa, wasl=wasl)
        display_text = ""
        # if (self.score < 5.8 and (self.score - self.previous_score) <= 0) and not force:
        #     return display_text
        for i, letter in enumerate(uthmani_text):
            if colors[i] == 1:
                display_text += "\033[32m" + letter + "\033[0m"
            elif colors[i] == -1:
                display_text += "\033[31m" + letter + "\033[0m"
            elif colors[i] == 0:
                display_text += "\033[33m" + letter + "\033[0m"
            else:
                display_text += letter
        return display_text