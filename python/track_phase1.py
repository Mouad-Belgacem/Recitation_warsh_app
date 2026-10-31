import json
import re
import random
from itertools import repeat

class moshaf:
    def __init__(self, location="moshaf.json"):
        # Creating an instance of the quran in the form of a dictionary
        # In doing so we store a dictionary that map the number of a sura to its name

        with open(location, 'r', encoding='utf-16') as f:
            data = json.load(f)
        self.quran = {}
        self.to_surah = {}

        for i, surah in enumerate(data.get("السور", []), start=1):
            self.to_surah[i] = surah.get("السورة", "").strip()
            for j, aya in enumerate(surah.get("الآيات بالترقيم", []), start=1):
                self.quran[(i, j)] = aya.strip()
        
    def __call__(self, i, j):
        return self.quran[(i, j)]
    
    def get_surah(self, i):
        return self.to_surah[i]
    
def update_track(track, occurence):
    new_track = []
    for i, x in enumerate(track):
        n = occurence.get(i, 0)
        if n:
            new_track.extend(repeat(x, n))
    return new_track

# Defining lawasiq
lawasiq = "ُ" + "۟" + "ٖ" + "ٛ" + "ْ" + "ٌ" + "ً" + "ّ" + "ٰ" + "َ" + "ٗ" + "۬" + "ۨ" + "۪" + "ٞ" + "ِ" + "ً"
    

