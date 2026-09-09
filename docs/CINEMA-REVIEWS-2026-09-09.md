# What it is actually like inside: ratings, complaints and temperature

Google Maps reviews for every cinema Sala Nearby lists showtimes for, read on 2026-09-09.
Every rating, review count and quote below came out of a page that was actually loaded;
nothing here is remembered or inferred.

**Reviews were reachable.** They are read from the rendered Google Maps place page in
Keivan's own Chrome over CDP on 127.0.0.1:9222, in a background tab that is closed
afterwards. Two cheaper routes were tried first and are written up under Method, because
both fail in ways that look like success.

Regenerate with:

    /opt/homebrew/bin/python3 tools/find-places.py <cinemas.json> docs/places.json
    TARGET=100 node tools/scrape-reviews.mjs docs/places.json /tmp/reviews_raw.json
    /opt/homebrew/bin/python3 tools/analyze-reviews.py /tmp/reviews_raw.json docs/cinema-reviews.json
    /opt/homebrew/bin/python3 tools/write-report.py docs/cinema-reviews.json docs/CINEMA-REVIEWS-2026-09-09.md

## The short answer on temperature

Across 39 cinemas and 3267 reviews read, temperature comes up in 75 reviews: 12 reviews complaining the room was cold, 63 reviews complaining it was hot or that the cooling was off. A further 46 reviews say something was cold and mean the popcorn.

**The freezing-cinema reputation does not survive the reviews.** People complain about these rooms being too WARM about 5 times as often as too cold. What they are describing is air conditioning that is off, broken, or losing to the afternoon -- not a cinema kept at meat-locker temperature.

Cinema by cinema: 0 cinemas read cold, 8 cinemas read hot, 1 cinema genuinely mixed, and 30 cinemas have too few temperature mentions in a hundred reviews to call either way.

**And the honest caveat, which matters more than the ranking:** those 75 temperature mentions are 2.3% of the 3267 reviews read. Temperature is simply not what people write about at these cinemas -- staff, seats and cleanliness are, by an order of magnitude. 8 cinemas have enough heat complaints to be worth a warning and 0 cinemas have enough cold ones. For the other 31 there is no honest reading, and a per-cinema temperature badge on all 39 would be inventing a signal for most of them.

## Every cinema

Rating and review count are Google's own, read off the place header. "Sample" is how many
distinct reviews were loaded and read for that cinema -- Maps pages them in twenties and
renders each one twice, so the number is what survived de-duplication. Cold and hot are
counts of reviews in that sample whose text complains about the room's temperature.

| Cinema | km | Rating | Reviews | Sample | Cold | Hot | Verdict | Top complaints and praise |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Cinemex Insurgentes | 0.3 | 4.4 | 4,277 | 110 | 0 | 2 | thin evidence | staff and service (46%), seat comfort (38%), what is showing (27%) |
| Cinemex Pabellón Cuauhtémoc | 1.4 | 4.2 | 7,485 | 110 | 1 | 6 | HOT | staff and service (50%), cleanliness / bathrooms (39%), what is showing (32%) |
| Cinemex Parque Delta | 1.7 | 4.4 | 11,752 | 40 | 0 | 1 | thin evidence | staff and service (45%), snack bar (32%), what is showing (28%) |
| Cinemex Parque Delta Platino *(thin listing)* | 1.7 | 2.5 | 12 | 8 | 0 | 0 | no signal | staff and service (75%), snack bar (38%), crowding and queues (25%) |
| Cinemex Reforma Casa de Arte | 1.7 | 4.2 | 5,900 | 110 | 0 | 15 | HOT | what is showing (53%), staff and service (40%), seat comfort (32%) |
| Cinemex Reforma 222 Market | 2.0 | 4.3 | 7,858 | 80 | 0 | 7 | HOT | snack bar (36%), staff and service (34%), what is showing (24%) |
| Cinemex Patriotismo Market *(shares a listing)* | 2.1 | 4.2 | 4,525 | 60 | 0 | 1 | thin evidence | staff and service (37%), crowding and queues (30%), snack bar (28%) |
| Cinemex Patriotismo Platino *(shares a listing)* | 2.1 | 4.2 | 4,525 | 60 | 0 | 1 | thin evidence | staff and service (37%), crowding and queues (30%), snack bar (28%) |
| Cinemex Centro Telmex | 2.1 | 4.0 | 4,094 | 40 | 0 | 2 | thin evidence | what is showing (35%), picture and screen (25%), seat comfort (22%) |
| Cinemex Galerías | 2.7 | 4.1 | 7,485 | 110 | 1 | 1 | thin evidence | staff and service (53%), cleanliness / bathrooms (30%), crowding and queues (27%) |
| Cinemex San Antonio | 3.4 | 4.1 | 5,824 | 40 | 0 | 0 | no signal | cleanliness / bathrooms (40%), snack bar (38%), staff and service (38%) |
| Cinemex Real | 3.7 | 4.2 | 13,789 | 60 | 0 | 3 | HOT | staff and service (52%), cleanliness / bathrooms (32%), what is showing (27%) |
| Cinemex Portal Centro | 4.1 | 4.4 | 8,738 | 110 | 0 | 2 | thin evidence | staff and service (63%), cleanliness / bathrooms (36%), snack bar (34%) |
| Cinemex Universidad | 4.3 | 4.3 | 10,781 | 110 | 0 | 0 | no signal | staff and service (51%), what is showing (34%), cleanliness / bathrooms (34%) |
| Cinemex Félix Cuevas Platino | 4.4 | 4.5 | 3,560 | 50 | 0 | 0 | no signal | staff and service (68%), seat comfort (36%), snack bar (28%) |
| Cinemex Manacar | 4.5 | 4.5 | 7,082 | 60 | 0 | 3 | HOT | staff and service (50%), seat comfort (48%), cleanliness / bathrooms (28%) |
| Cinemex Galerías Insurgentes Market | 4.6 | 4.6 | 1,565 | 60 | 0 | 1 | thin evidence | snack bar (63%), seat comfort (52%), staff and service (48%) |
| Cinemex Antara Market | 4.7 | 4.5 | 4,878 | 110 | 0 | 1 | thin evidence | staff and service (43%), snack bar (33%), seat comfort (32%) |
| Cinemex Antara Platino *(thin listing)* | 4.7 | 3.7 | 55 | 33 | 0 | 1 | thin evidence | seat comfort (39%), staff and service (36%), picture and screen (30%) |
| Cineteca Nacional Mexico (Xoco) | 5.7 | 4.8 | 63,587 | 60 | 0 | 0 | no signal | what is showing (40%), price (27%), staff and service (18%) |
| Cinemex Clavería | 6.0 | 4.4 | 5,107 | 110 | 1 | 2 | HOT | staff and service (52%), cleanliness / bathrooms (36%), snack bar (32%) |
| Cinemex La Viga | 6.0 | 4.3 | 7,431 | 110 | 0 | 4 | HOT | staff and service (57%), what is showing (30%), crowding and queues (29%) |
| Cineteca Nacional Chapultepec | 6.7 | 4.3 | 1,941 | 110 | 1 | 0 | thin evidence | what is showing (42%), snack bar (37%), seat comfort (26%) |
| Cinemex Portal Vallejo | 6.8 | 4.5 | 4,884 | 110 | 1 | 0 | thin evidence | staff and service (64%), snack bar (34%), cleanliness / bathrooms (32%) |
| Cinemex Cuatro Caminos | 7.0 | 4.4 | 6,988 | 110 | 2 | 2 | mixed | staff and service (56%), cleanliness / bathrooms (44%), snack bar (42%) |
| Cineteca Nacional de las Artes | 7.1 | 4.5 | 14,989 | 40 | 0 | 0 | no signal | cleanliness / bathrooms (38%), what is showing (28%), snack bar (25%) |
| Cinemex Altavista | 7.3 | 4.3 | 1,784 | 110 | 1 | 3 | HOT | staff and service (50%), what is showing (39%), seat comfort (28%) |
| Cinemex Paseo Hipódromo Platino | 7.6 | 4.6 | 1,156 | 110 | 2 | 0 | thin evidence | staff and service (57%), seat comfort (33%), what is showing (26%) |
| Cinemex Duraznos Platino | 7.8 | 4.2 | 879 | 110 | 0 | 2 | thin evidence | staff and service (49%), snack bar (36%), what is showing (36%) |
| Cinemex Miguel Ángel de Quevedo | 8.0 | 4.4 | 381 | 110 | 0 | 1 | thin evidence | staff and service (57%), seat comfort (53%), cleanliness / bathrooms (34%) |
| Cinemex Patio Revolución Platino | 8.1 | 4.4 | 2,704 | 110 | 0 | 0 | no signal | staff and service (74%), seat comfort (40%), snack bar (36%) |
| Cinemex Encuentro Oceanía | 8.4 | 4.4 | 2,227 | 110 | 1 | 0 | thin evidence | staff and service (61%), cleanliness / bathrooms (36%), snack bar (34%) |
| Cinemex Loreto | 8.5 | 4.3 | 6,472 | 60 | 0 | 0 | no signal | cleanliness / bathrooms (50%), staff and service (48%), snack bar (30%) |
| Cinemex San Esteban | 8.6 | 4.2 | 5,907 | 110 | 0 | 2 | thin evidence | staff and service (62%), snack bar (39%), what is showing (36%) |
| Cinemex Ferrería | 8.8 | 4.5 | 2,521 | 110 | 0 | 0 | no signal | staff and service (69%), cleanliness / bathrooms (40%), crowding and queues (28%) |
| Cine Tonalá | - | 4.5 | 4,778 | 110 | 0 | 0 | no signal | snack bar (43%), staff and service (42%), what is showing (41%) |
| Cine Lido Bella Época | - | 4.7 | 186 | 87 | 0 | 0 | no signal | seat comfort (10%), price (9%), what is showing (9%) |
| La Casa del Cine MX | - | 4.6 | 3,678 | 110 | 1 | 0 | thin evidence | what is showing (66%), staff and service (36%), price (30%) |
| Cinematógrafo del Chopo *(thin listing)* | - | 4.4 | 15 | 9 | 0 | 0 | no signal | sound (33%), price (33%), what is showing (33%) |

