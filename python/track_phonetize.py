#This is a high-level structure of how we can process the phonetic text based on the rules we have defined for the characters. We will need to implement the helper functions to get the necessary information about the characters and their context in the text.
from bab_alhuruf import build_handlers
from qiraat_config import WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID
from itertools import repeat

Huruf_qalqala_normal=['ق', 'ب', 'ج']

def process_phonetic_text(input_text, track, cfg=None):
    if cfg is None:
        cfg = WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID
    
    Get_Handler = build_handlers(cfg)   # ← on construit les handlers avec le config
    
    Text_fragments = []
    idx = 0
    length = len(input_text)
    new_track = []

    while idx < length:
        char = input_text[idx]
        handler = Get_Handler.get(char)
        if handler is None:
            Text_fragments.append(char)
            new_track.append(track[idx])
            idx += 1
            continue
        res, consumed = handler(idx, input_text)
        Text_fragments.append(res)
        new_track.extend(repeat(track[idx], len(res)))
        idx += consumed

    return "".join(Text_fragments), new_track