# T for Transformations
T1 = [
      # Non pronounced Alif
      ["اْ", "", [(0,0), (1,0)]],
      ["وٓا", "وٓ", [(2,0)]], # one place forced us to add this
      # Switching order
      ["لاَ", "لَا", []],
      # Removing ishmam sign
      ["س۬", "سِ", []],
      # Some special caracters
      ["ۨ", "ن", []],
      ["ےْ" , "يْ", []],
      # Transforming the mim mokhfaa
      ["َۢ", "ً", [(1,0)]],
      ["ِۢ", "ٍ", [(1,0)]],
      ["ُۢ", "ٌ", [(1,0)]],
      # Transforming tanween ikhfa
      ["ٞ", "ٌ", []],
      ["ٗ", "ً", []],
      ["ٖ", "ٍ", []],
    #   # Removing waqf 
    #   ["(?<![ًٌٍٖٞٗ])"+"ۖ", ""],
    #   ["ۖ"+r"\$", r"$"],
      # Some special caracters
      ["(" + "ۧ" + "|ـ|۩|‏|-|" + "ۖ" + "|۞)", "", [(0,0)]],
      # some verbs have an additional alif
      ["لَّا" + r"(?![ ٓۖ\$])", "لَّ", [(3,0)]],
      [" لَا" + "(?![ ٓۖ])", " لَ", [(3,0)]],
      # Transforming special words
      ["وٰ", "ا", [(0,0)]],
    #   ["لَوٰة", "لَاة", [(2,0)]],
    #   ["بَوٰ", "بَا", [(2,0)]],
      ["تَاللَّهِ", "تَلَّاهِ", [(2,0), (3,0), (6,2)]],
      ["للَّه", "لَّاه", [(0,0), (3, 2)]],
      ["آٰللَّه", "اٰلَّاه", [(3, 2)]],
      ["لِّله", "لِّلَّاه", [(3,4)]],
      ["لِلهِ", "لِلَّاهِ", [(2, 4)]],
      ["نَخْلُقكُّم", "نَخْلُكُّم", [(6, 0)]],
      ["خَذتّ", "خَتّ", [(2, 0)]],
      ["أَوَاَ", "أَوَ", [(4,0), (5,0)]],
    #   ["ز(ّ?)َكَو", r"ز\1َكَ", [(-1,0)]],
    #   ["حَيَوٰة", "حَيَاة", [(-3,0)]],
      ["ل۪ےْ", "لَّا۽ِ", [(0,4), (-1,0)]],
      ["لتِ", "لَّتِ", [(0,3)]],
      ["لذِ", "لَّذِ", [(0,3)]],
      ["ل" + "ٰ", "لَّا", [(0,3)]],
      ["لذَ", "لَّذَ", [(0,3)]],
      ["ليْ", "لَّيْ", [(0,3)]],
      ["اٗ اَ۬لُّا", "َ لُّ", [(0,0), (3,0), (4,0), (5,0), (9,0)]],
      # Huruf moqataa
      ["اَلَٓمِّٓصَٓ", "أَلِف لَام مِّيم صَاد", [(0,6), (1,0), (2,5), (3,0), (4,0), (5,6), (6,0), (7,0), (8,0), (9,4), (10,0), (11,0)]],
      ["أَلَٓر۪", "أَلِف لَام ر۪ا", [(0,6), (1,0), (2,5), (3,0), (4,0), (5,3), (6,0)]],
      ["أَلَٓمِّٓر۪", "أَلِف لَام مِّيم ر۪ا", [(0,6), (1,0), (2, 5), (3,0), (4,0), (5,6), (6,0), (7,0), (8,0), (9,3), (10,0)]],
      ["كَٓه۪ي۪عَٓصَٓ", "كَاف ه۪ا ي۪ا عَين صَاد", [(0,5), (1,0), (2,0), (3,4), (4,0), (5,4), (6,0), (7,5), (8,0), (9,0), (10,4), (11,0), (12,0)]],
      ["طَه۪", "طَا ه۪ا", [(0,4), (1,0), (2,3), (3,0)]],
      ["طَسِٓمِّٓ", "طَا سِين مِّيم", [(0,4), (1,0), (2,5), (3,0), (4,0), (5,5), (6,0), (7,0), (8,0)]],
      ["طَسِٓ", "طَا سِين", [(0,4), (1,0), (2,4), (3,0), (4,0)]],
      ["يَسِٓ", "يَا سِينs", [(0,4), (1,0), (2,5), (3,0), (4,0)]],
      ["صَٓ", "صَاد", [(0,4), (1,0), (2,0)]],
      ["ح۪مِٓ عَٓسِٓقَٓ", "ح۪ا مِيم عَين سِين قَاف", [(0,4), (1,0), (2,4), (3,0), (4,0), (6,5), (7,0), (8,0), (9,5), (10,0), (11,0), (12,4), (13,0), (14,0)]],
      ["قَٓ", "قَاف", [(0,4), (1,0), (2,0)]],
      ["نُّٓ", "نُونs", [(0,5), (1,0), (2,0), (3,0)]],
      # Sometimes we get two spaces
      ["  ", " ", [(0,0)]],
      # Expliciting a type of Madd badal
      ["أٓ", "ءَا", [(1,2)]],
      # The special phenomena of "faddaratom" (albaqra hizb 1 thomon 8)
      ["رَٰٔ", "رَء", [(2,0)]],
      # The additional ya in afain
    #   ["أَفَإِيْن", "أَفَإِن"],
      ["إِيْ", "إِ", [(2,0), (3,0)]],
      # Transforming ya to Alif magsora
      [r"ي(ً|ٗ)(?!(.?)\$)", "اً", []],
      ["يٰ" ,"ا", [(1,0)]],
      # The special behavior of ا۟وْلَٰٓئِكَ and أُوْلُواْ
    #   ["وْلَٰٓئِ", "لَٰءِ", [(0,0), (1,0), (5,0)]],
      ["أُوْ", "أُ", [(2,0), (3,0)]],
      ["ا۟وْ", "ا۟", [(2,0), (3,0)]],
      [r"\$"+"اوْلَٰٓ",r"$"+"ءُلَا", [(3,0), (7,0)]], # اوْلَٰٓئِكَ في اية الهمز المزدوج
      # special case of hamza above ي (يَسْتَهْزِۓُ)
      ["ۓ","ء", [(0,0)]],
      # Removing sakin before alif man9ola
      # To simplify tracking we have different copies
      ["(ا|و|ے|ي)  " +"ا(َ|ُ|ِ)?"+"(۬|۟|۪)?"+"ل(َ|ُ|ِ)(ٛ)?ا(?![ ٓ])", r" ا\2\3ل\4\5ا", [(0,0), (1,0)]],
      ["(ا|و|ے|ي) " +"ا(َ|ُ|ِ)?"+"(۬|۟|۪)?"+"ل(َ|ُ|ِ)(ٛ)?ا(?![ ٓ])", r" ا\2\3ل\4\5ا", [(0,0)]],
      ["واْ  " +"ا(َ|ُ|ِ)?"+"(۬|۟|۪)?"+"ل(َ|ُ|ِ)(ٛ)?ا(?![ ٓ])", r" ا\1\2ل\3\4ا", [(0,0), (1,0), (2,0), (3,0)]],
      ["واْ " +"ا(َ|ُ|ِ)?"+"(۬|۟|۪)?"+"ل(َ|ُ|ِ)(ٛ)?ا(?![ ٓ])", r" ا\1\2ل\3\4ا", [(0,0), (1,0), (2,0)]],
      # Removing al taarif in the case of alif man9ola
      ["(وَ|فَ|كَ)" +"ا"+"ل(َ|ُ|ِ)(?![ ٛ])ا(?![ ٓ])", r"\1ل\2", [(2,0), (-1,0)]],
      ["(وَ|فَ|كَ)" +"ا"+"لَٛا(?![ ٓ])", r"\1لَٛا", [(2,0)]],
      # Iltiqaa hamzatayn in one word
      ["اَوْ۟", "اَ۽ُ", [(-1,0)]],  # اَوْ۟نَبِّئُكُم
      ["اَ۟نزِلَ", "اَ۽ُنزِلَ", [(2,2)]],  # اَ۟نزِلَ
      ["اَ۟ش", "اَ۽ُش", [(2,2)]],  # اَ۟شْهِدُواْ
      ["اَ۟لْ", "اَ۽ُلْ", [(2,2)]],  # اَ۟لْقِيَ
      ["أَئِ", "ءَ۽ِ", []],
      ["أَ۟", "ءَ۽ِ", [(-1,2)]],
      ["اَ۟ل", "اَ۬۽ِل", [(2,3)]],
      ["اَ۟ذَ", "اَ۬۽ِذَ", [(2,3)]],
      ["ءَامِنت", "ءَا@مِنت", [(2,2)]],
      ["ءَالِدُ", "ءَا@لِدُ", [(2,2)]],
      ["أَئِ", "ءَ۽ِ", []], # أَئِمَّةٗ
      ["أَي۪", "ءَ۽ِ", []],
      [" اَئِ", " ۽ِ", [(1,0), (2,0)]], # قُلَ اَئِنَّكُمْ
      [r"\$"+"اَئِ", r"$"+"ءَ۽ِ", []],
      # Removing ibdal sign
      ["وَ۬", "وَ", [(2,0)]],
      # The seven Alifat
      [r"(أَنَ|لَّٰكِنَّ)ا(?![\$ٓ])", r"\1", [(-1,0)]],
      # special writing of اَنَا (naql case)
      ["اَنَا ", "اَنَ ", [(4,0)]],
      # Imala Expection
      # here it's just a first stage to ensure that the next operation detecting 
      # imalas in waqfs doesn't take into consideration these special cases
      ["إِلَي" + "ٰ?" + "ٓ?" + r"\$", "إِلَا" + r"$", [(6,0), (7,0)]],
      ["عَلَي" + "ٰ?" + "(ٰ|ٓ)?" + r"\$", "عَلَا" + r"$", [(6,0), (7,0)]],
      ["حَتَّي" + "ٰ?" + "(ٰ|ٓ)?" + r"\$", "حَتَّا" + r"$", [(7,0), (8,0)]],
      ["زَكَي" + "ٰ?" + "(ٰ|ٓ)?" + r"\$", "زَكَا" + r"$", [(6,0), (7,0)]],
      ["لَدَي" + r"\$", "لَدَا" + r"$", []],
      # Words with normal alif and imala
      ["قْصَا", "قْصَي", []],
      ["طَغَا", "طَغَي", []],
      ["أَحْيَا" + "(?!ٓ)", "أَحْيَي", []],
      # اسرائيل
      ["إِسْرَآءِي", "إِسْرَآءِي" + "@", [(-1,2)]],
      # exptions of madd leen almahmuz
      ["لْمَوْءُ","لْمَوْ@ءُ", [(-3, 2)]],# الموؤودة
      ["مَوْئِ","مَوْ@ئِ", [(-3,2)]],# موئلا
      # قل اي وربي
      ["اِے", "اِے" + "*", [(2,2)]],
      # Handling alana
      # ["ءَالَٰن", "ءَلَ&ان"],
      # Removing a type a hmaza man9olaتَاللَّهِ
      ["لِلَا", "لِلَ", [(4,0)]],
      # Removing an additional yaa
      ["ِ" + "ےْ", "ِ", [(1,0), (2,0)]],
      # three hamazat
      ["ءَاٰ۬", "ءَ۽َا", []], # "قَالَ  فِرْعَوْنُ ءَاٰ۬مَنتُم"
      # يُوَآدُّونَ and كافة
      ["يُوَآدُّ", "يُوَaآدُّ", [(3,2)]],
      ["كَآفَّ", "كَaآفَّ", [(1,2)]],
      # Not sure why we should have imala here
      ["رّ۪", "رَّ", []],
      # Badal at the end
      [r"ءً\$", "ءَا$", [(1,2)]],
      ["أَلَٓمِّٓۖ اَحَسِبَ","ءَلِف لَام مِّي£مَ حَسِبَ", [(0,6), (1,0), (2,5), (3,0), (4,0), (5,7), (6,0), (7,0), (8,0), (10,0), (11,0)]],
      # Removing lam taarif
      ["ا(َ|ُ|ِ)۬ل([^ل]ّ|.ّ(?!َه))", r"ا\1" + "۬" + r"\2", [(3,0)]],
      ["آٰل([^ل]ّ|.ّ(?!َه))", "اٰ" + r"\1", [(2,0), (3,0)]],
      ["لِل([^ل]ّ|.ّ(?!َه))", "لِ" + r"\1", [(2,0)]],
      ["لِّل(.ّ)", "لِّ" + r"\1", [(3,0)]],
      ["(وَ|بِ|فَ)ال([^ل]ّ|.ّ(?!َه))", r"\1ا" + r"\2", [(3,0)]],
      # A typo in almoshaf (maybe)
      ["لشَ", "ششَ", [(0,0), (1,2)]], # اَ۬لشَفَٰعَةَ

]