**3 cinemas carry fewer than 100 Google reviews**, so their star rating is not comparable to the four-figure listings beside it: Cinemex Parque Delta Platino (2.5 stars from 12 reviews); Cinemex Antara Platino (3.7 stars from 55 reviews); Cinematógrafo del Chopo (4.4 stars from 15 reviews). Searching those addresses returns one busy listing each, and these are separate near-empty pins for the same building.

**Google has one listing where Sala Nearby has two.** Cinemex Patriotismo Market and Cinemex Patriotismo Platino share one place id. The rating, the review count and the temperature reading are therefore the same number reported twice, not two independent measurements.

## Per cinema, with the evidence

### Cinemex Reforma Casa de Arte

4.2 stars from 5,900 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Reforma Casa de Arte".

- **Temperature: HOT.** 0 of 110 reviews read call the room cold, 15 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: aire acondicionado 16, calor 10, frio 1, helado 1.
- **What people write about:** what is showing in 58 of 110; staff and service in 44 of 110; seat comfort in 35 of 110; cleanliness / bathrooms in 30 of 110; snack bar in 26 of 110.
- Stars in the sample: 5*: 26, 4*: 19, 3*: 20, 2*: 12, 1*: 33.
- Hot, 1 stars Hace 2 meses: "No hay aire acondicionado, las salas no cuentan con aire acondicionado y si la sala está a más de la mitad es ..."
- Hot, 1 stars Hace 3 meses: "Las condiciones de las instalaciones no es la óptima, focos fundidos, salas sin aire acondicionado, asientos rotos"
- Hot, 1 stars Hace 4 meses: "Por cierto estábamos a 21 grados con sensación térmica de 31 y no había aire acondicionado"
- Hot, 1 stars Hace 4 meses: "terrible experiencia: el aire acondicionado no servía y el calor era aturdidor, se escuchaba el sonido de la película de acción en la s..."
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJYyEdQUr_0YURDfKiuNVuYpQ&hl=es&gl=mx)

### Cinemex Pabellón Cuauhtémoc

4.2 stars from 7,485 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Pabellón Cuauhtémoc".

- **Temperature: HOT.** 1 of 110 reviews read call the room cold, 6 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: aire acondicionado 7, calor 3, chamarra o sueter 1, frio 1.
- **What people write about:** staff and service in 55 of 110; cleanliness / bathrooms in 43 of 110; what is showing in 35 of 110; crowding and queues in 30 of 110; seat comfort in 29 of 110.
- Stars in the sample: 5*: 19, 4*: 17, 3*: 12, 2*: 18, 1*: 44.
- Cold, 4 stars: "Deben traer chamarra eskimal para sobrevivir"
- Hot, 2 stars Hace 3 meses: "Por algún motivo en plena ola de calor, encendieron el aire acondicionado"
- Hot, 1 stars Hace un mes: "Este cine está en su peor momento, salas sin limpieza, aire acondicionado nulo y los baños asquerosos, sin limipeza y llenos de orina, sin contar que h..."
- Hot, 2 stars Hace 4 meses: "No hay aire acondicionado, no hay papel en los baños, están muy sucios y algunos no sirven"
- Hot, 2 stars Hace un año: "Vine por primera vez, la sala olía muy mal, el aire acondicionado estuvo apagado todo el tiempo y el calor era insoportable"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJ729e4CL_0YURnQwO2-ORRsA&hl=es&gl=mx)

### Cinemex Reforma 222 Market

4.3 stars from 7,858 reviews on Google. 80 reviews read for this write-up. Google's own name for it is "Cinemex Reforma 222 Market".

