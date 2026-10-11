const {
  getNextCaracter, getNextHarf, getNextHarfInSameWord,
  getPreviousHaraka, getPreviousHarf, getPreviousHarfInSameWord,
  isSakin, safeHarakaAt,
} = require("./utils");
const { QiraatConfig, WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID } = require("./qiraat_config");

function buildHandlers(cfg = WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID) {

  function handleSmallWaw(index, text) {
    let res = "";
    const [nxtH] = getNextHarf(index, text);
    const [nxtHSameWord, idxNxtHSameWord] = getNextHarfInSameWord(index, text);
    const [prevHSameWord] = getPreviousHarfInSameWord(index, text);
    const prevHaraka = getPreviousHaraka(index, text);
    const prevThree = index - 3 >= 0 ? text.slice(index - 3, index) : null;
    const prevTwo = index - 2 >= 0 ? text.slice(index - 2, index) : null;

    if (text[index - 1] === " ") {
      if (text[index - 3] === "ء") return ["ۥ".repeat(2), 1];
      return ["ۥ".repeat(cfg.madd_badal), 1];
    }
    if (prevThree === "اِ۟") return ["ۥ".repeat(2), 1];
    if (prevTwo === "ا۟") return ["ۥ".repeat(cfg.madd_badal), 1];

    if (prevHaraka !== "ُ") return ["", 1];

    if (nxtHSameWord !== null) {
      if (nxtHSameWord === "@") res = "ۥ".repeat(2);
      else if (nxtHSameWord === "ء" || nxtHSameWord === "۽") res = "ۥ".repeat(cfg.madd_muttasil);
      else if (getNextCaracter(idxNxtHSameWord, text)[0] === "$") res = "ۥ".repeat(cfg.madd_arid);
      else if (isSakin(index + 1, text)) res = "ۥ".repeat(cfg.madd_lazim);
      else if (prevHSameWord === "ء" || prevHSameWord === "۽") res = "ۥ".repeat(cfg.madd_badal);
      else res = "ۥ".repeat(2);
    } else {
      if (nxtH === "ء") res = "ۥ".repeat(cfg.madd_munfasil);
      else if (isSakin(getNextHarf(index, text)[1], text)) res = "";
      else res = "ۥ".repeat(2);
    }
    return [res, 1];
  }

  function handleWaw(index, text) {
    const prevHaraka = getPreviousHaraka(index, text);
    const [nxtH, idxNxtH] = getNextHarf(index, text);

    if (isSakin(index, text) && index - 2 >= 0 && text.slice(index - 2, index) === "ُ ") {
      return ["ۥ".repeat(cfg.madd_badal), 1];
    }

    if (isSakin(index, text)) {
      if (nxtH === text[index] && isSakin(idxNxtH, text))
        return [text[index], idxNxtH - index + 1];
      if (nxtH === text[index] && !isSakin(idxNxtH, text))
        return [text[index], 1];
      if (nxtH === "ء" && prevHaraka === "َ")
        return ["و".repeat(cfg.madd_leen), 1];
      if (index + 2 < text.length && prevHaraka === "َ") {
        if (text[index + 2] === "$") return ["و".repeat(cfg.madd_leen), 1];
      } else {
        return ["و", 1];
      }
    }
    return ["و", 1];
  }

  function handleYah(index, text) {
    const prevHaraka = getPreviousHaraka(index, text);
    const [nxtH] = getNextHarf(index, text);
    const [prevHarf, idxPrevHarf] = getPreviousHarf(index, text);
    const harakaPrevHarf = safeHarakaAt(idxPrevHarf !== null ? idxPrevHarf + 1 : null, text);
    const prevThree = index - 3 >= 0 ? text.slice(index - 3, index) : null;

    if (["اُ۪", "اِ۪", "اَ۪"].includes(prevThree)) return ["ے".repeat(2), 1];

    if (index - 1 >= 0 && text[index - 1] === " ") {
      if (isSakin(index, text)) {
        if (prevHarf === "ا") return ["ا".repeat(2), 1];
        if (harakaPrevHarf === "َ" && nxtH === "ت") return ["ا".repeat(2), 1];
        if (harakaPrevHarf === "ِ" && nxtH === "ت") return ["ے".repeat(2), 1];
        if (harakaPrevHarf === "ُ") return ["ۥ".repeat(2), 1];
        return ["ي", 1];
      }
    }

    if (prevHaraka === "َ" && isSakin(index, text)) {
      if (nxtH === "ء") return ["ي".repeat(cfg.madd_leen), 1];
      if (isSakin(index + 1, text)) return ["ي".repeat(cfg.madd_leen), 1];
    }
    return ["ي", 1];
  }

  function handleYahMaddiya(index, text) {
    const [nxtH] = getNextHarf(index, text);
    const [prevHInSameWord] = getPreviousHarfInSameWord(index, text);
    const [nxtHSameWord, idxNxtHSameWord] = getNextHarfInSameWord(index, text);

    if (nxtHSameWord !== null) {
      if (nxtHSameWord === "£") return ["ے".repeat(6), 2];
      if (nxtHSameWord === "@") {
        if (isSakin(getNextHarfInSameWord(idxNxtHSameWord, text)[1], text))
          return ["ے".repeat(cfg.madd_arid), 2];
        return ["ے".repeat(2), 2];
      }
      if (nxtHSameWord === "*") return [text[index].repeat(cfg.madd_badal), 2];
      if (nxtHSameWord === "ء") return ["ے".repeat(cfg.madd_muttasil), 1];
      if (isSakin(idxNxtHSameWord, text)) {
        if (getNextCaracter(idxNxtHSameWord, text)[0] === "$")
          return [text[index].repeat(cfg.madd_arid), 1];
        return ["ے".repeat(cfg.madd_lazim), 1];
      }
      if (nxtHSameWord === "ء" || nxtHSameWord === "۽") return ["ے".repeat(cfg.madd_muttasil), 1];
      if (prevHInSameWord === "ء" || prevHInSameWord === "۽") return ["ے".repeat(cfg.madd_badal), 1];
      return ["ے".repeat(2), 1];
    }

    if (nxtH === "ء") return ["ے".repeat(cfg.madd_munfasil), 1];
    if (prevHInSameWord === "ء") return ["ے".repeat(cfg.madd_badal), 1];
    if (isSakin(getNextHarf(index, text)[1], text)) {
      if (nxtH === "و") return ["ے".repeat(2), 3];
      return ["", 1];
    }
    return ["ے".repeat(2), 1];
  }

  function handleAnd(index, text) {
    return ["ا".repeat(cfg.madd_badal), 2];
  }

  function handlePlus(index, text) {
    return ["ے".repeat(6), 2];
  }

  function handleChapeau(index, text) {
    const [nxtChar] = getNextCaracter(index, text);
    if (["ا", "ۥ", "ے"].includes(nxtChar))
      return [nxtChar.repeat(cfg.madd_badal), 2];
    return ["", 1];
  }

  function handleAlif(index, text) {
    const prevHaraka = getPreviousHaraka(index, text);
    const [nxtH, idxNxtH] = getNextHarf(index, text);
    const [prevHarf] = getPreviousHarfInSameWord(index, text);
    const [nxtChar] = getNextCaracter(index, text);
    const [nextHSameWord, idxNextHSameWord] = getNextHarfInSameWord(index, text);

    if (prevHarf === "a") return ["ا".repeat(cfg.madd_lazim), 1];

    if (["ف", "و", "ك"].includes(prevHarf)) {
      if (isSakin(idxNextHSameWord, text)) {
        if (index + 2 < text.length && text[index + 2] === "$") return ["ا".repeat(cfg.madd_arid), 1];
        if (nextHSameWord !== "ف") return ["", 1];
      } else {
        if (["ف", "ك"].includes(prevHarf) && text.slice(index + 1, index + 3) === "لَ")
          return ["", 1];
      }
    }

    const mapPoint = { "۬": "َ", "۪": "ِ", "۟": "ُ" };

    if (prevHaraka !== "َ" && prevHaraka !== null) return ["", 1];

    if (text[index - 1] === "$") {
      if (mapPoint[text[index + 2]]) return ["ء" + mapPoint[text[index + 2]], 3];
      if (["َ", "ُ", "ِ"].includes(text[index + 1])) return ["ء" + text[index + 1], 2];
      if (mapPoint[text[index + 1]]) return ["ء" + mapPoint[text[index + 1]], 2];
      if (text[index + 1] === "ٰ") {
        if (isSakin(idxNextHSameWord, text))
          return ["ءَ" + "ا".repeat(cfg.madd_lazim), 2];
        return ["ءَ" + "ا".repeat(cfg.madd_badal), 2];
      }
      return [text.slice(index, idxNextHSameWord), idxNextHSameWord - index];
    }

    if (nextHSameWord !== null) {
      if (nextHSameWord === "$") return ["ا".repeat(2), 1];
      if (nextHSameWord === "@") return ["ا".repeat(2), 2];
      if (nextHSameWord === "ء" || nextHSameWord === "۽") return ["ا".repeat(cfg.madd_muttasil), 1];
      if (isSakin(idxNextHSameWord, text)) {
        if (text[index + 1] === "ٰ") return ["ا".repeat(cfg.madd_lazim), 2];
        if (text[index + 1] === "۟") return ["", 2];
        if (getNextCaracter(idxNextHSameWord, text)[0] === "$")
          return [text[index].repeat(cfg.madd_arid), 1];
        return ["ا".repeat(cfg.madd_lazim), 1];
      }
      if (prevHarf === "ء" || prevHarf === "۽") return ["ا".repeat(cfg.madd_badal), 1];
      if (text[index + 1] === "ٰ") return ["ا".repeat(cfg.madd_badal), 2];
      return ["ا".repeat(2), 1];
    }

    if (isSakin(idxNxtH, text)) return ["", 1];
    if (nxtH === "ء" || nxtH === "۽") return ["ا".repeat(cfg.madd_munfasil), 1];
    if (nxtChar === "ٰ") return ["ا".repeat(cfg.madd_badal), 2];
    if (prevHarf === "ء" || prevHarf === "۽") return ["ا".repeat(cfg.madd_badal), 1];
    return ["ا".repeat(2), 1];
  }

  const hurufIkhfaa = ["ت","ث","ج","د","ذ","ز","س","ش","ص","ض","ط","ظ","ك","ف","ق"];
  const hurufIdghamKamil = ["م", "ن"];
  const hurufIdghamNakis = ["و", "ي"];
  const hurufIdghamWithoutGunnah = ["ل", "ر"];

  function handleNoon(index, text) {
    const [nxtH, idxNxtH] = getNextHarf(index, text);
    const [nxtHSameWord] = getNextHarfInSameWord(index, text);

    if (!isSakin(index, text)) return ["ن", 1];

    if (nxtHSameWord !== null) {
      if (nxtHSameWord === "ن") return ["ن".repeat(4), 2];
      if (hurufIkhfaa.includes(nxtHSameWord)) return ["ںں", 1];
      if (hurufIdghamNakis.includes(nxtHSameWord)) return ["ن", 1];
      if (nxtHSameWord === "ب") return ["۾۾", 1];
      return ["ن", 1];
    }

    if (hurufIkhfaa.includes(nxtH)) return ["ںں", 1];
    if (hurufIdghamKamil.includes(nxtH)) return [nxtH.repeat(4), 4];
    if (hurufIdghamNakis.includes(nxtH)) return [nxtH.repeat(3), 3];
    if (hurufIdghamWithoutGunnah.includes(nxtH)) return ["", 1];
    if (nxtH === "ب") return ["۾۾", 2];
    return ["ن", 1];
  }

  function handleMim(index, text) {
    const [nextH] = getNextHarf(index, text);
    const [nextHSameWord] = getNextHarfInSameWord(index, text);

    if (!isSakin(index, text)) return ["م", 1];

    if (nextHSameWord !== null) {
      if (nextHSameWord === "م") return ["م".repeat(4), 2];
      if (nextHSameWord === "ب") return ["۾۾", 1];
      return ["م", 1];
    }

    if (nextH === "ب") return ["۾۾", 1];
    if (nextH === "م") return ["م".repeat(4), 4];
    return ["م", 1];
  }

  const hurufQalqala = ["ق", "ب", "ج"];

  function handleQalqalaNormal(index, text) {
    const [nextH, idxNextH] = getNextHarf(index, text);
    if (isSakin(index, text)) {
      if (nextH === text[index] && isSakin(idxNextH, text))
        return [text[index], idxNextH - index + 1];
      if (nextH === text[index] && !isSakin(idxNextH, text))
        return [text[index], 1];
      return [text[index] + "چ", 1];
    }
    return [text[index], 1];
  }

  function handleDal(index, text) {
    const [nextH, idxNextH] = getNextHarf(index, text);
    if (isSakin(index, text) && ["ت", "ظ", "ض"].includes(nextH)) return ["", 1];
    if (isSakin(index, text)) {
      if (nextH === text[index] && isSakin(idxNextH, text))
        return [text[index], idxNextH - index + 1];
      if (nextH === text[index] && !isSakin(idxNextH, text))
        return [text[index], 1];
      return ["د" + "چ", 1];
    }
    return ["د", 1];
  }

  function handleTha(index, text) {
    const [nextH, idxNextH] = getNextHarf(index, text);
    if (isSakin(index, text) && nextH === "ت") return ["ڟ", 1];
    if (isSakin(index, text)) {
      if (nextH === text[index] && isSakin(idxNextH, text))
        return [text[index], idxNextH - index + 1];
      if (nextH === text[index] && !isSakin(idxNextH, text))
        return [text[index], 1];
      return ["ط" + "چ", 1];
    }
    return ["ط", 1];
  }

  function handleTa(index, text) {
    const [nextH, idxNextH] = getNextHarf(index, text);
    if (isSakin(index, text)) {
      if (["ط", "د", "ظ"].includes(nextH)) return ["", 1];
      if (nextH === text[index] && isSakin(idxNextH, text))
        return [text[index], idxNextH - index + 1];
      return [text[index], 1];
    }
    return ["ت", 1];
  }

  function handleDhal(index, text) {
    const [nextH, idxNextH] = getNextHarf(index, text);
    if (isSakin(index, text)) {
      if (nextH === "ظ") return ["", 1];
      if (nextH === text[index] && isSakin(idxNextH, text))
        return [text[index], idxNextH - index + 1];
      return [text[index], 1];
    }
    return [text[index], 1];
  }

  function handleLam(index, text) {
    const [nextH] = getNextHarf(index, text);
    const [nextHSameWord] = getNextHarfInSameWord(index, text);

    if (isSakin(index, text)) {
      if (nextHSameWord !== null) return ["ل", 1];
      if (nextH === "ل" || nextH === "ر") return ["", 2];
      return ["ل", 1];
    }
    return ["ل", 1];
  }

  const hurufMutamatilan = ["ث","ح","خ","ر","ز","س","ش","ص","ض","ظ","ع","غ","ف","ك"];

  function handleMutamatilan(index, text) {
    const [nextHarf, idxNextHarf] = getNextHarf(index, text);
    if (isSakin(index, text)) {
      if (nextHarf === text[index] && isSakin(idxNextHarf, text))
        return [text[index], idxNextHarf - index + 1];
      return [text[index], 1];
    }
    return [text[index], 1];
  }

  const standardChars = ["ه", "ِ", "َ", "۪", "ء", "", "ُ", "۽"];
  function handleStandardChar(index, text) { return [text[index], 1]; }

  const toRemove = ["@", "۟", "$", "۬", "ٰ", " ", "s", "a", "£"];
  function handleRemove() { return ["", 1]; }

  const getHandler = {};
  const map = {
    "و": handleWaw, "ۥ": handleSmallWaw, "ي": handleYah,
    "ا": handleAlif, "ٛ": handleChapeau, "ے": handleYahMaddiya,
    "ن": handleNoon, "م": handleMim, "د": handleDal,
    "ط": handleTha, "ت": handleTa, "ذ": handleDhal,
    "ل": handleLam, "&": handleAnd, "+": handlePlus,
  };
  Object.assign(getHandler, map);
  for (const k of standardChars) getHandler[k] = handleStandardChar;
  for (const k of toRemove) getHandler[k] = handleRemove;
  for (const k of hurufQalqala) getHandler[k] = handleQalqalaNormal;
  for (const k of hurufMutamatilan) getHandler[k] = handleMutamatilan;

  return getHandler;
}

module.exports = { buildHandlers };