T2 = [
      # Transforming hamza above yaa
      ["ئ", "ء", [(0,0)]],
      # One verse needs the alif to be removed (except at the end)
      [r"وا(?![ًْ\$])", "", [(0,0), (1,0)]],
      [r"وا\$", "و", [(1,0)]],
      # Removing alif man9ola
      ["ا(َ|ُ|ِ)?"+"(۬|۟|۪)?"+"ل(َ|ُ|ِ)(?![ ٛ])ا(?![ ٓ])", r"ا\1\2ل\3", [(-1,0)]],
      # Putting imala where it's removed if it's the end
      [r"يً\$","۪"+r"ا$", []],
      [r"َي\$","۪"+r"ا$", []],
      # Removing waw and yaa maddia at the end
      [r"ۥٓ?\$", r"$", [(1,0), (2,0)]],
      [r"ۦٓ?\$", r"$", [(1,0), (2,0)]],
      # Huruf moqataa
      ["أَلَٓمِّٓ اَ۬لَّاهُ", "ءَلِف لَام مِّي£مَ لَّاهُ", [(0,6), (1,0), (2,5), (3,0), (4,0), (5,7), (6,0), (7,0), (8,0), (10,0), (11,0), (12,0)]],
      ["(أ|ا)َلَٓمِّٓ(?! اَ۬لَّاهُ)", "ءَلِف لَام مِّيم", [(0,6), (1,0), (2,5), (3,0), (4,0), (5,5), (6,0), (7,0), (8,0)]],
      ["ح۪مِٓ", "ح۪ا مِيم", [(0,4), (1,0), (2,4), (3,0), (4,0)]],
      # Removing Madd
      ["ٓ", "", [(0,0)]],
      # Removing remaining ikhfaa sign
      ["ۢ", "", [(0,0)]],
      # Removing haraka at the end
      [r"اً\$", r"َا$", []],
      [r"(َ|ُ|ِ|ً|ٌ|ٍ)\$", r"$", [(0,0)]],
      # Normalizing hamazat
      ["(أ|ئ|ؤ|إ|ٔ|ٕ)", "ء", []],
      # Different type of madd albadal
      ["ءَ ا۟لَ", "ءَ ۽َالَ", [(3,3), (4,0)]],
      # Expliciting Naql Alharaka for tanween
      ["(ً|ٗ)" + " " + "ا([^ٰ])", r"َن\2 ا\2", [(1,0), (2,4)]],
      ["ا" + "(ً|ٗ)" + " " + "ا([^ٰ])", r"َن\2 ا\2", [(0,0), (2,0), (3,4)]],
      ["ا" + "(ً|ٗ)" + " " + "اٰ", "َنَ اٰ", [(0,0), (2,0), (3,4)]],
      ["(ٌ|ٞ)" + " " + "ا([^ٰ])", r"ُن\2 ا\2", [(1,0), (2,4)]],
      ["(ٌ|ٞ)" + " " + "اٰ", r"ُنَ اٰ", [(1,0), (2,4)]],
      ["(ٍ|ٖ)" + " " + "ا([^ٰ])", r"ِن\2 ا\2", [(1,0), (2,4)]],
      ["(ٍ|ٖ)" + " " + "اٰ", r"ِنَ اٰ", [(1,0), (2,4)]],
      # Removing sukun
      ["ْ", "", [(0,0)]],
      # Transforming alif ma9sora
      [r"َي ",r"َا ", []],
      # Removing a special waw
      ["ءُ او", "ءُ ۥ", [(3,0)]], # أَوْلِيَآءُ اوْلَٰٓئِكَ
      # Badal exceptions
      ["ظَّمَْٔا", "ظَّمءَا" + "@", [(-1,2), (4,0)]],
      ["سُْٔو", "سءُۥ" + "@", [(-1,2), (1,0)]],
      ["ذْءُ(ۥ|و)", "ذءُۥ" + "@", [(-1,2), (1,0)]],
      ["رْءَا", "رءَا" + "@", [(-1,2), (1,0)]],
]