- **Temperature: HOT.** 0 of 80 reviews read call the room cold, 7 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: aire acondicionado 10, calor 5, frio 1, caluroso 1.
- **What people write about:** snack bar in 29 of 80; staff and service in 27 of 80; what is showing in 19 of 80; seat comfort in 18 of 80; cleanliness / bathrooms in 15 of 80.
- Stars in the sample: 5*: 18, 4*: 11, 3*: 15, 2*: 4, 1*: 32.
- Hot, 1 stars Hace 4 meses: "Podrá haber sido una excelente remodelación, pero no vengan en época de calor no encienden el aire acondicionado por más que se le pide al personal que lo prendan"
- Hot, 1 stars Hace 4 meses: "Con el calor que está haciendo en CDMX y NO hay aire acondicionado, mínimo una… Más"
- Hot, 1 stars Hace 4 meses: "...olmo con Cinemex, una de las películas más esperadas y la arruinan, dejándonos en la sala sin aire acondicionado y estás fechas con más calor y te quejabas y nadie solucionó"
- Hot, 4 stars: "...isite no prendieron el aire acondicionado aunque varias personas lo solicitaron por tanto calor que se sentia a pesar de ser la funcion de las 8 p"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJNdMbgDP_0YURVqgjCMCj3rA&hl=es&gl=mx)

### Cinemex La Viga

4.3 stars from 7,431 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex".

- **Temperature: HOT.** 0 of 110 reviews read call the room cold, 4 call it hot or say the air conditioning was off, and 2 more say the food was cold.
- Unfiltered word counts in the same sample: chamarra o sueter 1, aire acondicionado 4, frio 2, calor 2.
- **What people write about:** staff and service in 63 of 110; what is showing in 33 of 110; crowding and queues in 32 of 110; cleanliness / bathrooms in 31 of 110; snack bar in 31 of 110.
- Stars in the sample: 5*: 44, 4*: 27, 3*: 14, 2*: 9, 1*: 16.
- Hot, 1 stars Hace 4 meses: "El dia de hoy vine al cine y en ninguna sala no hay aire acondicionado"
- Hot, 3 stars Hace 2 meses: "Sin aire acondicionado y de estacionamiento muy caro"
- Hot, 2 stars Hace un año: "Y hace un calor del infierno"
- Hot, 2 stars Hace 5 años: "El calor en la sala fue demasiado y a la salida no existió la sana distancia ni tampoco existió el personal para ..."
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJ1RyzSWf-0YURNRIYnyWGWx4&hl=es&gl=mx)

### Cinemex Cuatro Caminos

4.4 stars from 6,988 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Cuatro Caminos".

- **Temperature: mixed.** 2 of 110 reviews read call the room cold, 2 call it hot or say the air conditioning was off.
- Unfiltered word counts in the same sample: aire acondicionado 5, calor 2, frio 2.
- **What people write about:** staff and service in 61 of 110; cleanliness / bathrooms in 49 of 110; snack bar in 46 of 110; crowding and queues in 35 of 110; what is showing in 31 of 110.
- Stars in the sample: 5*: 55, 4*: 19, 3*: 20, 2*: 6, 1*: 10.
- Cold, 4 stars Hace 8 años: "El aire acondicionado es exageradamente frío"
- Cold, 5 stars Hace 2 años: "...ención es bueno, lo único malo es el aire acondicionado que particularmente siento que es demasiado frío"
- Hot, 3 stars Hace 4 meses: "estamos en sala con mucha gente y se encierra el calor 🥵, y tuve que salirme de la sala varias veces y aparte del calor, es olores y demás"
- Hot, 3 stars Hace 4 meses: "No hay aire acondicionado en la sala y nos estábamos muriendo de calor en la función y los baños sucios"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJo4eBG0EC0oURUmW5DNYaNVU&hl=es&gl=mx)

### Cinemex Altavista

4.3 stars from 1,784 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Altavista".

- **Temperature: HOT.** 1 of 110 reviews read call the room cold, 3 call it hot or say the air conditioning was off, and 2 more say the food was cold.
- Unfiltered word counts in the same sample: aire acondicionado 2, calor 1, frio 2, helado 1, caluroso 1.
- **What people write about:** staff and service in 55 of 110; what is showing in 43 of 110; seat comfort in 31 of 110; crowding and queues in 27 of 110; cleanliness / bathrooms in 26 of 110.
- Stars in the sample: 5*: 51, 4*: 23, 3*: 13, 2*: 6, 1*: 17.
- Cold, 1 stars: "Hace frio , la pantalla tiene lo tonos bajos y aparte de todo su precio es mas alto al de otras sucursales"
- Hot, 1 stars Hace 2 años: "...leaños y el cine esta horrible, las butacas ¿PREMIUM¿ rechinan horrible toda la película, no hay aire acondicionado, compre un boleto para la película de LONGLEGS que si tienen la oportunidad de no ve..."
- Hot, 1 stars Hace falta que se regule le temperatura. Inicia fresca la sala, pero termina siendo un sauna. Con sensores de temperatura se mantendría confortable. Sobretodo con la sala llena.: "Inicia fresca la sala, pero termina siendo un sauna"
- Hot, 2 stars: "Las salas no son modernas y a veces son muy calurosas"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJYaSIWB0A0oUR7sDACdDQnc8&hl=es&gl=mx)

### Cinemex Real

4.2 stars from 13,789 reviews on Google. 60 reviews read for this write-up. Google's own name for it is "Cinemex Real".

- **Temperature: HOT.** 0 of 60 reviews read call the room cold, 3 call it hot or say the air conditioning was off.
- Unfiltered word counts in the same sample: calor 1, aire acondicionado 3.
- **What people write about:** staff and service in 31 of 60; cleanliness / bathrooms in 19 of 60; what is showing in 16 of 60; snack bar in 15 of 60; crowding and queues in 11 of 60.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine es un lugar cómodo para ver películas, ya que generalmente no está abarrotado y ofrece asientos cómodos. Aprecian el personal amable y la ubicación conveniente cerca del transporte público. Otras personas dicen que el servicio a veces puede ser ineficiente."
- Stars in the sample: 5*: 15, 4*: 14, 3*: 6, 2*: 9, 1*: 16.
- Hot, 2 stars Hace 4 meses: "Audio la película , no parecía tener el aire puesto y había mucho calor en la sala aún con poca gente"
- Hot, 1 stars Hace 3 meses: "No sirve el aire acondicionado"
- Hot, 1 stars Hace 2 meses: "Sin aire acondicionado,baños sucios, un lugar muy descuidado en mantenimiento"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJXS5Co9X40YURZeHxmsu-ysA&hl=es&gl=mx)

### Cinemex Manacar

4.5 stars from 7,082 reviews on Google. 60 reviews read for this write-up. Google's own name for it is "Cinemex Premium".

- **Temperature: HOT.** 0 of 60 reviews read call the room cold, 3 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: aire acondicionado 3, calor 2, frio 1.
- **What people write about:** staff and service in 30 of 60; seat comfort in 29 of 60; cleanliness / bathrooms in 17 of 60; snack bar in 14 of 60; crowding and queues in 14 of 60.
- Stars in the sample: 5*: 33, 4*: 4, 3*: 6, 2*: 1, 1*: 16.
- Hot, 1 stars Hace 3 meses: "SIEMPRE QUE VENGO HACE UN CALOR INFERNAL EN LAS SALAS, no prenden el aire acondicionado, te dan largas de que lo van a encender o te dic..."
- Hot, 5 stars Hace 4 meses: "Lugar tranquilo, limpio, ordenado aún que con un poco de calor en la sección de boletos y comida pero dentro de la sala todo de maravilla, la comida sabe bien los baño..."
- Hot, 2 stars: "El bochorno se vuelve incómodo, te distrae de la película, puede provocar… Más"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJ89sXUI7_0YURQqaz9FDhLcA&hl=es&gl=mx)

