const HARAKAT = ["َ", "ِ", "ُ"];
const huruf = [
  "ا","ب","ت","ث","ج","ح","خ","د",
  "ذ","ر","ز","س","ش","ص","ض","ط",
  "ظ","ع","غ","ف","ق","ك","ل","م",
  "ن","ه","و","ي","ء","۽","$","@","*","a","£"
];
const WHITESPACE = [" ", "\t", "\n", "\r"];

function getNextCaracter(index, text) {
  if (index === null || index === undefined) return [null, null];
  if (index + 1 < text.length) return [text[index + 1], index + 1];
  return [null, null];
}

function getNextHarf(index, text) {
  if (index === null || index === undefined) return [null, null];
  for (let i = index + 1; i < text.length; i++) {
    if (huruf.includes(text[i])) return [text[i], i];
  }
  return [null, null];
}

function getNextHarfInSameWord(index, text) {
  if (index === null || index === undefined) return [null, null];
  for (let i = index + 1; i < text.length; i++) {
    if (WHITESPACE.includes(text[i])) break;
    if (huruf.includes(text[i])) return [text[i], i];
  }
  return [null, null];
}

function getPreviousHarfInSameWord(index, text) {
  if (index === null || index === undefined) return [null, null];
  for (let i = index - 1; i >= 0; i--) {
    if (WHITESPACE.includes(text[i])) break;
    if (huruf.includes(text[i])) return [text[i], i];
  }
  return [null, null];
}

function getPreviousHaraka(index, text) {
  if (index === null || index === undefined) return null;
  if (index - 1 >= 0 && HARAKAT.includes(text[index - 1])) return text[index - 1];
  return null;
}

function isSakin(index, text) {
  const [nextChar] = getNextCaracter(index, text);
  if (index === null || index === undefined) return false;
  if (!huruf.includes(text[index])) return false;
  if (nextChar === "$") return true;
  if ((huruf.includes(nextChar) || nextChar === " ") && !HARAKAT.includes(nextChar)) return true;
  return false;
}

function getPreviousHarf(index, text) {
  if (index === null || index === undefined) return [null, null];
  for (let i = index - 1; i >= 0; i--) {
    if (huruf.includes(text[i])) return [text[i], i];
  }
  return [null, null];
}

function safeHarakaAt(idx, text) {
  if (idx === null || idx === undefined || idx >= text.length) return null;
  return HARAKAT.includes(text[idx]) ? text[idx] : null;
}

module.exports = {
  HARAKAT, huruf, WHITESPACE,
  getNextCaracter, getNextHarf, getNextHarfInSameWord,
  getPreviousHarfInSameWord, getPreviousHaraka, isSakin,
  getPreviousHarf, safeHarakaAt,
};