T3 = [
      # Expliciting Madd Alwead with taking in account the possbility of madd alabadal
      [r"اً\$", r"َا$", []],
      [r"ءً\$", r"ءَا@$", [(1,3)]],
      # Transforming taa at the end then normalizing taa
      [r"ة\$", r"ه$", []],
      ["ة", "ت", []],
      # Making sukun at the end
      [r"(َ|ُ|ِ)\$", r"$", [(0,0)]],
      # Iltiqaa hamzatayn in two words
      ["ءَ اُ۟", "ءَ ۽ُ", [(-1,0)]],
      ["ءَ ا۪", "ءَ ۽ِ", []],
      ["ءُ اَ۬", "ءُ وَ", [(-1,0)]],
      ["ءُ ا۪", "ءُ وِ", []],
      ["ءِ اَ۟", "ءِ يَ&ا", [(4,3), (5,0)]], # & can be (perhaps) transformed to ^
      ["ءِ اَ۬", "ءِ يَ", [(-1,0)]],
      ["ءُ الَٰ", "ءُ ۥلَا", []], # أولياء اولائك
      ["الَٰء", "ءُلَاء", [(0,2)]], # اولائك في البداية
      ["ءِ ان(َ|ِ)", r"ءِ +ےن\1", [(3,2)]], 
      ["ءِ ا(?!۬)(?!.۬)(?!۟)", "ءِ ے", []],
      # Removing Al taarif
      # Again we create two versions to simplify tracking
      [" ا(َ|ُ|ِ)"+"(۬|۟|۪)", " ", [(1,0), (2,0), (3,0)]],
      [" ا(َ|ُ|ِ)"+"(?![۬|۟|۪])", " ", [(1,0), (2,0)]],
      # Removing some special Alifat
    #   [r"( |\$)(وَ|فَ)ا", r"\1\2"],
      [r"( |\$| وَ)بِا", r"\1بِ", [(-1,0)]],
      # Transforming tanwen
      ["ً", "َن", [(0,2)]],
      ["اً", "َن", []],
      ["ٌ"+r"(?!\$)", "ُن", [(0,2)]],
      ["ٌ"+r"\$", r"$", [(0,0)]],
      ["ٍ"+r"(?!\$)", "ِن", [(0,2)]],
      ["ٍ"+r"\$", r"$", [(0,0)]],
      # Fakk Tad3if
      ["(.)ّ", r"\1\1", []],
      # Transforming a type of alif
      ["(?<!ا)ٰ", "ا", []],
      # Transforming yaa maddia
      ["(ٛ|ِ)ي(?![َُِّْ۪])", r"\1ے", []],
      ["ۦ", "ے", []],
      # Naql sometimes yield the wrong haraka
      ["ن۟", "نُ", []],
      [" ا۟(?!و)", " ", [(1,0), (2,0)]],
      [" ا۟و", " ۥ", [(1,0), (2,0)]],
      # Ibtida2 على البغاء ان اردن -- و مثيلاتها
      [r"\$" + "ان(ِ|َ)", r"$" + r"ءِن\1", [(1,2)]],
      # Transforming waw maddia
      ["(۟|ُ|ٛ)و(?![َُِّْ۪])", r"\1ۥ", []],
      # Removing shadda at the begining
      [r"\$(.)ّ", r"$\1", [(-1,0)]],
      # اُ۬ل۪ےْ حالة الوقف
      ["۽" + r"\$", "ء" + r"$", []],
]