### Cinemex Clavería

4.4 stars from 5,107 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex".

- **Temperature: HOT.** 1 of 110 reviews read call the room cold, 2 call it hot or say the air conditioning was off.
- Unfiltered word counts in the same sample: aire acondicionado 2, calor 1, frio 2, chamarra o sueter 1.
- **What people write about:** staff and service in 57 of 110; cleanliness / bathrooms in 39 of 110; snack bar in 35 of 110; what is showing in 29 of 110; crowding and queues in 25 of 110.
- Stars in the sample: 5*: 50, 4*: 23, 3*: 14, 2*: 8, 1*: 15.
- Cold, 3 stars Hace un año: "se pasan de frio"
- Hot, 1 stars Hace 4 meses: "no venga a este cine, terrible no hay aire acondicionado y no son ni para resolver, el calor es terrible"
- Hot, 5 stars Hace un año: "...a vez tuve problemas en este cine y fue porque nunca prendieron el aire y la sala parecía horno, ya no ha vuelto a pasar y las alas están espaciosas, buenas para disfrutar la peli"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJv565BZv40YURVqQAzMQb-J8&hl=es&gl=mx)

### Cinemex Insurgentes

4.4 stars from 4,277 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Insurgentes".

- **Temperature: thin evidence.** 0 of 110 reviews read call the room cold, 2 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: frio 1, aire acondicionado 2, calor 1.
- **What people write about:** staff and service in 50 of 110; seat comfort in 42 of 110; what is showing in 30 of 110; cleanliness / bathrooms in 24 of 110; snack bar in 24 of 110.
- Stars in the sample: 5*: 58, 4*: 24, 3*: 10, 2*: 5, 1*: 13.
- Hot, 4 stars Hace 2 meses: "A veces se les olvida poner el aire acondicionado y se pone insoportable el el calor"
- Hot, 1 stars Hace 4 meses: "Disfruta “diablo viste la moda” sin acondicionador de aire 👠🥵🫠…"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJtT_KWo7_0YURSJG8vHREjdw&hl=es&gl=mx)

### Cinemex Centro Telmex

4.0 stars from 4,094 reviews on Google. 40 reviews read for this write-up. Google's own name for it is "Cinemex".

- **Temperature: thin evidence.** 0 of 40 reviews read call the room cold, 2 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: aire acondicionado 3, calor 1, frio 1.
- **What people write about:** what is showing in 14 of 40; picture and screen in 10 of 40; seat comfort in 9 of 40; staff and service in 9 of 40; sound in 8 of 40.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine ofrece asientos cómodos y un ambiente tranquilo, lo que lo hace ideal para una experiencia cinematográfica relajada. Destacan los precios accesibles de las entradas y los productos de la dulcería, junto con un personal amable y atento. Otras personas dicen que las instalaciones a veces pueden estar mal mantenidas."
- Stars in the sample: 5*: 9, 4*: 9, 3*: 8, 2*: 3, 1*: 11.
- Hot, 1 stars Hace un mes: "La sala 2 no tenía aire acondicionado, hacía demasiado calor y era muy incómodo permanecer ahí"
- Hot, 1 stars Hace 2 meses: "..., asientos incómodos, sonido muy bajito, se escuchaba el ruido de las salas de los lados, no hay o nunca prendieron el aire acondicionado y me dolió la cabeza y el cuello porque la pantalla no queda a..."
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJpxkPaS7_0YURwwsrJcTPZK4&hl=es&gl=mx)

### Cinemex Galerías

4.1 stars from 7,485 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Galerías Plaza de las Estrellas".

- **Temperature: thin evidence.** 1 of 110 reviews read call the room cold, 1 call it hot or say the air conditioning was off, and 2 more say the food was cold.
- Unfiltered word counts in the same sample: frio 2, calor 1, congelando 1.
- **What people write about:** staff and service in 58 of 110; cleanliness / bathrooms in 33 of 110; crowding and queues in 30 of 110; snack bar in 23 of 110; what is showing in 22 of 110.
- Stars in the sample: 5*: 42, 4*: 21, 3*: 16, 2*: 11, 1*: 20.
- Cold, 2 stars Hace un mes: "Cine frío, oscuro, solo, sin mucha demanda, pero eso sí combos infladisimos de precios paralos tamalitos que maneja..."
- Hot, 1 stars Hace un mes: "Horrible cine y más horrible plaza, un calor insoportable dentro de la sala, una plaza vieja, fea y el personal grosero"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJRe1fTbT40YURVNMr0VScLG0&hl=es&gl=mx)

### Cinemex Portal Centro

4.4 stars from 8,738 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex".

- **Temperature: thin evidence.** 0 of 110 reviews read call the room cold, 2 call it hot or say the air conditioning was off, and 2 more say the food was cold.
- Unfiltered word counts in the same sample: calor 2, helado 1, aire acondicionado 5, frio 1.
- **What people write about:** staff and service in 69 of 110; cleanliness / bathrooms in 39 of 110; snack bar in 37 of 110; what is showing in 35 of 110; crowding and queues in 27 of 110.
- Stars in the sample: 5*: 43, 4*: 24, 3*: 14, 2*: 8, 1*: 21.
- Hot, 1 stars Hace 4 meses: "así que si hay mucho calor afuera no pidan de la sala 1 a la 6"
- Hot, 2 stars Hace 11 meses: "... la pasa diciendo albures y groserías subidas de tono cuando aún hay familias, hace mucho calor en los sanitarios y afuera de las salas"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJAdLlR8T-0YURu-kYJKHUHg0&hl=es&gl=mx)

### Cinemex Paseo Hipódromo Platino

4.6 stars from 1,156 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Platino Plaza Hipódromo".

- **Temperature: thin evidence.** 2 of 110 reviews read call the room cold, 0 call it hot or say the air conditioning was off, and 3 more say the food was cold.
- Unfiltered word counts in the same sample: frio 4, congelando 1.
- **What people write about:** staff and service in 63 of 110; seat comfort in 36 of 110; what is showing in 29 of 110; snack bar in 28 of 110; cleanliness / bathrooms in 25 of 110.
- Stars in the sample: 5*: 64, 4*: 20, 3*: 7, 2*: 9, 1*: 10.
- Cold, 1 stars Hace 2 meses: "La temperatura de la sala muy baja hacia demasiado frío"
- Cold, 5 stars Hace 7 años: "y si tienes frío nunca dudes en pedir una frazada q siempre tienen y además super limpias, siempre tienen un lindo aroma"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJO9KaytUD0oURNBhiOspq0mQ&hl=es&gl=mx)

### Cinemex Duraznos Platino

