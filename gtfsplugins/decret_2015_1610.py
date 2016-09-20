# -*- coding: utf-8 -*-
#    This file is part of Gtfslib-python.
#
#    Gtfslib-python is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Gtfslib-python is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with gtfslib-python.  If not, see <http://www.gnu.org/licenses/>.
"""
@author: Laurent GRÉGOIRE <laurent.gregoire@mecatran.com>
"""

from _collections import defaultdict
from gtfslib.utils import fmttime

"Cf. plugin pour la documentation"
def decret_2015_1610(trips, trace=True, required_distance=500, required_ratio=2.5):

    affiche(trace, "Calcul decret 2015 1610 sur %d voyages." % (len(trips)))
    if len(trips) == 0:
        affiche(trace, "Aucun voyages, impossible de calculer.")
        return None, None, None

    affiche(trace, "Calcul de l'espacement moyen des arrêts...")
    espacement_moyen = 0
    w_esp = 0
    for trip in trips:
        # Note: on pondère par le nombre de jours chaque voyage est applicable.
        # Ceci permet de prendre en compte la fréquence: par exemple, la distance
        # d'un intervalle entre deux arrêt actif le lundi uniquement sera pondéré
        # 5 fois moins qu'un autre intervalle actif du lundi au vendredi.
        n_jours = len(trip.calendar.dates)
        for stoptime1, stoptime2 in trip.hops():
            espacement_moyen += (stoptime2.shape_dist_traveled - stoptime1.shape_dist_traveled) * n_jours
            w_esp += n_jours
    espacement_moyen /= w_esp
    affiche(trace, "L'espacement moyen entre arrêt du réseau est de %.2f mètres (max %.0fm)." % (espacement_moyen, float(required_distance)))

    affiche(trace, "Calcul du jour ayant la fréquence en voyage la plus élevée...")
    frequences = defaultdict(lambda: 0)
    for trip in trips:
        for date in trip.calendar.dates:
            frequences[date] += 1
    date_max = None
    freq_max = 0
    for date, frequence in frequences.items():
        if frequence > freq_max:
            freq_max = frequence
            date_max = date
    affiche(trace, "Le jour ayant le nombre de voyage le plus élevé est le %s, avec %d voyages." % (date_max.as_date(), freq_max))

    affiche(trace, "Calcul des fréquences sur la plage horaire 8h - 19h...")
    # TODO Est-ce que ce calcul est correct? Le décret est pas clair.
    # On calcule le nombre de voyages actifs pendant chaque minute.
    frequences = [ 0 for minute in range(0, 20 * 60) ]
    for trip in trips:
        if date_max not in trip.calendar.dates:
            continue
        minute_depart = trip.stop_times[0].departure_time // 60
        minute_arrivee = trip.stop_times[-1].arrival_time // 60
        for minute in range(minute_depart, minute_arrivee + 1):
            if minute >= 8 * 60 and minute < 20 * 60:
                frequences[minute] += 1
    frequence_min = 99999999999
    minute_min = 0
    frequence_max = 0
    minute_max = 0
    # La fréquence horaire min/max est calculé en moyenne glissante
    # sur une heure en sommant les fréquences par minute.
    for minute in range(8 * 60, 19 * 60):
        freq = 0
        for delta_minute in range(0, 60):
            freq += frequences[minute + delta_minute]
        if freq > frequence_max:
            frequence_max = freq
            minute_max = minute
        if freq < frequence_min:
            frequence_min = freq
            minute_min = minute
    affiche(trace, "La fréquence minimale est de %.2f voyages/heure, entre %s et %s." % (frequence_min / 60.0, fmttime(minute_min * 60), fmttime((minute_min + 60) * 60)))
    affiche(trace, "La fréquence maximale est de %.2f voyages/heure, entre %s et %s." % (frequence_max / 60.0, fmttime(minute_max * 60), fmttime((minute_max + 60) * 60)))
    if frequence_min == 0:
        ratio_frequence = float('inf')
    else:
        ratio_frequence = frequence_max / float(frequence_min)
    affiche(trace, "Le ratio entre fréquence max et min est de %.3f (max %.2f)." % (ratio_frequence, float(required_ratio)))

    urbain = ratio_frequence < required_ratio and espacement_moyen < required_distance
    affiche(trace, "Ce service est %s au sens du décret n° 2015-1610."
          % ("URBAIN" if urbain else "NON URBAIN"))
    return urbain, espacement_moyen, ratio_frequence

def affiche(affiche, message):
    if affiche:
        print(message)

class Decret_2015_1610(object):
    """
    Teste un ensemble de voyages (trips) par rapport au décret n° 2015-1610
    du 8 décembre 2015 relatif aux critères d'espacement moyen des arrêts
    et de variation de la fréquence de passage des services réguliers de
    transport public routier urbain de personnes. Pour plus d'informations:
    http://www.legifrance.gouv.fr/affichTexte.do?cidTexte=JORFTEXT000031589954

    Paramètres:
    --distance=<dist>   Distance minimale moyenne entre arrêts.
                        Valeur par défaut (décret): 500m
    --ratio=<ratio>     Ratio entre fréquence horaire minimale et maximale.
                        Valeur par défaut (décret): 2.5
    """
    def run(self, context, distance=500, ratio=2.5, **kwargs):
        print("Chargement des données...")
        trips = context.dao().trips(fltr=context.args.filter, prefetch_stop_times=True, prefetch_calendars=True, prefetch_stops=False)
        trips = list(trips)
        urbain = decret_2015_1610(trips, trace=True, required_distance=float(distance), required_ratio=float(ratio))
        return urbain