Ts = [T1, T2, T3]

rules1 = [(re.compile(pat), rep) for pat, rep, _ in T1]
rules2 = [(re.compile(pat), rep) for pat, rep, _ in T2]
rules3 = [(re.compile(pat), rep) for pat, rep, _ in T3]

ruless = [rules1, rules2, rules3]

pattern1 = re.compile(
    "|".join(f"(?P<R{i}>{pat.pattern})" for i, (pat, _) in enumerate(rules1))
)
pattern2 = re.compile(
    "|".join(f"(?P<R{i}>{pat.pattern})" for i, (pat, _) in enumerate(rules2))
)
pattern3 = re.compile(
    "|".join(f"(?P<R{i}>{pat.pattern})" for i, (pat, _) in enumerate(rules3))
)

patterns = [pattern1, pattern2, pattern3]

M = moshaf()

def ph1T(aya=None, attach_lawasiq=False, return_aya=False):
    if aya == None:
        aya = "$" + random.choice(list(M.quran.values())) + "$"
    elif aya[0] != "$" or aya[-1] != "$":
        raise Exception("The aya should start and finish with $ sign")
    
    track = [i for i in range(len(aya))]
    if attach_lawasiq:
        for i, x in enumerate(aya):
            if x in lawasiq:
                track[i] = track[i-1]
    
    occurence = {i: 1 for i in range(len(aya))}
    
    result = aya
    
    for T, rules, pattern in zip(Ts, ruless, patterns):
        
        occurence = {i: 1 for i in range(len(track))}
        
        def repl(match):
            rule_name = match.lastgroup
            start, length = match.start(), len(match.group(0))
            i = int(rule_name[1:])
            pat, replacement = rules[i]
            changes = T[i][2]
            # putting changes in context
            changes = [(start+idx, occ) if idx >= 0 else (start+idx+length, occ) for idx, occ in changes]
            # updating occurence
            occurence.update(changes)

            local_match = pat.fullmatch(match.group(0))
            return local_match.expand(replacement)
        
        result = pattern.sub(repl, result)
        track = update_track(track, occurence)

    if return_aya:
        return result, track, aya
    return result, track
        