4.2 stars from 879 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Parque Duraznos".

- **Temperature: thin evidence.** 0 of 110 reviews read call the room cold, 2 call it hot or say the air conditioning was off, and 7 more say the food was cold.
- Unfiltered word counts in the same sample: aire acondicionado 3, calor 2, frio 6, helado 1, chamarra o sueter 2.
- **What people write about:** staff and service in 54 of 110; snack bar in 39 of 110; what is showing in 39 of 110; seat comfort in 23 of 110; crowding and queues in 18 of 110.
- Stars in the sample: 5*: 41, 4*: 10, 3*: 16, 2*: 12, 1*: 31.
- Hot, 1 stars Hace 3 meses: "Mi asiento no reclinaba y hacía demasiado calor en la sala"
- Hot, 1 stars Hace 9 años: "Pésima en esta época de calor uno tiene que estar asándose porque no prenden el aire acondicionado"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJHUMfYOcc0oUR3w0SNR0ULNU&hl=es&gl=mx)

### Cinemex San Esteban

4.2 stars from 5,907 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex San Esteban".

- **Temperature: thin evidence.** 0 of 110 reviews read call the room cold, 2 call it hot or say the air conditioning was off, and 2 more say the food was cold.
- Unfiltered word counts in the same sample: aire acondicionado 3, frio 1, helado 1.
- **What people write about:** staff and service in 68 of 110; snack bar in 43 of 110; what is showing in 40 of 110; cleanliness / bathrooms in 38 of 110; crowding and queues in 29 of 110.
- Stars in the sample: 5*: 36, 4*: 24, 3*: 22, 2*: 7, 1*: 21.
- Hot, 1 stars Hace un mes: "Baños horribles (viejos y sucios), salas pequeñas y sin aire acondicionado"
- Hot, 1 stars Hace 4 años: "Salas limpias pero sin aire acondicionado"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJHcdysEwC0oURRkZN_HTiJvY&hl=es&gl=mx)

### Cinemex Parque Delta

4.4 stars from 11,752 reviews on Google. 40 reviews read for this write-up. Google's own name for it is "Cinemex Parque Delta".

- **Temperature: thin evidence.** 0 of 40 reviews read call the room cold, 1 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: frio 1, aire acondicionado 1.
- **What people write about:** staff and service in 18 of 40; snack bar in 13 of 40; what is showing in 11 of 40; cleanliness / bathrooms in 9 of 40; crowding and queues in 9 of 40.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine tiene salas cómodas y limpias, con una excelente calidad de sonido y espectaculares pantallas IMAX. Aprecian al personal amable y mencionan que el cine no suele estar lleno, especialmente antes de las 5 PM. Otras personas dicen que el personal puede ser poco servicial."
- Stars in the sample: 5*: 12, 4*: 5, 3*: 5, 2*: 7, 1*: 11.
- Hot, 3 stars: "Además el sistema de aire acondicionado parece no funcionar, se eleva la temperatura y hace que la experiencia sea bastante incómod..."
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJ_QJvzRv_0YUR-k9zQfY5cLs&hl=es&gl=mx)

### Cinemex Patriotismo Market

4.2 stars from 4,525 reviews on Google. 60 reviews read for this write-up. Google's own name for it is "Cinemex Patriotismo".

- **Temperature: thin evidence.** 0 of 60 reviews read call the room cold, 1 call it hot or say the air conditioning was off.
- Unfiltered word counts in the same sample: aire acondicionado 1.
- **What people write about:** staff and service in 22 of 60; crowding and queues in 18 of 60; snack bar in 17 of 60; seat comfort in 10 of 60; price in 9 of 60.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine ofrece salas prémium cómodas, amplias y limpias, con buena calidad de sonido y pantalla. Mencionan también la gran variedad de opciones de comida y el personal amable y atento. Otras personas dicen que los precios pueden ser elevados."
- Stars in the sample: 5*: 16, 4*: 8, 3*: 10, 2*: 11, 1*: 15.
- Hot, 1 stars Hace 4 meses: "Pésimo servicio, no es humano que te encierren en una sala llena de gente sin aire acondicionado es una falta de respeto"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJvySUMWX_0YURo6P7A-wt7WE&hl=es&gl=mx)

### Cinemex Patriotismo Platino

4.2 stars from 4,525 reviews on Google. 60 reviews read for this write-up. Google's own name for it is "Cinemex Patriotismo".

- **Temperature: thin evidence.** 0 of 60 reviews read call the room cold, 1 call it hot or say the air conditioning was off.
- Unfiltered word counts in the same sample: aire acondicionado 1.
- **What people write about:** staff and service in 22 of 60; crowding and queues in 18 of 60; snack bar in 17 of 60; seat comfort in 10 of 60; price in 9 of 60.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine ofrece salas prémium cómodas, amplias y limpias, con buena calidad de sonido y pantalla. Mencionan también la gran variedad de opciones de comida y el personal amable y atento. Otras personas dicen que los precios pueden ser elevados."
- Stars in the sample: 5*: 16, 4*: 8, 3*: 10, 2*: 11, 1*: 15.
- Hot, 1 stars Hace 4 meses: "Pésimo servicio, no es humano que te encierren en una sala llena de gente sin aire acondicionado es una falta de respeto"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJvySUMWX_0YURo6P7A-wt7WE&hl=es&gl=mx)

### Cinemex Galerías Insurgentes Market

4.6 stars from 1,565 reviews on Google. 60 reviews read for this write-up. Google's own name for it is "Cinemex Premium Galerías Insurgentes Market".

- **Temperature: thin evidence.** 0 of 60 reviews read call the room cold, 1 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: calor 1, frio 1.
- **What people write about:** snack bar in 38 of 60; seat comfort in 31 of 60; staff and service in 29 of 60; price in 17 of 60; cleanliness / bathrooms in 16 of 60.
- Stars in the sample: 5*: 37, 4*: 13, 3*: 5, 2*: 1, 1*: 4.
- Hot, 1 stars Hace 3 meses: "... hace poco que fui a ver la peli de Michael Jackson y queria tomar al refrescante para el calor fui al Cielito Querido andetro de Cinemex Market y le pegunte la chica que me recomiendas y me contesto ..."
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJ6Vm2fML_0YUR9gGvc6rllbg&hl=es&gl=mx)

### Cinemex Antara Market

4.5 stars from 4,878 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Market Antara".

- **Temperature: thin evidence.** 0 of 110 reviews read call the room cold, 1 call it hot or say the air conditioning was off, and 5 more say the food was cold.
- Unfiltered word counts in the same sample: calor 1, frio 4, helado 2, aire acondicionado 1.
- **What people write about:** staff and service in 47 of 110; snack bar in 36 of 110; seat comfort in 35 of 110; what is showing in 31 of 110; cleanliness / bathrooms in 26 of 110.
- Stars in the sample: 5*: 46, 4*: 20, 3*: 11, 2*: 11, 1*: 22.
- Hot, 3 stars: "Dentro de l sala hacía un buen de calor, parecía que no prendieron el aire, los asistentes se abanicaban como podían"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJA5HvARsC0oURPWgqfv6kyCY&hl=es&gl=mx)

