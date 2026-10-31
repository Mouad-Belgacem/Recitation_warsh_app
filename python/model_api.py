import json
import numpy as np
import kaldi_native_fbank as knf
import onnxruntime as ort


class Transcriber:
    def __init__(self, model_path="comp_graph.onnx", meta_path="meta_data.json", vocab_path="vocab.json"):
        with open(meta_path) as f:
            meta = json.load(f)
        with open(vocab_path) as f:
            self.id_to_token = {v: k for k, v in json.load(f).items()}

        self.sample_rate = meta["sample_rate"]
        self.num_mel_bins = meta["num_mel_bins"]
        self.chunk_size = meta["chunk_size"]
        self.pad_length = meta["pad_length"]
        self.commit_frames = meta["commit_frames"]
        self.blank_id = meta["blank_id"]
        self.num_states = meta["num_state_tensors"]
        self.log_eps = meta["log_eps"]
        self.state_shapes = meta["state_shapes"]
        self.fbank_cfg = meta["fbank"]

        so = ort.SessionOptions()
        so.log_severity_level = 3
        self.sess = ort.InferenceSession(model_path, so, providers=["CPUExecutionProvider"])
        self._input_dtypes = {i.name: i.type for i in self.sess.get_inputs()}
        self._np_dtype = {
            "tensor(float)": np.float32, "tensor(float16)": np.float16,
            "tensor(int64)": np.int64, "tensor(int32)": np.int32,
        }

        self._reset()

    def _reset(self):
        self.fbank = self._make_fbank()
        self.read_ptr = -self.pad_length
        self.states = [np.zeros(s, dtype=np.int32 if i == self.num_states - 1 else np.float32)
                       for i, s in enumerate(self.state_shapes)]
        self.token_ids = []
        self.spec_ids = []
        self.prev_label = None

    def _make_fbank(self):
        fb = self.fbank_cfg
        opts = knf.FbankOptions()
        opts.frame_opts.samp_freq = self.sample_rate
        opts.frame_opts.dither = fb["dither"]
        opts.frame_opts.snip_edges = fb["snip_edges"]
        opts.frame_opts.window_type = fb["window_type"]
        opts.frame_opts.preemph_coeff = fb["preemph_coeff"]
        opts.frame_opts.remove_dc_offset = fb["remove_dc_offset"]
        opts.frame_opts.round_to_power_of_two = fb["round_to_power_of_two"]
        opts.mel_opts.num_bins = self.num_mel_bins
        opts.mel_opts.high_freq = fb["high_freq"]
        opts.mel_opts.low_freq = fb["low_freq"]
        return knf.OnlineFbank(opts)

    def _frame_at(self, index):
        if 0 <= index < self.fbank.num_frames_ready:
            return np.array(self.fbank.get_frame(index), dtype=np.float32)
        return np.full(self.num_mel_bins, self.log_eps, dtype=np.float32)

    def _run_window(self, start):
        window_len = self.commit_frames + self.pad_length
        frames = np.stack([self._frame_at(start + i) for i in range(window_len)])
        x = frames[np.newaxis].astype(self._cast("x"))
        x_lens = np.array([window_len], dtype=self._cast("x_lens"))

        feeds = {"x": x, "x_lens": x_lens}
        for i in range(self.num_states):
            name = f"state_{i}"
            feeds[name] = self.states[i].astype(self._cast(name))

        outs = self.sess.run(None, feeds)
        log_probs = outs[0].astype(np.float32)
        out_len = int(outs[1][0])

        pred_ids = log_probs[0, :out_len].argmax(axis=1).tolist()
        self._ctc_append(pred_ids)
        self.states = list(outs[2:])

    def _run_speculative(self):
        self.spec_ids = []
        tail = self.fbank.num_frames_ready - (self.read_ptr + self.pad_length)
        tail -= tail % 2
        if tail < 2:
            return

        window_len = self.commit_frames + self.pad_length
        frames = np.stack([self._frame_at(self.read_ptr + i) for i in range(window_len)])
        x = frames[np.newaxis].astype(self._cast("x"))
        x_lens = np.array([window_len], dtype=self._cast("x_lens"))

        feeds = {"x": x, "x_lens": x_lens}
        for i in range(self.num_states):
            name = f"state_{i}"
            feeds[name] = self.states[i].astype(self._cast(name))

        outs = self.sess.run(None, feeds)
        log_probs = outs[0].astype(np.float32)
        out_len = int(outs[1][0])

        keep = min(tail // 4, out_len)
        pred_ids = log_probs[0, :keep].argmax(axis=1).tolist()
        prev = self.prev_label
        for p in pred_ids:
            if p != prev and p != self.blank_id:
                self.spec_ids.append(p)
            prev = p

    def _cast(self, name):
        return self._np_dtype[self._input_dtypes[name]]

    def _ctc_append(self, pred_ids):
        for p in pred_ids:
            if p != self.prev_label and p != self.blank_id:
                self.token_ids.append(p)
            self.prev_label = p

    def push(self, chunk):
        self.fbank.accept_waveform(self.sample_rate, chunk.tolist())
        while self.fbank.num_frames_ready - self.read_ptr >= self.commit_frames + self.pad_length:
            self._run_window(self.read_ptr)
            self.read_ptr += self.commit_frames
        self._run_speculative()

    def read(self):
        return "".join(self.id_to_token.get(i, "") for i in self.token_ids + self.spec_ids)
