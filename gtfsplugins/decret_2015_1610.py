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
def decret_2015_1610(trips):

    print("Calcul decret 2015 1610.")

    print("Calcul de l'espacement moyen des arrêts...")
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
    print("L'espacement moyen entre arrêt du réseau est de %.2f mètres (max 500m)." % espacement_moyen)

    print("Calcul du jour ayant la fréquence en voyage la plus élevée...")
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
    print("Le jour ayant le nombre de voyage le plus élevé est le %s, avec %d voyages." % (date_max.as_date(), freq_max))

    print("Calcul des fréquences sur la plage horaire 8h - 19h...")
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
    print("La fréquence minimale est de %.2f voyages/heure, entre %s et %s." % (frequence_min / 60.0, fmttime(minute_min * 60), fmttime((minute_min + 60) * 60)))
    print("La fréquence maximale est de %.2f voyages/heure, entre %s et %s." % (frequence_max / 60.0, fmttime(minute_max * 60), fmttime((minute_max + 60) * 60)))
    if frequence_min == 0:
        ratio_frequence = float('inf')
    else:
        ratio_frequence = frequence_max / float(frequence_min)
    print("Le ratio entre fréquence max et min est de %.3f (max 2.5)." % ratio_frequence)

    urbain = ratio_frequence < 2.5 and espacement_moyen < 500
    print("Ce service est %s au sens du décret n° 2015-1610."
          % ("URBAIN" if urbain else "NON URBAIN"))
    return urbain

class Decret_2015_1610(object):
    """
    Teste un ensemble de voyages (trips) par rapport au décret n° 2015-1610 du 8 décembre 2015
    relatif aux critères d'espacement moyen des arrêts et de variation de la fréquence de
    passage des services réguliers de transport public routier urbain de personnes.
    Pour plus d'informations:
    http://www.legifrance.gouv.fr/affichTexte.do?cidTexte=JORFTEXT000031589954
    """
    def run(self, context, **kwargs):
        trips = context.filter_trips(prefetch_stop_times=True, prefetch_calendars=True)
        urbain = decret_2015_1610(trips)
        return urbain