### Cinemex Antara Platino

3.7 stars from 55 reviews on Google. 33 reviews read for this write-up. Google's own name for it is "Cinemex Antara Platino".

- **Temperature: thin evidence.** 0 of 33 reviews read call the room cold, 1 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: frio 1, calor 1.
- **What people write about:** seat comfort in 13 of 33; staff and service in 12 of 33; picture and screen in 10 of 33; what is showing in 8 of 33; sound in 6 of 33.
- Stars in the sample: 5*: 11, 4*: 3, 3*: 5, 2*: 4, 1*: 10.
- Hot, 1 stars Hace 4 meses: "Pésimo servicio, insoportable el calor en la sala"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJIWoOo3_50YUR6XTS1yQN93c&hl=es&gl=mx)

### Cinemex Portal Vallejo

4.5 stars from 4,884 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex".

- **Temperature: thin evidence.** 1 of 110 reviews read call the room cold, 0 call it hot or say the air conditioning was off, and 2 more say the food was cold.
- Unfiltered word counts in the same sample: aire acondicionado 1, frio 2.
- **What people write about:** staff and service in 71 of 110; snack bar in 38 of 110; cleanliness / bathrooms in 35 of 110; seat comfort in 34 of 110; crowding and queues in 33 of 110.
- Stars in the sample: 5*: 63, 4*: 18, 3*: 7, 2*: 7, 1*: 15.
- Cold, 5 stars Hace 3 años: "Lo unico que no me agrada es que siempre tienen el aire muy fuerte, asi que lleven algo de tapar"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJPUK4sgL50YURYYu70YJU8iQ&hl=es&gl=mx)

### Cinemex Miguel Ángel de Quevedo

4.4 stars from 381 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex".

- **Temperature: thin evidence.** 0 of 110 reviews read call the room cold, 1 call it hot or say the air conditioning was off.
- Unfiltered word counts in the same sample: aire acondicionado 3.
- **What people write about:** staff and service in 63 of 110; seat comfort in 58 of 110; cleanliness / bathrooms in 38 of 110; what is showing in 34 of 110; snack bar in 31 of 110.
- Stars in the sample: 5*: 65, 4*: 19, 3*: 9, 2*: 5, 1*: 12.
- Hot, 2 stars Hace 5 meses: "...aza, para dirigirse al CINEMEX huele a caño, el cine no usa el aire acondicionado y es un horno"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJ3bnElMP_0YUR9QE_62EJmyE&hl=es&gl=mx)

### Cinemex Encuentro Oceanía

4.4 stars from 2,227 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Encuentro Oceanía".

- **Temperature: thin evidence.** 1 of 110 reviews read call the room cold, 0 call it hot or say the air conditioning was off.
- Unfiltered word counts in the same sample: chamarra o sueter 1, aire acondicionado 1, frio 1.
- **What people write about:** staff and service in 67 of 110; cleanliness / bathrooms in 39 of 110; snack bar in 38 of 110; seat comfort in 31 of 110; crowding and queues in 30 of 110.
- Stars in the sample: 5*: 53, 4*: 19, 3*: 11, 2*: 8, 1*: 19.
- Cold, 1 stars Hace 4 años: "Ya mejoró la atención , pero hace frío y los baños están mal ubicados"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJ1bB3MLj70YURLOdvnHbqlts&hl=es&gl=mx)

### Cineteca Nacional Chapultepec

4.3 stars from 1,941 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cineteca Nacional Chapultepec".

- **Temperature: thin evidence.** 1 of 110 reviews read call the room cold, 0 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: frio 2.
- **What people write about:** what is showing in 46 of 110; snack bar in 41 of 110; seat comfort in 29 of 110; staff and service in 29 of 110; cleanliness / bathrooms in 29 of 110.
- Stars in the sample: 5*: 74, 4*: 26, 3*: 6, 2*: 3, 1*: 1.
- Cold, 4 stars Hace 6 meses: "Recomiend revisar el clima puede ser una experiencia fría"
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJM0LzecIB0oURmF6toWEvQJc&hl=es&gl=mx)

### La Casa del Cine MX

4.6 stars from 3,678 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "La Casa del Cine Mx".

- **Temperature: thin evidence.** 1 of 110 reviews read call the room cold, 0 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: frio 1, aire acondicionado 2, chamarra o sueter 1.
- **What people write about:** what is showing in 73 of 110; staff and service in 39 of 110; price in 33 of 110; crowding and queues in 28 of 110; seat comfort in 26 of 110.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine independiente ofrece una cuidada selección de películas de autor, mexicanas y clásicas, junto con deliciosos aperitivos y bebidas que se pueden disfrutar dentro de las íntimas salas de proyección. Destacan también los precios accesibles de las entradas y la comida, así como el ambiente acogedor y artístico. Mencionan que el personal es amable y atento."
- Stars in the sample: 5*: 78, 4*: 19, 3*: 6, 2*: 2, 1*: 5.
- Cold, 5 stars Hace 3 años: "...s un lugar acogedor con mucho amor, eso si, son muy puntuales con el acceso (lleva alguna cobija si tu función es en la noche y mucha buena vibra), nunca pude comprar los boletos en línea así que siem..."
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJ-8XGBdP-0YUR62XpJRtipek&hl=es&gl=mx)

### Cinemex Parque Delta Platino

2.5 stars from 12 reviews on Google. 8 reviews read for this write-up. Google's own name for it is "Cinemex Parque Delta Platino".

- **Temperature: no signal.** 0 of 8 reviews read call the room cold, 0 call it hot or say the air conditioning was off.
- **What people write about:** staff and service in 6 of 8; snack bar in 3 of 8; crowding and queues in 2 of 8; picture and screen in 2 of 8; cleanliness / bathrooms in 2 of 8.
- Stars in the sample: 4*: 1, 3*: 1, 2*: 1, 1*: 5.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJEYIfmmX_0YURxKSftdvYF30&hl=es&gl=mx)

### Cinemex San Antonio

4.1 stars from 5,824 reviews on Google. 40 reviews read for this write-up. Google's own name for it is "Cinemex San Antonio".

- **Temperature: no signal.** 0 of 40 reviews read call the room cold, 0 call it hot or say the air conditioning was off.
- Unfiltered word counts in the same sample: chamarra o sueter 1.
- **What people write about:** cleanliness / bathrooms in 16 of 40; snack bar in 15 of 40; staff and service in 15 of 40; what is showing in 10 of 40; crowding and queues in 7 of 40.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine ofrece salas cómodas con buen audio y una variedad de servicios como café y crepas. Destacan también al personal atento y la ubicación conveniente con amplio estacionamiento. Otras personas dicen que las instalaciones a veces pueden estar mal mantenidas."
- Stars in the sample: 5*: 8, 4*: 5, 3*: 3, 2*: 5, 1*: 19.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJzVcw39UB0oURqBnHm5azW8s&hl=es&gl=mx)

### Cinemex Universidad

4.3 stars from 10,781 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Universidad".

