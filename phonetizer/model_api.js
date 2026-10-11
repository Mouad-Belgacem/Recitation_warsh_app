const ort = require("onnxruntime-node");
const fs = require("fs");

// --- Streaming Fbank (port of kaldi-native-fbank) ---

class StreamingFbank {
  constructor(cfg, sampleRate, numMelBins) {
    this.sampleRate = sampleRate;
    this.numMelBins = numMelBins;
    this.frameLength = Math.round(sampleRate * 0.025); // 400
    this.frameShift = Math.round(sampleRate * 0.01); // 160
    this.fftSize = nextPow2(this.frameLength); // 512
    this.preemphCoeff = cfg.preemph_coeff;
    this.removeDcOffset = cfg.remove_dc_offset;
    this.lowFreq = cfg.low_freq;
    this.highFreq = cfg.high_freq < 0 ? sampleRate / 2 + cfg.high_freq : cfg.high_freq;

    this.window = makeWindow(cfg.window_type, this.frameLength);
    this.melFilters = makeMelFilters(numMelBins, this.fftSize, sampleRate, this.lowFreq, this.highFreq);

    this.samples = [];
    this.frames = [];
  }

  acceptWaveform(samples) {
    for (let i = 0; i < samples.length; i++) this.samples.push(samples[i]);
    this._extract();
  }

  get numFramesReady() {
    return this.frames.length;
  }

  getFrame(index) {
    return this.frames[index];
  }

  _extract() {
    const n = this.samples.length;
    while (true) {
      const start = this.frames.length * this.frameShift + Math.floor(this.frameShift / 2) - Math.floor(this.frameLength / 2);
      if (start + this.frameLength > n) break;

      const raw = new Float32Array(this.frameLength);
      for (let i = 0; i < this.frameLength; i++) {
        let idx = start + i;
        while (idx < 0 || idx >= n) {
          if (idx < 0) idx = -idx - 1;
          else idx = 2 * n - 1 - idx;
        }
        raw[i] = this.samples[idx];
      }

      if (this.removeDcOffset) {
        let sum = 0;
        for (let i = 0; i < raw.length; i++) sum += raw[i];
        const mean = sum / raw.length;
        for (let i = 0; i < raw.length; i++) raw[i] -= mean;
      }

      if (this.preemphCoeff > 0) {
        for (let i = raw.length - 1; i > 0; i--) {
          raw[i] -= this.preemphCoeff * raw[i - 1];
        }
        raw[0] -= this.preemphCoeff * raw[0];
      }

      for (let i = 0; i < raw.length; i++) raw[i] *= this.window[i];

      const padded = new Float32Array(this.fftSize);
      padded.set(raw);
      const spectrum = rfft(padded);

      const numBins = this.fftSize / 2 + 1;
      const power = new Float32Array(numBins);
      for (let i = 0; i < numBins; i++) {
        power[i] = spectrum[2 * i] * spectrum[2 * i] + spectrum[2 * i + 1] * spectrum[2 * i + 1];
      }

      const melEnergies = new Float32Array(this.numMelBins);
      for (let m = 0; m < this.numMelBins; m++) {
        let sum = 0;
        const filter = this.melFilters[m];
        for (let k = filter.start; k < filter.end; k++) {
          sum += power[k] * filter.weights[k - filter.start];
        }
        melEnergies[m] = Math.log(Math.max(sum, 1.1920929e-7));
      }

      this.frames.push(melEnergies);
    }
  }
}

function nextPow2(n) {
  let p = 1;
  while (p < n) p *= 2;
  return p;
}

function makeWindow(type, length) {
  const w = new Float32Array(length);
  const a = (2 * Math.PI) / (length - 1);
  for (let i = 0; i < length; i++) {
    w[i] = 0.5 - 0.5 * Math.cos(a * i); // Hanning
  }
  if (type === "povey") {
    for (let i = 0; i < length; i++) w[i] = Math.pow(w[i], 0.85);
  }
  return w;
}

function mel(f) {
  return 1127.0 * Math.log(1.0 + f / 700.0);
}

function invMel(m) {
  return 700.0 * (Math.exp(m / 1127.0) - 1.0);
}

