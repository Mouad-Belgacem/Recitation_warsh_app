HARAKAT = ["َ", "ِ","ُ"]
huruf=['ا', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي',"ء", "۽","$","@","*","a","£"]
WHITESPACE = [' ', '\t', '\n', '\r']
def get_next_caracter(index, text):
    if index is None:
        return None, None
    if index + 1 < len(text):
        return text[index + 1], index + 1
    return None, None

def get_next_harf(index, text):
    if index is None:
        return None, None
    for i in range(index + 1, len(text)):
        if text[i] in huruf:
            return text[i], i
    return None, None

def get_next_harf_in_same_word(index, text):
    if index is None:
        return None, None
    for i in range(index + 1, len(text)):
        if text[i] in WHITESPACE:
            break
        if text[i] in huruf:
            return text[i], i
    return None, None



def get_previous_harf_in_same_word(index, text):
    if index is None:
        return None, None
    for i in range(index - 1, -1, -1):
        if text[i] in WHITESPACE:
            break
        if text[i] in huruf:
            return text[i], i
    return None, None

def get_previous_haraka(index, text):
    if index is None:
        return None
    if index - 1 >= 0 and text[index - 1] in HARAKAT:
        return text[index - 1]
    return None

def is_sakin(index, text):
    """Vérifie si la lettre porte un Soukoun ou n'a pas de voyelle."""
    # Dans le Mushaf, une lettre sans haraka est souvent Sakina (ex: Idgham)
    # On regarde les caractères entre cette lettre et la suivante
    # next_char = text[index + 1] if index + 1 < len(text) else None
    next_char, idx_nxt_car = get_next_caracter(index, text)
    if index is None:
        return False
    if text[index] not in huruf:
        return False  # Si ce n'est pas une lettre, on ne considère pas ça comme sakin
    if next_char=="$":
        return True  # 
    if (next_char in huruf or next_char==" ") and  next_char not in HARAKAT: # Pas de voyelle du tout
        return True
    return False

def get_previous_harf(index, text):
    if index is None:
        return None, None
    for i in range(index - 1, -1, -1):
        if text[i] in huruf:
            return text[i], i
    return None, None

def safe_haraka_at(idx, text):
    """Retourne la haraka à text[idx] si elle existe, sinon None."""
    if idx is None or idx >= len(text):
        return None
    return text[idx] if text[idx] in HARAKAT else None