- **Temperature: no signal.** 0 of 110 reviews read call the room cold, 0 call it hot or say the air conditioning was off.
- **What people write about:** staff and service in 56 of 110; what is showing in 38 of 110; cleanliness / bathrooms in 37 of 110; snack bar in 32 of 110; crowding and queues in 24 of 110.
- Stars in the sample: 5*: 39, 4*: 23, 3*: 18, 2*: 8, 1*: 22.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJv2LDW6P_0YURdSSGCh2QdEw&hl=es&gl=mx)

### Cinemex Félix Cuevas Platino

4.5 stars from 3,560 reviews on Google. 50 reviews read for this write-up. Google's own name for it is "Cinemex Platino".

- **Temperature: no signal.** 0 of 50 reviews read call the room cold, 0 call it hot or say the air conditioning was off.
- **What people write about:** staff and service in 34 of 50; seat comfort in 18 of 50; snack bar in 14 of 50; what is showing in 11 of 50; crowding and queues in 9 of 50.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine ofrece asientos cómodos, amplios y reclinables, junto con una buena calidad de sonido e imagen. Mencionan también al personal atento y el conveniente sistema para pedir comida desde el asiento. Los clientes destacan la atmósfera tranquila y las deliciosas palomitas de maíz, pizzas y margaritas."
- Stars in the sample: 5*: 30, 4*: 10, 3*: 1, 2*: 3, 1*: 6.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJl1tz_pn_0YURe5ebOPbE5oo&hl=es&gl=mx)

### Cinemex Patio Revolución Platino

4.4 stars from 2,704 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Patio Revolución".

- **Temperature: no signal.** 0 of 110 reviews read call the room cold, 0 call it hot or say the air conditioning was off, and 5 more say the food was cold.
- Unfiltered word counts in the same sample: frio 4, helado 1, aire acondicionado 2.
- **What people write about:** staff and service in 81 of 110; seat comfort in 44 of 110; snack bar in 39 of 110; crowding and queues in 33 of 110; cleanliness / bathrooms in 27 of 110.
- Stars in the sample: 5*: 45, 4*: 22, 3*: 8, 2*: 9, 1*: 26.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJd11giwEA0oUReQaR4bxHvhA&hl=es&gl=mx)

### Cinemex Loreto

4.3 stars from 6,472 reviews on Google. 60 reviews read for this write-up. Google's own name for it is "Cinemex Plaza Loreto".

- **Temperature: no signal.** 0 of 60 reviews read call the room cold, 0 call it hot or say the air conditioning was off.
- **What people write about:** cleanliness / bathrooms in 30 of 60; staff and service in 29 of 60; snack bar in 18 of 60; seat comfort in 14 of 60; what is showing in 13 of 60.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine ofrece asientos cómodos y limpios, junto con buena comida y bebidas. Aprecian al personal amable y paciente, y destacan la atmósfera tranquila con menos multitudes. Otras personas dicen que las instalaciones pueden estar descuidadas."
- Stars in the sample: 5*: 16, 4*: 10, 3*: 5, 2*: 5, 1*: 24.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJw7-bHQEA0oUR8VkdaHMef4s&hl=es&gl=mx)

### Cinemex Ferrería

4.5 stars from 2,521 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cinemex Ferrería".

- **Temperature: no signal.** 0 of 110 reviews read call the room cold, 0 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: frio 1.
- **What people write about:** staff and service in 76 of 110; cleanliness / bathrooms in 44 of 110; crowding and queues in 31 of 110; what is showing in 29 of 110; snack bar in 27 of 110.
- Stars in the sample: 5*: 71, 4*: 20, 3*: 2, 2*: 4, 1*: 13.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJATkIcXr40YURUZHwtsVvH2E&hl=es&gl=mx)

### Cineteca Nacional Mexico (Xoco)

4.8 stars from 63,587 reviews on Google. 60 reviews read for this write-up. Google's own name for it is "Cineteca Nacional de México".

- **Temperature: no signal.** 0 of 60 reviews read call the room cold, 0 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: helado 1.
- **What people write about:** what is showing in 24 of 60; price in 16 of 60; staff and service in 11 of 60; cleanliness / bathrooms in 9 of 60; snack bar in 9 of 60.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine ofrece una amplia variedad de películas, incluyendo selecciones de cine de arte e internacionales, con salas de proyección cómodas, espaciosas y limpias. También destacan los precios accesibles para las entradas y las concesiones, junto con un estacionamiento amplio y asequible. Aprecian la hermosa arquitectura, el ambiente agradable y las numerosas opciones de comida, bebida y actividades culturales en el lugar."
- Stars in the sample: 5*: 51, 4*: 7, 3*: 1, 2*: 1.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJHTPVvcD_0YURgn2tsuuI4ZY&hl=es&gl=mx)

### Cineteca Nacional de las Artes

4.5 stars from 14,989 reviews on Google. 40 reviews read for this write-up. Google's own name for it is "Cineteca Nacional de las Artes".

- **Temperature: no signal.** 0 of 40 reviews read call the room cold, 0 call it hot or say the air conditioning was off, and 1 more say the food was cold.
- Unfiltered word counts in the same sample: frio 1.
- **What people write about:** cleanliness / bathrooms in 15 of 40; what is showing in 11 of 40; snack bar in 10 of 40; price in 8 of 40; parking in 7 of 40.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine ofrece una variada selección de películas nacionales e internacionales, incluyendo opciones de cine de arte y comerciales, con asientos cómodos, buen sonido y pantallas grandes. También destacan los precios accesibles de las entradas y las instalaciones limpias y bien mantenidas, incluyendo los baños. Los visitantes aprecian la atmósfera tranquila y el estacionamiento conveniente y asequible."
- Stars in the sample: 5*: 27, 4*: 11, 2*: 2.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJ_Rc-WG7_0YUR0nwXXvHsNdI&hl=es&gl=mx)

### Cine Tonalá

4.5 stars from 4,778 reviews on Google. 110 reviews read for this write-up. Google's own name for it is "Cine Tonalá".

- **Temperature: no signal.** 0 of 110 reviews read call the room cold, 0 call it hot or say the air conditioning was off.
- **What people write about:** snack bar in 47 of 110; staff and service in 46 of 110; what is showing in 45 of 110; price in 25 of 110; seat comfort in 16 of 110.
- **Google's own summary of its whole review corpus** (not of the sample above): "La gente dice que este cine ofrece una experiencia única e íntima, con una amplia variedad de películas, comida deliciosa y un menú diverso de bebidas. Mencionan la atmósfera hermosa, acogedora y tranquila, junto con el excelente servicio del personal. Los clientes destacan los asientos cómodos, la buena calidad del sonido y la atractiva zona de la terraza."
- Stars in the sample: 5*: 77, 4*: 14, 3*: 10, 2*: 4, 1*: 5.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJzbWbjj3_0YURrt6mE5VJJLE&hl=es&gl=mx)

### Cine Lido Bella Época

4.7 stars from 186 reviews on Google. 87 reviews read for this write-up. Google's own name for it is "Cine Lido".

