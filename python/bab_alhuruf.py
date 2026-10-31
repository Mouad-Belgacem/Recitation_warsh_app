from utils import (
    get_next_caracter,
    get_next_harf,
    get_next_harf_in_same_word,
    get_previous_haraka,
    get_previous_harf,
    get_previous_harf_in_same_word,
    is_sakin,
    safe_haraka_at,
)
from qiraat_config import QiraatConfig,WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID
def build_handlers(cfg: QiraatConfig = WARSH_TAWASOT_ALBADAL_ICHBAA_ALARID):
    """
    Retourne un dict Get_Handler où chaque handler
    est une closure capturant `cfg`.
    """
    #BAB alwaw
    def handle_small_waw(index, text):
        res = ""
        # On regarde la prochaine lettre 
        nxt_h,idx_nxt_h = get_next_harf(index, text)
        nxt_h_same_word,idx_nxt_h_same_word = get_next_harf_in_same_word(index, text)
        prev_h_same_word,idx_prev_h_same_word = get_previous_harf_in_same_word(index, text)
        prev_haraka = get_previous_haraka(index, text)

        prev_three_sequences= text[index-3:index] if index-3 >=0 else None
        prev_two_sequences= text[index-2:index] if index-2 >=0 else None
        
        if text[index-1]==" ": 
            if text[index-3] == "ء": #  ءَولِيَاءُ ۥلَٰءك
                return "ۥ"*2, 1
            else: # فَمَنُ ۥتِيَ
                return "ۥ"*cfg.madd_badal, 1
        #    حال الابتداء في اِ۟وتُمِنَ  
        if prev_three_sequences in ["اِ۟"]:
            return "ۥ"*2, 1
        #    حال الابتداء في ا۟وتِيَ  
        elif prev_two_sequences in ["ا۟"]:
            return "ۥ"*cfg.madd_badal, 1
        
        if prev_haraka!="ُ":
            return "",1
        else:
            if nxt_h_same_word is not None: # s'il est pa None alors index+1 est dans le même mot
                if nxt_h_same_word == "@":
                    res = "ۥ" * 2 
                elif nxt_h_same_word in ['ء',"۽"]: # should replace it by the actual caracter
                    res = "ۥ" * cfg.madd_muttasil  #مد متصل
                elif get_next_caracter(idx_nxt_h_same_word,text)[0]=="$":
                    res="ۥ"*cfg.madd_arid
                elif is_sakin(index + 1, text): # Si le prochain harf  est sakin
                    res = "ۥ" *cfg.madd_lazim
                elif prev_h_same_word in ['ء',"۽"]: # should replace it by the actual caracter
                    res = "ۥ" * cfg.madd_badal  #مد بدل
                else: # Madd Tabi3i
                    res = "ۥ" * 2
            
            else: # Si il n'y a pas de lettre après le waw dans le même mot
                # print("we are here znd next harf is ",nxt_h)
                # 1. Madd muchbaa (devant Hamza) ou cas Sakin
                if nxt_h == 'ء':
                    res = "ۥ"* cfg.madd_munfasil 
                elif is_sakin(idx_nxt_h, text):
                    res = "" # قالو دع لنا eliminte the waw maddia in this case
                else:
                    res = "ۥ" * 2 # Madd Tabi3i

        return res, 1  # On a traité uniquement le caractère 'ۥ', donc on avance de 1

    def handle_waw(index, text):
        # On récupère les infos contextuelles
        prev_haraka = get_previous_haraka(index, text)
        nxt_h,idx_nxt_h = get_next_harf(index, text)
        # nxt_caracter=text[index+1] if index+1 < len(text) else None
        nxt_caracter, idx_nxt_caracter = get_next_caracter(index, text)
        
        # Votre logique de Madd Leen (Lien)
        # Note : Le Madd Leen dépend souvent de l'arrêt (Waqf), 
        if is_sakin(index,text) and index-2>=0 and text[index-2:index]== "ُ ":
            return "ۥ"*cfg.madd_badal,1
        
        # مد اللين
        elif  is_sakin(index, text): # Waw Sakin précédé d'une Fatha
            if nxt_h== text[index] and is_sakin(idx_nxt_h, text):
                return text[index], idx_nxt_h- index +1 # ألمتماثلان الصغير
            elif nxt_h==text[index] and not is_sakin(idx_nxt_h, text):
                return text[index], 1 # حال التضعيف
            if nxt_h == 'ء' and prev_haraka == 'َ': # مد االين المهموز
                return "و" *cfg.madd_leen, 1
            elif index + 2 < len(text) and  prev_haraka == 'َ':
                if text[index+2]=="$": # if the next caracter of the harf after waw is a end of a word then it's madd leen
                    return "و" * cfg.madd_leen, 1  # مد اللين في الوقف
            else:
                return "و" * 1, 1  # 
        return "و", 1 # C'est un Waw normal, on le garde tel quel
            

    # باب الياء العادية (ي) والياء المدية
    def handle_yah(index, text):
        # On récupère les infos contextuelles
        prev_haraka = get_previous_haraka(index, text)
        nxt_h,idx_nxt_h = get_next_harf(index, text)
        nxt_caracter,idx_nxt_caracter = get_next_caracter(index, text)

        previous_harf, idx_previous_harf = get_previous_harf(index, text)
        # haraka_of_the_previous_harf=text[idx_previous_harf+1] if text[idx_previous_harf+1] in ["َ","ِ","ُ"] else None 
        haraka_of_the_previous_harf = safe_haraka_at(
        idx_previous_harf + 1 if idx_previous_harf is not None else None, text)
        prev_three_sequences= text[index-3:index] if index-3 >=0 else None
        
        #الحالات 15 مثل اِ۪يتِنَا حال الابتداء
        if prev_three_sequences in ["اُ۪","اِ۪",'اَ۪']:
            return "ے"*2, 1
        # here it's اِ۪يتِنَا في حال الوصل
        if index-1 >= 0 and text[index-1] ==" ": # here it's اِ۪يتِنَا في حال الوصل
            if is_sakin(index,text): # اِ۪يتِنَا after phase1 becomes يتِنَا 
                
                if previous_harf=='ا':
                    return "ا"*2,1
                else:
                    if haraka_of_the_previous_harf=="َ" and nxt_h == "ت": # if the previous harf has fatha we should replace by اا
                        return "ا"*2,1
                    elif haraka_of_the_previous_harf =="ِ" and nxt_h == "ت": # if the previous harf has kasra we should replace by ے
                        return "ے"*2,1
                    elif haraka_of_the_previous_harf =="ُ": # if the previous harf has damma we should replace by و
                        return "ۥ"*2,1
                    else:
                        return "ي",1 # normal case
                
        # Logique pour la Yah normale vs Yah Maddiya
        if prev_haraka == 'َ' and is_sakin(index, text): # Yah Sakin précédé d'une fatha
            if nxt_h == 'ء':
                return "ي" * cfg.madd_leen, 1
            else:
                if is_sakin(index+1,text):
                    return "ي" * cfg.madd_leen, 1

        return "ي", 1 # C'est une Yah normale, on la garde tel quel

    def handle_yah_maddiya(index, text):
        # Logique pour la Yah Maddiya (Madd Sila)
        nxt_h,idx_nxt_h = get_next_harf(index, text)
        prev_h_in_same_word, idx_prev_h_in_same_word = get_previous_harf_in_same_word(index, text)
        nxt_h_same_word, idx_nxt_h_same_word = get_next_harf_in_same_word(index, text)
        

        if nxt_h_same_word is not None:
            if nxt_h_same_word=="£":
                return "ے"*6,2  # "ءَلِف لَام مِّي£مَ حَسِبَ"
            if nxt_h_same_word == "@": # Handling إسرائيل
                if is_sakin(get_next_harf_in_same_word(idx_nxt_h_same_word, text)[1], text): 
                    return "ے" * cfg.madd_arid, 2
                else:
                    return "ے" * 2, 2
            if nxt_h_same_word=="*":# قل اي وربي
                return text[index]*cfg.madd_badal,2
            elif nxt_h_same_word == 'ء':
                return "ے" * cfg.madd_muttasil, 1  # Madd muchbaa mutassil
            elif is_sakin(idx_nxt_h_same_word, text):
                
                if get_next_caracter(idx_nxt_h_same_word,text)[0]=="$":
                    
                    return text[index]*cfg.madd_arid,1
                else:
                    return "ے" * cfg.madd_lazim, 1  # Madd lazim
            elif nxt_h_same_word in ['ء', "۽"]:
                
                return "ے" * cfg.madd_muttasil, 1  # Madd muchbaa mutassil
            elif prev_h_in_same_word in ['ء', "۽"]:
                
                return "ے" * cfg.madd_badal, 1  # Madd Badal
            else:
                
                return "ے" * 2, 1  # Madd Tabi3i
        else:
         
            if nxt_h == 'ء':
                return "ے" * cfg.madd_munfasil, 1  # Madd muchbaa
            elif prev_h_in_same_word == 'ء':
                return "ے" * cfg.madd_badal, 1  # Badal
            elif is_sakin(idx_nxt_h, text):
                if nxt_h == "و": # اِ۬لذِے اِ۟وتُمِنَ
                    return "ے" * 2, 3
                return "", 1 # for في صحف

            else:
                return "ے" * 2, 1  # Tabi3i

    # باب &
    def handle_and(index,text):
        # Logique pour le caractère '&' (Waw de liaison) # comme السماء ي&اية & ici est utilisé pour dire qu'il y'a madd 4 badal ms la hamza est mobdala 
        
        return "ا"*cfg.madd_badal, 2  
    # لِننَبِےءِ +ےنَ رَاد
    def handle_plus(index,text):
        # Logique pour le caractère '&' (Waw de liaison) # comme   لِننَبِےءِ +ےنَ رَاد + ici est utilisé pour dire qu'il y'a madd 6   
        
        return "ے"*6, 2  # Ici, on choisit de l'ignorer complètement
    # باب "\u065B"
    def handle_chapeau(index,text):
        # Logique pour le caractère '&' (Waw de liaison) # comme السماء ي&اية & ici est utilisé pour dire qu'il y'a madd 4 badal ms la hamza est mobdala 
        # On peut décider de le remplacer par une lettre spécifique ou de l'ignorer
        nxt_caracter, idx_nxt_caracter = get_next_caracter(index, text)
        if nxt_caracter in ['ا','ۥ','ے']: # ca caractétise الاخرة الاولى الايمن
            return nxt_caracter * cfg.madd_badal, 2  # we ignore it but we need to skip the next caracter as well since it's madd and no need to treat it again
        else:
            return '',1
        
    # باب الالف 
    def handle_alif(index, text):
        # you have to add قالا لحمد لله
        # Logique pour l'Alif normale vs Alif Maddiya
        prev_haraka = get_previous_haraka(index, text)
        nxt_h,idx_nxt_h = get_next_harf(index, text)
        prev_harf,idx_prev_harf = get_previous_harf_in_same_word(index, text)
        nxt_caracter,idx_nxt_caracter = get_next_caracter(index, text)
        next_h_same_word, idx_next_h_same_word = get_next_harf_in_same_word(index, text)
        
        if prev_harf == "a":
            return "ا"*cfg.madd_lazim, 1
        
        if prev_harf in ['ف','و', 'ك']: #فادع والحمد
            if is_sakin(idx_next_h_same_word,text):
                if index+2 < len(text) and text[index+2]=="$":
                    return "ا"*cfg.madd_arid,1  # من وال$
                elif next_h_same_word != "ف": # كَاف ه۪ا ي۪ا عَين صَاد
                    return "", 1 # for cases like والحمد
            else: 
                if prev_harf in ['ف', 'ك'] and text[index+1:index+3]=="لَ":
                    return "",1
                    
            
        map_point={"۬":"َ",    # map points above and under alifs with thier corresponding harakat
                "۪":"ِ",
                "۟":"ُ"} # for example اُ۟شْكُرْ
        # if prev_haraka !="َ": # if not preceded by Fatha, it's a normal Alif
        #     return "ا", 1
        # else:
        # if text[index+1]=="ٰ":
        #     return "ا"*4,2 # comme مِنَ اٰيَةٍ 
        if prev_haraka not in ["َ", None]: # we are not in ibtidae and not precedeed by fatha as لابنه
            return "", 1

        if text[index-1]== "$": # ألابتداء 

            if text[index+2] in map_point.keys(): # diffrent type pf points in the top of alif , above alif 
                return "ء"+ map_point[text[index+2]], 3
            elif text[index+1] in ['َ',"ُ","ِ"]: # fatha damma kassra
                return "ء"+ text[index+1],2
            elif text[index+1] in map_point.keys(): # Sometimes the alif contain only one special character ا۟رِيدَ
                return "ء"+ map_point[text[index+1]], 2
            elif text[index+1]=='ٰ':
                if is_sakin(idx_next_h_same_word, text):
                    return "ءَ"+"ا"*cfg.madd_lazim,2 # اٰلذذَكَرَينِ : هنا قاعدة أقوى المدود لانه اجتمع سببان الهمز قبل المد والسكون بعده
                else:
                    return 'ءَ'+ "ا"*cfg.madd_badal,2  # الابتداء في من اٰيَةٍ 
            
            else:
                return text[index:idx_next_h_same_word], idx_next_h_same_word-index # ibtidae
        else:
            if next_h_same_word is not None:
                if next_h_same_word == '$':
                    return "ا" * 2, 1  # Madd iwad
                elif next_h_same_word == '@':
                    return "ا" * 2, 2  # Madd iwad for words like بناءً
                elif next_h_same_word in ['ء','۽']:
                    return "ا" * cfg.madd_muttasil, 1  # Madd muchbaa mutassil
                elif is_sakin(idx_next_h_same_word, text):
                    if text[index+1]=='ٰ': # for example اٰلذذَكَرَينِ الاصل انه بدل لكن قاعدة أقوى المدود تعده لازما لأن بعده ساكن
                        return "ا" * cfg.madd_lazim, 2  # Madd lazim
                    elif text[index+1] in ["۟"]:
                        # return "ا"+map_point[text[index+1]],2 # مثل لئن ا۟خرِجُ
                        return "",2
                    elif get_next_caracter(idx_next_h_same_word,text)[0]=="$":
                        return text[index]*cfg.madd_arid,1
                    else:
                        return 'ا'*cfg.madd_lazim, 1
                elif prev_harf in ['ء', "۽"]:
                    return "ا" * cfg.madd_badal, 1  # Madd Badal
                elif text[index+1]=="ٰ":
                    return "ا"*cfg.madd_badal,2 # comme مِنَ اٰيَةٍ 

                else:
                    return "ا" * 2, 1  # Madd Tabi3i
            else:
                if is_sakin(idx_nxt_h, text):
                    return "", 1  # لها دخلي
                # if nxt_h == '$':
                #     return "ا" * 2, 1  # Madd iwad
                # elif nxt_h == '@':
                #     return "ا" * 2, 2  # Madd iwad for words like بناءً
                elif nxt_h in ['ء',"۽"]: # should replace it by the actual caracter
                    return "ا" * cfg.madd_munfasil, 1  #مد مشبع
                elif nxt_caracter =="ٰ": # if the next character is Alif
                    return "ا" * cfg.madd_badal, 2  # Madd badal special
                elif prev_harf in  ['ء',"۽"]: # should replace it by the actual caracter
                    return "ا" * cfg.madd_badal, 1  # Badal
                else:
                    return "ا" * 2, 1  # Madd Tabi3i
            


    # باب النون
    huruf_ikhfaa=['ت', 'ث', 'ج', 'د', 'ذ', 'ز', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ',"ك","ف","ق"]
    huruf_idgham_kamil=[ 'م', 'ن']
    huruf_idgham_nakis= ['و', "ي"]
    huruf_idgham_without_gunnah=['ل', 'ر']

    def handle_noon(index, text):
        # Logique pour le Noon normal vs Noon Maddiya
        prev_haraka = get_previous_haraka(index, text)
        nxt_h,idx_nxt_h = get_next_harf(index, text)
        nxt_h_same_word,idx_nxt_h_same_word = get_next_harf_in_same_word(index, text)


        if not is_sakin(index, text):
            return "ن", 1
        else:
            if nxt_h_same_word is not None: # s'il est pa None alors index+1 est dans le même mot
                if nxt_h_same_word=="ن":
                    return "ن"*4, 2
                elif nxt_h_same_word in huruf_ikhfaa:
                    return "ںں", 1
                elif nxt_h_same_word in huruf_idgham_nakis:
                    return "ن", 1  # الحالات الخاصة للادغام في كلمة واحدة مثل صنوان قنوان دنيا بنيان 
                # elif nxt_h_same_word in huruf_idgham_without_gunnah:
                #     return "", 1  # idgham without gunnah
                elif nxt_h_same_word == 'ب':
                    return "۾۾", 1  # الاقلاب 2  two is for the noon and the space after it
                else:
                    return "ن", 1  # اظهار
            else:
                if nxt_h in huruf_ikhfaa:
                    return "ںں", 1  # ikhfaa
                elif nxt_h in huruf_idgham_kamil: # in idgham don't forget the special cases صنوان ...
                    return nxt_h*4, 4   # we treated noun+ espace + noun_sakina + noun_mota7arrika
                elif nxt_h in huruf_idgham_nakis:
                    return nxt_h*3, 3  # idgham nakis
                elif nxt_h in huruf_idgham_without_gunnah:
                    return "", 1  # idgham without gunnah
                elif nxt_h == 'ب':
                    return "۾۾", 2  # الاقلاب 2  two is for the noon and the space after it
                else:
                    return "ن", 1  # اظهار

    # BAB almim
    def handle_mim(index, text):
        next_h,idx_next_h = get_next_harf(index, text)
        next_h_same_word,idx_next_h_same_word = get_next_harf_in_same_word(index, text)

        if not is_sakin(index, text):
            
            return "م", 1
        else:
            if next_h_same_word is not None:
                if next_h_same_word=="م":
                    return "م" * 4, 2  # ghona
                elif next_h_same_word=='ب':
                    return "۾۾" , 1
                else:
                    return "م", 1  # اظهار
            else:
                if next_h == 'ب':
                    return "۾۾" , 1  # Idgham Mimi
                elif next_h == 'م':
                    return "م" * 4, 4  # Idgham Mimi Shamel
                else:
                    return "م", 1  # اظهار
            

    # باب الحروف المقلقلة العادية

    Huruf_qalqala_normal=['ق', 'ب', 'ج']

    def handle_qalqala_normal(index, text):
        # Logique pour les lettres de qalqala normales
        next_h, idx_next_h = get_next_harf(index, text)
        if is_sakin(index, text):
            if next_h== text[index] and is_sakin(idx_next_h, text):
                return text[index], idx_next_h - index + 1 # ألمتماثلان الصغير
            elif next_h==text[index] and not is_sakin(idx_next_h, text):
                return text[index], 1 # حال التضعيف
            else:
                return text[index] +"چ", 1  # add چ for qalqala
        else:
            return text[index], 1  # Pas de qalqala, on garde la lettre normale

    # باب الدال
    def handle_dal(index, text):
        # Logique pour les lettres de qalqala normales
        next_h,idx_next_h = get_next_harf(index, text)
        next_h_same_word, idx_next_h_same_word = get_next_harf_in_same_word(index, text)
        if is_sakin(index, text) and next_h in ['ت', "ظ", "ض"]: # باب المتجانسان والمتقاربان
            return "", 1 # we eliminate the dal in this case (باب المتجانسان)
        elif is_sakin(index, text):
            if next_h== text[index] and is_sakin(idx_next_h, text):
                return text[index], idx_next_h - index + 1 # ألمتماثلان الصغير
            elif next_h==text[index] and not is_sakin(idx_next_h, text):
                return text[index], 1 # حال التضعيف
            else:
                return "د" +"چ", 1  # add چ for qalqala
        else:
            return "د", 1  # Pas de qalqala, on garde la lettre normale
        

    #  باب الطاء
    def handle_tha(index, text):
        # Logique pour les lettres de qalqala normales
        next_h,idx_next_h = get_next_harf(index, text)
        next_h_same_word, idx_next_h_same_word = get_next_harf_in_same_word(index, text)
        if is_sakin(index, text) and next_h in ['ت']: # if the next harf is a space or end of word then we are in a waqf situation and we should apply qalqala
            return "ڟ", 1 # we eliminate the dal in this case (باب المتجانسان)
        elif is_sakin(index, text):
            if next_h== text[index] and is_sakin(idx_next_h, text):
                return text[index], idx_next_h - index + 1 # ألمتماثلان الصغير
            elif next_h==text[index] and not is_sakin(idx_next_h, text):
                return text[index], 1 # حال التضعيف
            else:
                return "ط" +"چ", 1  # add چ for qalqala
        else:
            return "ط", 1  # Pas de qalqala, on garde la lettre normale

    # باب التاء
    def handle_ta(index, text):
        # Logique pour les lettres de qalqala normales
        next_h,idx_next_h = get_next_harf(index, text)
        if is_sakin(index, text):
            if next_h in ['ط', "د","ظ"]: # المتجانسان والمتقاربان
                return "", 1 # we eliminate the dal in this case (باب المتجانسان)
            elif next_h== text[index] and is_sakin(idx_next_h, text):
                return text[index], idx_next_h - index + 1 # المتماثلان الصغير
            else:
                return text[index], 1  
        else:
            return "ت", 1  # Pas de qalqala, on garde la lettre normale


    #باب الذال
    def handle_dhal(index, text):
        # Logique pour les lettres de qalqala normales
        next_h,idx_next_h = get_next_harf(index, text)
        if is_sakin(index, text):
            if next_h in ['ظ']: # المتجانسان والمتقاربان
                return "", 1 # we eliminate the dhal in this case (باب المتجانسان)
            elif next_h== text[index] and is_sakin(idx_next_h, text):
                return text[index], idx_next_h - index + 1 # المتماثلان الصغير
            else:
                return text[index], 1  
        else:
            return text[index], 1  


    # باب اللام 
    def handle_lam(index, text):
        # Logique pour les lettres de qalqala normales
        next_h,idx_next_h = get_next_harf(index, text)
        next_h_same_word, idx_next_h_same_word = get_next_harf_in_same_word(index, text)

        if is_sakin(index, text):
            if next_h_same_word is not None:  # if the next harf in the same word is a lam then we are in a waqf situation and we should apply qalqala
                return "ل", 1
            else: 
                if next_h in ['ل', "ر"]: # if the next harf لام or ر
                    return '', 2
                else:
                    return "ل", 1
        else:
            return "ل", 1  # on garde la lettre normale
        
    huruf_mutamatilan=['ث', 'ح', 'خ', 'ر', 'ز', 'س', 'ش', 'ص', 'ض', 'ظ', 'ع', 'غ', 'ف', 'ك']

    def handle_mutamatilan(index,text):
        next_harf,idx_next_harf=get_next_harf(index,text)
        if is_sakin(index,text):
            if next_harf==text[index] and is_sakin(idx_next_harf, text):
                return text[index], idx_next_harf - index + 1
            else:
                return text[index],1
        else:
            return text[index],1

    # باب الحروف العادية (خ، ح، )
    # we need to define الحروف العادية
    standard_caracters=[ "ه", "ِ", "َ", "۪", "ء", "", "ُ", "۽"]
    def handle_standard_char(index, text):
        return text[index], 1  # For now, we just return the character itself and move to the next one

    # باب العلامات غير المنطوقة
    to_remove = ["@", "۟", "$", "۬", "ٰ", " ", "s", "a","£"]
    def handle_remove(index, text):
        return "", 1

    # باب الحروف المقلقلة العادية
    Huruf_qalqala_normal=['ق', 'ب', 'ج']

    Get_Handler = {
        'و': handle_waw,
        'ۥ': handle_small_waw,
        'ي': handle_yah,
        'ا': handle_alif,
        'ٛ': handle_chapeau,
        "ے": handle_yah_maddiya,
        'ن': handle_noon,
        'م': handle_mim,
        'د': handle_dal,
        "ط": handle_tha,
        'ت': handle_ta,
        "ذ": handle_dhal,
        'ل': handle_lam,
        "&": handle_and,
        "+": handle_plus,
    }

    Handle_standard = {k: handle_standard_char for k in standard_caracters}
    Handle_remove = {k: handle_remove for k in to_remove}
    Handl_moqalqal_normal = {k: handle_qalqala_normal for k in Huruf_qalqala_normal}
    Handl_mutamatilan={k: handle_mutamatilan for k in huruf_mutamatilan}

    Get_Handler = Get_Handler | Handle_standard | Handle_remove | Handl_moqalqal_normal | Handl_mutamatilan 
    return Get_Handler