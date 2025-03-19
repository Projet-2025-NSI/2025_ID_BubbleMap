import mysql.connector
import pygame
import math

## PYGAME 
pygame.init()
width, height = 800, 600
screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
pygame.display.set_caption("Bubblemap")
icon = pygame.image.load("BM.png")
pygame.display.set_icon(icon)


## VARIABLES

#couleurs
FOND_SIMPLE=(220, 235, 245)
FOND_GRIS=(199,212,221)

BULLE_SIMPLE=(20, 80, 120)
BULLE_GRIS=(8,34,51)

BRANCHES_SIMPLES=(180, 210, 230)
BRANCHES_GRIS=(112, 130, 142)

TEXTE=(180, 210, 230)

#variables interface
deplacement = False
position_interface = [0, 0]
facteur_zoom = 1.0
detail_ouvert=False

def connexion_db(): #connnexion à la BD
    conn = mysql.connector.connect(host="localhost",user="root",password="",database="art_nsi")
    return conn

def coupe_texte(texte, font, largeur_ligne_max):
    #la fonction prend un texte, une police et une largeur maximale de ligne et renvoie une liste du textes découpés en lignes
    liste_mots = texte.split()
    lignes = []
    temp_ligne = ""

    for i in liste_mots:
        ligne_teste = temp_ligne + " " + i
        if font.size(ligne_teste)[0] <= largeur_ligne_max:
            temp_ligne = ligne_teste
        else:
            lignes.append(temp_ligne)
            temp_ligne = i

    if temp_ligne !="" :
        lignes.append(temp_ligne)

    return lignes

