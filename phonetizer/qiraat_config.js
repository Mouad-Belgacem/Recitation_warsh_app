class QiraatConfig {
  constructor({
    madd_tabi3i = 2,
    madd_badal = 4,
    madd_arid = 6,
    madd_muttasil = 6,
    madd_munfasil = 6,
    madd_leen = 4,
    madd_lazim = 6,
    madd_iwad = 2,
  } = {}) {
    this.madd_tabi3i = madd_tabi3i;
    this.madd_badal = madd_badal;
    this.madd_arid = madd_arid;
    this.madd_muttasil = madd_muttasil;
    this.madd_munfasil = madd_munfasil;
    this.madd_leen = madd_leen;
    this.madd_lazim = madd_lazim;
    this.madd_iwad = madd_iwad;
  }
}

const WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID = new QiraatConfig({
  madd_badal: 4,
  madd_arid: 6,
  madd_muttasil: 6,
  madd_munfasil: 6,
  madd_leen: 4,
});

const WARSH_TAWASOT_ALBADAL_TAWASOT_ALARID = new QiraatConfig({
  madd_badal: 4,
  madd_arid: 4,
  madd_muttasil: 6,
  madd_munfasil: 6,
  madd_leen: 4,
});

const WARSH_TAWASOT_ALBADAL_QASR_ALARID = new QiraatConfig({
  madd_badal: 4,
  madd_arid: 2,
  madd_muttasil: 6,
  madd_munfasil: 6,
  madd_leen: 4,
});

const WARSH_QASR_ALBADAL_ICHBAA_ALARID = new QiraatConfig({
  madd_badal: 2,
  madd_arid: 6,
  madd_muttasil: 6,
  madd_munfasil: 6,
  madd_leen: 4,
});

const WARSH_QASR_ALBADAL_TAWASOT_ALARID = new QiraatConfig({
  madd_badal: 2,
  madd_arid: 4,
  madd_muttasil: 6,
  madd_munfasil: 6,
  madd_leen: 4,
});

const WARSH_QASR_ALBADAL_QASR_ALARID = new QiraatConfig({
  madd_badal: 2,
  madd_arid: 2,
  madd_muttasil: 6,
  madd_munfasil: 6,
  madd_leen: 4,
});

module.exports = {
  QiraatConfig,
  WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID,
  WARSH_TAWASOT_ALBADAL_TAWASOT_ALARID,
  WARSH_TAWASOT_ALBADAL_QASR_ALARID,
  WARSH_QASR_ALBADAL_ICHBAA_ALARID,
  WARSH_QASR_ALBADAL_TAWASOT_ALARID,
  WARSH_QASR_ALBADAL_QASR_ALARID,
};