function makeMelFilters(numBins, fftSize, sampleRate, lowFreq, highFreq) {
  const numFftBins = fftSize / 2;
  const fftBinWidth = sampleRate / fftSize;
  const lowMel = mel(lowFreq);
  const highMel = mel(highFreq);
  const melDelta = (highMel - lowMel) / (numBins + 1);

  const filters = [];
  for (let m = 0; m < numBins; m++) {
    const leftMel = lowMel + m * melDelta;
    const centerMel = lowMel + (m + 1) * melDelta;
    const rightMel = lowMel + (m + 2) * melDelta;

    let start = numFftBins;
    let end = 0;
    const weights = new Float32Array(numFftBins);

    for (let k = 0; k < numFftBins; k++) {
      const freq = k * fftBinWidth;
      const melFreq = mel(freq);
      let w = 0;
      if (melFreq > leftMel && melFreq < rightMel) {
        if (melFreq <= centerMel) {
          w = (melFreq - leftMel) / (centerMel - leftMel);
        } else {
          w = (rightMel - melFreq) / (rightMel - centerMel);
        }
      }
      if (w > 0) {
        if (k < start) start = k;
        end = k + 1;
      }
      weights[k] = w;
    }

    const trimmed = new Float32Array(end - start);
    for (let k = start; k < end; k++) trimmed[k - start] = weights[k];
    filters.push({ start, end, weights: trimmed });
  }
  return filters;
}

function rfft(x) {
  const n = x.length;
  const re = new Float64Array(n);
  const im = new Float64Array(n);
  for (let i = 0; i < n; i++) re[i] = x[i];
  fftInPlace(re, im);
  const out = new Float64Array((n / 2 + 1) * 2);
  for (let i = 0; i <= n / 2; i++) {
    out[2 * i] = re[i];
    out[2 * i + 1] = im[i];
  }
  return out;
}

function fftInPlace(re, im) {
  const n = re.length;
  let j = 0;
  for (let i = 0; i < n; i++) {
    if (i < j) {
      [re[i], re[j]] = [re[j], re[i]];
      [im[i], im[j]] = [im[j], im[i]];
    }
    let m = n >> 1;
    while (m >= 1 && j >= m) {
      j -= m;
      m >>= 1;
    }
    j += m;
  }
  for (let size = 2; size <= n; size *= 2) {
    const half = size / 2;
    const angle = (-2 * Math.PI) / size;
    const wRe = Math.cos(angle);
    const wIm = Math.sin(angle);
    for (let start = 0; start < n; start += size) {
      let curRe = 1, curIm = 0;
      for (let k = 0; k < half; k++) {
        const a = start + k;
        const b = start + k + half;
        const tRe = curRe * re[b] - curIm * im[b];
        const tIm = curRe * im[b] + curIm * re[b];
        re[b] = re[a] - tRe;
        im[b] = im[a] - tIm;
        re[a] += tRe;
        im[a] += tIm;
        const nextRe = curRe * wRe - curIm * wIm;
        curIm = curRe * wIm + curIm * wRe;
        curRe = nextRe;
      }
    }
  }
}

// --- Transcriber ---

class Transcriber {
  constructor(modelPath="comp_graph.onnx", metaPath="meta_data.json", vocabPath="vocab.json") {
    const meta = JSON.parse(fs.readFileSync(metaPath, "utf-8"));
    const vocab = JSON.parse(fs.readFileSync(vocabPath, "utf-8"));
    this.idToToken = {};
    for (const [token, id] of Object.entries(vocab)) this.idToToken[id] = token;

    this.sampleRate = meta.sample_rate;
    this.numMelBins = meta.num_mel_bins;
    this.padLength = meta.pad_length;
    this.commitFrames = meta.commit_frames;
    this.blankId = meta.blank_id;
    this.numStates = meta.num_state_tensors;
    this.logEps = meta.log_eps;
    this.stateShapes = meta.state_shapes;
    this.fbankCfg = meta.fbank;

    this._modelPath = modelPath;
    this._session = null;
    this._inputDtypes = null;
  }

  async init() {
    this._session = await ort.InferenceSession.create(this._modelPath, {
      logSeverityLevel: 3,
    });
    this._reset();
  }

  _reset() {
    this.fbank = new StreamingFbank(this.fbankCfg, this.sampleRate, this.numMelBins);
    this.readPtr = -this.padLength;
    this.states = this.stateShapes.map((shape, i) => {
      const size = shape.reduce((a, b) => a * b, 1);
      if (i === this.numStates - 1) {
        return new ort.Tensor("int32", new Int32Array(size), shape);
      }
      return new ort.Tensor("float32", new Float32Array(size), shape);
    });
    this.tokenIds = [];
    this.specIds = [];
    this.prevLabel = null;
  }