class Bulle:
    def __init__(self,x,y,rayon,texte,profondeur,parent=None, id_periode=None,bulle_detail=None):
        self.x=x
        self.y=y
        self.rayon=rayon
        self.texte=texte                    #texte à afficher dans la bulle
        self.parent=parent
        self.profondeur=profondeur          #comme dans un arbre, position par rapport à la racine "bulle_principale" (départ avec une profondeur 1)
        self.id_periode=id_periode
        self.bulle_detail=bulle_detail      #attribut réservé à la bulle principale qui stocke le détail (texte) à afficher lors d'un clic droit
        self.active=False                   #True si les bulles sont à afficher, False si non
        self.sous_bulles=[]                 #liste des sous bulles d'une bulle

    ### METHODES DE GESTION DES BULLES
    def zoomer(self, facteur):
        #méthode récursive pour grossir les 
        self.rayon *= facteur
        self.x = width // 2 + (self.x - width // 2) * facteur
        self.y = height // 2 + (self.y - height // 2) * facteur

        self.taille_texte = int(self.rayon*0.2)

        for sous_bulle in self.sous_bulles:
            sous_bulle.zoomer(facteur)

    def trouver_bulle_plus_proche(self,x,y): 
        #méthode récursive pour obtenir la bulle où l'utilisateur clique, fonctionne comme une recherche min d'une liste mais avec la distance des bulles
        bulle_plus_proche = self
        distance_min = math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
        for sous_bulle in self.sous_bulles:
            bulle_candidate = sous_bulle.trouver_bulle_plus_proche(x, y)
            distance_candidate = math.sqrt((x - bulle_candidate.x) ** 2 + (y - bulle_candidate.y) ** 2)
            if distance_candidate < distance_min:
                bulle_plus_proche = bulle_candidate
                distance_min = distance_candidate
        return bulle_plus_proche

    def deplacer(self,dx,dy):
        #méthode récursive qui déplace les centres des bulles
        self.x+=dx
        self.y+=dy
        for sous_bulle in self.sous_bulles:
            sous_bulle.deplacer(dx,dy)

    def afficher_cacher_sous_bulles(self):
        #méthode qui désactive une bulle et toutes sous-bulles
        if self.active==True:
            self.desactiver_sous_bulles()
        else:
            self.active = True

    def desactiver_sous_bulles(self):
        #méthode récursive qui désactive toutes les sous-bulles d'une bulle
        self.active = False
        for sous_bulle in self.sous_bulles:
            sous_bulle.desactiver_sous_bulles()


    def ajouter_sous_bulles(self):
        #méthode qui permet de trouver dans la base de donnée les éléments à afficher dans les sous-bulles d'une bulle pour les ajouter en tant que bulles "filles" avec tous leurs paramètres
        if not self.sous_bulles and self.profondeur<5:
            conn = connexion_db()
            if not conn:
                return

            cursor = conn.cursor()
            #on utilise un dictionnaire pour ne pas répéter tout le code d'ajout des bulles (améliore la lisibilité du code)
            dico_requete={1:"SELECT id_Periodes, Periode FROM periodes;",
                          2:"SELECT nomMouvement_M FROM musiques WHERE id_Periodes = "+str(self.id_periode)+" UNION SELECT nomMouvement_VP FROM visuels_et_plastiques WHERE id_Periodes = "+str(self.id_periode)+";",
                          3:"SELECT nomArtistes FROM artistes WHERE id_Mouvement_VP IN (SELECT id_Mouvement_VP FROM visuels_et_plastiques WHERE nomMouvement_VP = \""+str(self.texte)+"\") OR id_Mouvement_M IN (SELECT id_Mouvement_M FROM musiques WHERE nomMouvement_M = \""+str(self.texte)+"\");",
                          4:"SELECT oeuvres.nomOeuvre FROM oeuvres JOIN artistes ON oeuvres.id_Oeuvres = artistes.id_Oeuvres WHERE artistes.nomArtistes =\""+self.texte+"\";",
                         }

            #on récupère les périodes artistiques dans la base de donnée selon
            cursor.execute(dico_requete[self.profondeur])
            resultats = cursor.fetchall()
            nb_sous_bulles = len(resultats)

            #on calcule l'angle nécessaire entre chaque sous-bulle selon le nombre de sous-bulle
            angle_ecart=2*math.pi/nb_sous_bulles
            
            #on décale d'une demi fois l'angle calculé en fonction de si le nombre de sous-bulle est pair ou impair pour éviter une superposition des bulles/branches
            if self.parent is None:
                angle_depart=0
            else:
                angle_depart = math.atan2(self.y - self.parent.y, self.x - self.parent.x)
                if nb_sous_bulles%2==0:
                    angle_depart+=angle_ecart/2

            
            #déclaration de variables vides pour éviter de trop répéter le code selon les requêtes (améliore la lisibilité)
            nom_periode,nom_mouvement,nom_artiste,nom_oeuvres,id_periode="","","","",None

            #on enregistre les résultats des requêtes dans les variables pour chaque sous-bulle
            for i in range(len(resultats)):
                if self.profondeur==1:
                    id_periode = resultats[i][0]
                    nom_periode = resultats[i][1]

                elif self.profondeur==2:
                    nom_mouvement = resultats[i][0]

                elif self.profondeur==3:
                    nom_artiste = resultats[i][0]

                elif self.profondeur==4:
                    nom_oeuvres = resultats[i][0]

                #on utilise un dictionnaire pour savoir quel texte doit être enregistré dans une sous bulle en fonction de la profondeur
                dico_textes={1:nom_periode,
                             2:nom_mouvement,
                             3:nom_artiste,
                             4:nom_oeuvres
                            }

                #on utilise un dictionnaire pour avoir différentes distances entre les bulles "parents" et les bulles "filles" en fonction de la profondeur pour éviter les superpositions
                dico_distances={
                                1:(bulle_principale.rayon/self.profondeur+self.rayon)*4,
                                2:(self.rayon/self.profondeur+self.rayon)*3,
                                3:2*self.rayon,
                                4:2*self.rayon
                              }
                
                angle=angle_depart+i*(angle_ecart)
                distance=dico_distances[self.profondeur]
                new_x=self.x+distance*math.cos(angle)
                new_y=self.y+distance*math.sin(angle)
                self.sous_bulles.append(Bulle(new_x, new_y,bulle_principale.rayon/(2**self.profondeur), dico_textes[self.profondeur], self.profondeur+1, parent=self, id_periode=id_periode))
            conn.close()

    ###METHODES DE DESSIN DE L'INTERFACE
    def dessiner_liens(self):
        #méthode qui permet de dessiner les branches entre les bulles sur l'interface
        if self.active:
            for sous_bulle in self.sous_bulles:
                if detail_ouvert: #on utilise une couleur différente en fonction de si le détail des bulles est ouvert
                    pygame.draw.line(screen,BRANCHES_GRIS,(int(self.x),int(self.y)),(int(sous_bulle.x),int(sous_bulle.y)),2)
                else:
                    pygame.draw.line(screen,BRANCHES_SIMPLES,(int(self.x),int(self.y)),(int(sous_bulle.x),int(sous_bulle.y)),2)
                sous_bulle.dessiner_liens() #récursif, relance la fonction sur les bulles sous_bulle

    def dessiner_bulle(self):  
        #méthode récursive qui permet de dessiner une bulle puis relance sur ses sous-bulle
        if detail_ouvert: #on utilise une couleur différente en fonction de si le détail des bulles est ouvert
            pygame.draw.circle(screen, BULLE_GRIS, (int(self.x), int(self.y)), int(self.rayon), int(self.rayon))
        else:
            pygame.draw.circle(screen, BULLE_SIMPLE, (int(self.x), int(self.y)), int(self.rayon), int(self.rayon))

        taille_texte = int(self.rayon * 0.2) #on règle la taille de la police de texte en fonction du rayon d'une bulle pour qu'elle dépende proprement du zoom
        font = pygame.font.Font(None, taille_texte)
        
        largeur_ligne_max = int(self.rayon * 1.7) #limite pour éviter que le texte déborde des bulles 
        lignes = coupe_texte(self.texte, font, largeur_ligne_max) #on découpe le texte en lignes pour ne pas que le texte soit trop grand
        
        hauteur_totale_texte=0
        if len(lignes)>1:
            hauteur_totale_texte = len(lignes) * taille_texte
        y_start = self.y - (hauteur_totale_texte//2) #on enregistre le point de départ du texte en fonction de la hauteur qu'il prend
        
        for i in range(len(lignes)): #on affiche les lignes du texte une par une
            text = font.render(lignes[i], True, TEXTE)
            text_rect = text.get_rect(center=(self.x, y_start + i * taille_texte))
            screen.blit(text, text_rect)

        if self.active == True: #on relance la méthode sur les sous-bulles si la bulle est active
            for sous_bulle in self.sous_bulles:
                sous_bulle.dessiner_bulle()

    def dessiner_detail(self):
        #méthode qui permet de gérer le dessin du cadre et du texte du détail des bulles quand (ce qui s'affiche lorsqu'on clique droit sur une bulle)
        rectangle_largeur= width//1.5
        rectangle_hauteur= height//1.2
        rectangle_x=width//2-rectangle_largeur//2
        rectangle_y=height//2-rectangle_hauteur//2
        pygame.draw.rect(screen,BULLE_SIMPLE, (rectangle_x,rectangle_y, rectangle_largeur, rectangle_hauteur),border_radius=30)

        requete="SELECT detailMouvement_VP from visuels_et_plastiques where nomMouvement_VP = \'"+bulle_principale.bulle_detail.texte+"\' union select detailMouvement_M from musiques where nomMouvement_M = \'"+bulle_principale.bulle_detail.texte+"\' union select detailOeuvre from oeuvres where nomOeuvre=\'"+bulle_principale.bulle_detail.texte+"\' union select Biographies from artistes where nomArtistes=\'"+bulle_principale.bulle_detail.texte+"\';"
        conn = connexion_db()
        cursor = conn.cursor()
        cursor.execute(requete)
        resultat = cursor.fetchone()

        #on utilise le même principe que dans les bulles pour ne pas que le texte dépasse du cadre et qu'il se découpe en lignes
        font = pygame.font.Font(None,32)
        texte=resultat[0]

        marge_texte=15
        lignes = coupe_texte(texte, font, rectangle_largeur-marge_texte)

        for i in range(len(lignes)):
            text_surface = font.render(lignes[i], True, TEXTE)
            screen.blit(text_surface, (rectangle_x + marge_texte, rectangle_y + 20 + i * 30))


#bulle de départ au centre de l'interface, équivalente à une racine dans un arbre
bulle_principale=Bulle(width // 2, height // 2, 128,"Art",1)


boucle=True
while boucle==True:
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            boucle = False

        elif event.type == pygame.MOUSEBUTTONDOWN:                      #détec boutons enfoncés sur le clavier ou la souris

            if event.button == 2:                                       #detec clic molette
                if detail_ouvert==False:
                    deplacement = True                                  #active le deplacement dans l'interface
                    position_interface = event.pos

            elif event.button == 1:                                     #détec clic gauche (afficher les sous_bulles)
                if detail_ouvert==False:                                #on bloque l'action si le détail est ouvert
                    bulle_cible = bulle_principale.trouver_bulle_plus_proche(event.pos[0], event.pos[1]) #on cherche la bulle qui est cliquée
                    dx = event.pos[0] - bulle_cible.x
                    dy = event.pos[1] - bulle_cible.y
                    if math.sqrt(dx ** 2 + dy ** 2) <= bulle_cible.rayon:
                        bulle_cible.ajouter_sous_bulles()
                        bulle_cible.afficher_cacher_sous_bulles()

            elif event.button == 3:                                     #détec clic droit (affiche les détails des bulles)
                if detail_ouvert==True:
                    detail_ouvert=False
                else:
                    bulle_cible = bulle_principale.trouver_bulle_plus_proche(event.pos[0], event.pos[1]) #on cherche la bulle qui est cliquée
                    dx = event.pos[0] - bulle_cible.x
                    dy = event.pos[1] - bulle_cible.y
                    if math.sqrt(dx ** 2 + dy ** 2) <= bulle_cible.rayon and bulle_cible.profondeur>2: #les bulles ont un détail à afficher à partir d'une profondeur de 2
                        detail_ouvert=True
                        bulle_principale.bulle_detail=bulle_cible


        elif event.type==pygame.MOUSEBUTTONUP:                          #détec boutons relâchés sur le clavier ou la souris
            if detail_ouvert==False:                                    #on bloque l'action si le détail est ouvert
                if event.button == 2:                                   #detec relâchement du clic molette
                    deplacement = False                                 #fin déplacement dans l'interface

        elif event.type==pygame.MOUSEMOTION:                            #détec souris déplacéee
            if detail_ouvert==False:                                    #on bloque l'action si le détail est ouvert
                if deplacement==True:
                    dx=event.pos[0] - position_interface[0]             #on enregistre le déplacement à effectuer en abscisse
                    dy=event.pos[1] - position_interface[1]             #on enregistre le déplacement à effectuer en ordonnée
                    bulle_principale.deplacer(dx, dy)                   
                    position_interface = event.pos

        elif event.type == pygame.MOUSEWHEEL:                           #détec molette
            if detail_ouvert==False:                                    #on bloque l'action si le détail est ouvert
                if event.y > 0:
                    zoom_suplementaire = 1.2
                else:
                    zoom_suplementaire=0.8
                if facteur_zoom*zoom_suplementaire>0.18 and facteur_zoom*zoom_suplementaire<25:
                    facteur_zoom*=zoom_suplementaire
                    bulle_principale.zoomer(zoom_suplementaire)

        elif event.type==pygame.VIDEORESIZE:                            #redimensionner la fenêtre
            width,height=event.w,event.h
            fenetre=pygame.display.set_mode((width,height),pygame.RESIZABLE)

    #on efface puis on redessine l'ensemble des bulles et leurs branches, en partant de la bulle Art (tout en récursif)
    if detail_ouvert==True: #on utilise une couleur différente en fonction de si le détail des bulles est ouvert
        screen.fill(FOND_GRIS)
    else:
        screen.fill(FOND_SIMPLE)
    bulle_principale.dessiner_liens()
    bulle_principale.dessiner_bulle()
    if detail_ouvert==True:
        bulle_principale.dessiner_detail()

    pygame.display.flip() #actualise

pygame.quit()