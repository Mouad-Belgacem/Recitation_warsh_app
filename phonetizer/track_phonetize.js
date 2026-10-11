const { buildHandlers } = require("./bab_alhuruf");
const { WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID } = require("./qiraat_config");

function processPhoneticText(inputText, track, cfg = null) {
  if (cfg === null) cfg = WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID;

  const getHandler = buildHandlers(cfg);
  const fragments = [];
  let idx = 0;
  const length = inputText.length;
  const newTrack = [];

  while (idx < length) {
    const char = inputText[idx];
    const handler = getHandler[char];
    if (!handler) {
      fragments.push(char);
      newTrack.push(track[idx]);
      idx += 1;
      continue;
    }
    const [res, consumed] = handler(idx, inputText);
    fragments.push(res);
    for (let k = 0; k < res.length; k++) newTrack.push(track[idx]);
    idx += consumed;
  }

  return [fragments.join(""), newTrack];
}

module.exports = { processPhoneticText };
