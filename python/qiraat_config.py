# qiraat_config.py

class QiraatConfig:
    def __init__(
        self,
        madd_tabi3i:int=2,
        madd_badal: int = 4,          # Warsh: 2, 4 ou 6
        madd_arid: int = 6,           # Warsh: 2, 4 ou 6
        madd_muttasil: int = 6,       # Warsh: 6
        madd_munfasil: int = 6,       # Warsh: 6
        madd_leen: int = 4,           #  4 
        madd_lazim: int = 6,          # fixe en général mais variable selon riwaya
        madd_iwad: int = 2,           # fixe
    ):
        self.madd_tabi3i   = madd_tabi3i
        self.madd_badal    = madd_badal
        self.madd_arid     = madd_arid
        self.madd_muttasil = madd_muttasil
        self.madd_munfasil = madd_munfasil
        self.madd_leen     = madd_leen
        self.madd_lazim    = madd_lazim
        self.madd_iwad     = madd_iwad

# Profils prédéfinis
WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID= QiraatConfig(
    madd_badal=4,       # Hafs: badal n'existe pas, alif normale
    madd_arid=6,
    madd_muttasil=6,
    madd_munfasil=6,
    madd_leen=4,
)

WARSH_TAWASOT_ALBADAL_TAWASOT_ALARID = QiraatConfig(
    madd_badal=4,
    madd_arid=4,
    madd_muttasil=6,
    madd_munfasil=6,
    madd_leen=4,
)

WARSH_TAWASOT_ALBADAL_QASR_ALARID = QiraatConfig(
    madd_badal=4,
    madd_arid=2,
    madd_muttasil=6,
    madd_munfasil=6,
    madd_leen=4,
)

WARSH_QASR_ALBADAL_ICHBAA_ALARID = QiraatConfig(
    madd_badal=2,
    madd_arid=6,
    madd_muttasil=6,
    madd_munfasil=6,
    madd_leen=4,
)
WARSH_QASR_ALBADAL_TAWASOT_ALARID = QiraatConfig(
    madd_badal=2,
    madd_arid=4,
    madd_muttasil=6,
    madd_munfasil=6,
    madd_leen=4,
)
WARSH_QASR_ALBADAL_QASR_ALARID = QiraatConfig(
    madd_badal=2,
    madd_arid=2,
    madd_muttasil=6,
    madd_munfasil=6,
    madd_leen=4,
)