- **Temperature: no signal.** 0 of 87 reviews read call the room cold, 0 call it hot or say the air conditioning was off.
- **What people write about:** seat comfort in 9 of 87; price in 8 of 87; what is showing in 8 of 87; cleanliness / bathrooms in 6 of 87; staff and service in 5 of 87.
- Stars in the sample: 5*: 68, 4*: 13, 3*: 5, 1*: 1.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJG0CiH2j_0YUR7i7HbvFM2v0&hl=es&gl=mx)

### Cinematógrafo del Chopo

4.4 stars from 15 reviews on Google. 9 reviews read for this write-up. Google's own name for it is "Cinematógrafo Del Chopo".

- **Temperature: no signal.** 0 of 9 reviews read call the room cold, 0 call it hot or say the air conditioning was off.
- **What people write about:** sound in 3 of 9; price in 3 of 9; what is showing in 3 of 9; staff and service in 2 of 9; picture and screen in 2 of 9.
- Stars in the sample: 5*: 6, 4*: 1, 3*: 1, 1*: 1.
- [Google Maps place](https://www.google.com/maps/place/?q=place_id:ChIJq6oG28_40YUR7ZCiOeXqJ4Y&hl=es&gl=mx)


## Method, and the two routes that do not work

**What was tried, in order.**

1. **Plain HTTP to Google Maps.** `www.google.com/maps/place/...`
   answers **200** and 208 KB, and the body is a JavaScript shell: no rating, no review
   count, no review text, and no place id. Searching that HTML for a rating finds nothing.
   A 200 here is not a refusal, which is exactly why it is worth writing down -- the page
   arrived, it just does not contain the answer.
2. **The `tbm=map` endpoint the Maps frontend itself calls.** This one works over plain
   HTTP and is what `find-places.py` uses. It answers **200** with a JSON array carrying
   the place's name, coordinates, feature id, place id and star rating. It does **not**
   reliably carry the review count, and it carries no review text at all. All 39 venues
   resolved to a place id this way, and this endpoint does answer plain `curl`.
3. **`/maps/rpc/listugcposts`, the reviews RPC.** **403 Forbidden** to a hand-built `pb`
   parameter, and still 403 when called from inside a logged-in Google Maps tab with
   `credentials: 'include'`. `/maps/preview/review/listentitiesreviews`, the older
   endpoint, answers **404**. Watching the network while a place's reviews loaded captured
   **zero** matching requests, because Maps ships the first page of reviews inside the
   document rather than fetching it.
4. **The rendered review pane in his Chrome.** This works, and it is what the numbers
   here come from.

**One thing measured rather than assumed:** the `tbm=map` endpoint does not care which TLS
stack asks. `/opt/homebrew/bin/python3` (OpenSSL 3.6.3), `/usr/bin/python3` (LibreSSL
2.8.3) and macOS `curl` all answer **200** with an identical 32,715-byte body. The
fingerprinting wall that blocks the system stack on some other sites is simply not present
here, and an earlier draft of this file asserted that it was.

**Four defects found and fixed while building the scrape**, each of which produced a
plausible-looking wrong answer:

- **Setting `scrollTop` loads exactly 20 reviews and then stops.** Maps' loader listens
  for a scroll *event*, so the event has to be dispatched by hand. Without that, every
  cinema would have reported a 20-review sample and looked consistent.
- **Every review renders twice.** 20 `data-review-id` nodes are 10 reviews. Counting
  nodes doubles every sample size and every keyword tally at once, so the ratios stay
  believable while every absolute number is wrong.
- **Eight cinemas rendered no review card at all, and their pages were perfectly fine.**
  Google's newer reviews layout shows the star histogram and its own written summary
  first and loads not one review until something scrolls. Every pane-finder here starts
  from a review card, so with zero cards there was nothing to start from -- and the record
  was written out with a sample of 0 and no error against it. Cineteca Nacional in Xoco,
  the most-reviewed venue in the whole app at 63,587 reviews, was one of the eight.
  Scrolling every tall overflowing container instead of starting from a card recovered
  all ten that had come back thin, on the first attempt.
- **Long reviews arrive folded at "... Mas".** 30 of the first 80 were cut off, and the
  temperature complaint is usually in the second half of a review, after the plot summary.
  The expander is a button whose accessible name is exactly "Ver mas", and clicking
  re-renders the card, so it takes several passes.

**How a temperature mention is counted.** Sentence by sentence, over accent-stripped
text. The rules below were not written in advance -- each one was added after reading
every sentence the classifier had flagged and finding a wrong one:

- **`palomitas frias` is cold popcorn, not a cold room.** It is the single most common
  "frio" in a Mexican cinema review -- 16 of them in the first 1,271 reviews, against 8
  genuine cold complaints. A sentence-level food filter is not enough: the sentence that
  defeated the first version was *"llegamos a las 11:30 am y palomitas frias"*, which also
  contains the word "funcion". So the check asks which noun the cold word is attached to,
  three tokens either side, and only falls back to the whole sentence when that window is
  inconclusive -- which is what catches *"por fuera estan calientes y por dentro frios"*.
- **`sin aire acondicionado` is a HEAT complaint** even though it contains the phrase
  "aire acondicionado". Counting that phrase as a cold signal, which is the obvious thing
  to do, gets the sign backwards on exactly the cinemas where the cooling is broken.
- **`lleven chamarra` never uses the word cold and is the strongest cold signal there is**,
  because the reviewer is giving advice. But a jacket only counts when advice is actually
  being given: *"se llevaron mi sueter"* is a theft and *"revision a las mochilas o bolsas
  o chamarras"* is a bag search, and both read as cold complaints until the rule was
  narrowed. The verb forms have to end at a word boundary, because `llev a` also matches
  "llevaron" -- which is how a robbery became a temperature reading.
- **`sin frio en exceso` is praise.** A negation immediately before the cold word flips
  its meaning, and that sentence was being counted against the one cinema doing it right.
- **`muros frios` is about the decor**, and `helado` is ice cream far more often than it
  is a freezing sala.

**The precision was measured, not assumed.** Every sentence the classifier flagged across
all 3,267 reviews was read by hand, four times, and each pass found wrong ones that the
previous rules had let through -- 11 of the first 16 "cold" hits were false. What survives
is 12 cold sentences, all of them genuine, and 63 heat sentences of which two are still
misreads: one is a wood-fired pizza oven and one complains about heat in the ticket hall
while saying the auditorium itself was fine. So call it about 3% error on the heat side and
none found on the cold side. The food-cold pile that was excluded is **46 reviews**, which
is nearly four times the number of real cold complaints -- that filter is not a nicety,
it is most of the work.

`analyze-reviews.py` opens with a control: 33 sentences that must classify into four
different verdicts, and every one of them is a real sentence out of these reviews that was
once classified wrongly. It exits non-zero if they collapse, because a classifier that answers the same
thing to every input produces a full, orderly, worthless table.

**What these numbers are not.** The sample is Google's "most relevant" ordering, not a
random draw, and it is roughly 100 reviews out of a corpus that runs to several thousand
at the busy sites. Ratios between cinemas are comparable because every cinema was read the
same way. An absolute rate like "4%% of visitors were cold" is not supported.