  _frameAt(index) {
    if (index >= 0 && index < this.fbank.numFramesReady) {
      return this.fbank.getFrame(index);
    }
    const silence = new Float32Array(this.numMelBins);
    silence.fill(this.logEps);
    return silence;
  }

  async _runWindow(start) {
    const windowLen = this.commitFrames + this.padLength;
    const xData = new Float32Array(windowLen * this.numMelBins);
    for (let i = 0; i < windowLen; i++) {
      const frame = this._frameAt(start + i);
      xData.set(frame, i * this.numMelBins);
    }

    const feeds = {
      x: new ort.Tensor("float32", xData, [1, windowLen, this.numMelBins]),
      x_lens: new ort.Tensor("int64", new BigInt64Array([BigInt(windowLen)]), [1]),
    };
    for (let i = 0; i < this.numStates; i++) {
      feeds[`state_${i}`] = this.states[i];
    }

    const results = await this._session.run(feeds);
    const logProbs = results["log_probs"];
    const outLen = Number(results["out_lens"].data[0]);

    const numClasses = logProbs.dims[2];
    const predIds = [];
    for (let t = 0; t < outLen; t++) {
      let best = 0;
      let bestVal = logProbs.data[t * numClasses];
      for (let c = 1; c < numClasses; c++) {
        if (logProbs.data[t * numClasses + c] > bestVal) {
          bestVal = logProbs.data[t * numClasses + c];
          best = c;
        }
      }
      predIds.push(best);
    }

    this._ctcAppend(predIds);

    this.states = this.stateShapes.map((shape, i) => {
      const tensor = results[`new_state_${i}`];
      if (i === this.numStates - 1) {
        return new ort.Tensor("int32", new Int32Array(Array.from(tensor.data, Number)), shape);
      }
      return new ort.Tensor("float32", new Float32Array(tensor.data), shape);
    });
  }

  async _runSpeculative() {
    this.specIds = [];
    let tail = this.fbank.numFramesReady - (this.readPtr + this.padLength);
    tail -= tail % 2;
    if (tail < 2) return;

    const windowLen = this.commitFrames + this.padLength;
    const xData = new Float32Array(windowLen * this.numMelBins);
    for (let i = 0; i < windowLen; i++) {
      const frame = this._frameAt(this.readPtr + i);
      xData.set(frame, i * this.numMelBins);
    }

    const feeds = {
      x: new ort.Tensor("float32", xData, [1, windowLen, this.numMelBins]),
      x_lens: new ort.Tensor("int64", new BigInt64Array([BigInt(windowLen)]), [1]),
    };
    for (let i = 0; i < this.numStates; i++) {
      feeds[`state_${i}`] = this.states[i];
    }

    const results = await this._session.run(feeds);
    const logProbs = results["log_probs"];
    const outLen = Number(results["out_lens"].data[0]);

    const numClasses = logProbs.dims[2];
    const keep = Math.min(Math.floor(tail / 4), outLen);
    const predIds = [];
    for (let t = 0; t < keep; t++) {
      let best = 0;
      let bestVal = logProbs.data[t * numClasses];
      for (let c = 1; c < numClasses; c++) {
        if (logProbs.data[t * numClasses + c] > bestVal) {
          bestVal = logProbs.data[t * numClasses + c];
          best = c;
        }
      }
      predIds.push(best);
    }

    let prev = this.prevLabel;
    for (const p of predIds) {
      if (p !== prev && p !== this.blankId) this.specIds.push(p);
      prev = p;
    }
  }

  _ctcAppend(predIds) {
    for (const p of predIds) {
      if (p !== this.prevLabel && p !== this.blankId) {
        this.tokenIds.push(p);
      }
      this.prevLabel = p;
    }
  }

  async push(chunk) {
    this.fbank.acceptWaveform(chunk);
    while (
      this.fbank.numFramesReady - this.readPtr >=
      this.commitFrames + this.padLength
    ) {
      await this._runWindow(this.readPtr);
      this.readPtr += this.commitFrames;
    }
    await this._runSpeculative();
  }

  read() {
    return [...this.tokenIds, ...this.specIds]
      .map((id) => this.idToToken[id] || "")
      .join("");
  }
}

module.exports = { Transcriber, StreamingFbank };
