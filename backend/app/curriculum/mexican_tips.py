"""Rotating Mexican culture tips — one per lesson day (after day 1 of each week)."""

from .program import t

# Each entry: (english, russian, spanish). Indexed by (global_day - 1) % len.
DAILY_MEXICAN_TIPS = [
    t("'¿Qué onda?' is a super casual 'What's up?' — very chilango.", "«¿Qué onda?» — неформальное «как дела?», типично для Мехико.", "'¿Qué onda?' es un saludo casual muy chilango."),
    t("'¿Mande?' is the polite Mexican way to say 'Excuse me? / Pardon?'", "«¿Mande?» — вежливое «простите? / что?» в Мексике.", "'¿Mande?' es la forma educada de decir «¿perdón?»."),
    t("'Ahorita' can mean 'right now'… or 'maybe later'. Context is everything!", "«Ahorita» может значить «прямо сейчас»… или «потом». Зависит от контекста!", "'Ahorita' puede ser «ahorita mismo»… o «más tarde». ¡Muy mexicano!"),
    t("'Padre' and 'chido' both mean 'cool/awesome' in Mexican slang.", "«Padre» и «chido» — оба значат «классно» в мекс. сленге.", "'Padre' y 'chido' significan «genial» en México."),
    t("'La neta' = 'honestly / for real' — a frank Mexican expression.", "«La neta» = «честно говоря / правда» — прямолинейное выражение.", "'La neta' = «la verdad / en serio» — muy mexicano."),
    t("'Sale' and 'órale' mean 'OK, deal!' or 'let's go!'", "«Sale» и «órale» — «ок, договорились!» или «погнали!»", "'Sale' y 'órale' = «¡va! / ¡ándale!»"),
    t("'Chamba' is Mexican slang for work; 'chambear' = to work.", "«Chamba» — работа (сленг); «chambear» — работать.", "'Chamba' = trabajo (mexicano); 'chambear' = trabajar."),
    t("In Mexico, the bus is often called 'el camión', not 'el autobús'.", "В Мексике автобус часто «el camión», а не «el autobús».", "En México el bus suele ser «el camión»."),
    t("'Mijo / mija' are warm terms: 'my son/daughter' used affectionately.", "«Mijo / mija» — ласково «сынок / доченька».", "'Mijo / mija' = cariño, como «hijito / hijita»."),
    t("'Provecho' or 'buen provecho' — say it when someone is eating.", "«Provecho» или «buen provecho» — когда кто-то ест.", "'Provecho' o 'buen provecho' al ver a alguien comer."),
    t("'¿A poco?' expresses surprise: 'Really? / No way!'", "«¿A poco?» — удивление: «неужели? / правда?»", "'¿A poco?' = sorpresa: «¿de veras? / ¡no manches!»"),
    t("'No manches' = 'No way!' (mild) — very common in central Mexico.", "«No manches» — «не может быть!» (мягко), очень часто.", "'No manches' = «¡no puede ser!» — muy común."),
    t("'Aguas!' means 'Watch out!' — originally 'waters' but now a warning.", "«¡Aguas!» — «осторожно!» (букв. «воды»).", "'¡Aguas!' = «¡cuidado!» — advertencia mexicana."),
    t("'¿Qué pedo?' (very informal) among friends = 'What's up?'", "«¿Qué pedo?» (очень неформ.) между друзьями = «как дела?»", "'¿Qué pedo?' (informal entre amigos) = «¿qué onda?»"),
    t("'Güey' (wey) = 'dude' — use only with close friends.", "«Güey» — «чувак», только с близкими друзьями.", "'Güey' = «carnal / compa», solo con amigos."),
    t("'Carnal' or 'cuate' = close buddy, like 'bro'.", "«Carnal» / «cuate» — близкий друг, как «братан».", "'Carnal' o 'cuate' = amigo muy cercano."),
    t("'Fresa' describes someone posh/preppy — Mexican youth slang.", "«Fresa» — «мажор / понт» в молодёжном сленге.", "'Fresa' = persona fresa / de clase alta."),
    t("'Naco' is the opposite of fresa — rough/unsophisticated (can be rude).", "«Naco» — противоположность «fresa» (может быть грубо).", "'Naco' = lo opuesto a fresa (cuidado, puede ofender)."),
    t("'La tiendita' = the little corner shop — heart of every neighborhood.", "«La tiendita» — лавка на углу, душа района.", "'La tiendita' = la tienda de la esquina."),
    t("'El mercado' is where locals buy fresh food — great for practicing Spanish.", "«El mercado» — рынок, отличное место практиковать язык.", "'El mercado' es ideal para practicar español."),
    t("'Una chela' = a beer (casual). 'Una michelada' = beer with lime and spices.", "«Una chela» — пиво; «michelada» — пиво с лаймом и специями.", "'Una chela' = cerveza; 'michelada' = cerveza preparada."),
    t("'Taco al pastor' is the iconic Mexico City street food.", "«Taco al pastor» — культовый стритфуд Мехико.", "'Taco al pastor' = comida callejera icónica del DF."),
    t("'Con todo' on a taco means 'with all the toppings'.", "«Con todo» на тако — «со всеми начинками».", "'Con todo' en un taco = con cebolla, cilantro y salsa."),
    t("'Sin picante, por favor' — essential if you can't handle spicy!", "«Sin picante, por favor» — если не переносите острое!", "'Sin picante, por favor' — si no aguantas el chile."),
    t("'Está cañón' = 'It's intense / tough / amazing' depending on context.", "«Está cañón» — «жёстко / круто / сложно» по контексту.", "'Está cañón' = intenso / difícil / impresionante."),
    t("'Qué padre' = 'How cool!' — one of the most Mexican compliments.", "«Qué padre» — «как классно!»", "'Qué padre' = «¡qué chido!»"),
    t("'Ándale' can mean 'come on', 'hurry up', or 'OK then'.", "«Ándale» — «давай», «поторопись» или «ну ладно».", "'Ándale' = «vamos / apúrate / bueno»."),
    t("'Híjole' expresses dismay or surprise — like 'Oh man!'", "«Híjole» — «ё-моё! / ну вот!»", "'Híjole' = «¡ay! / ¡caray!»"),
    t("'Ahorita te marco' — 'I'll call you right back' (phone Mexicanism).", "«Ahorita te marco» — «сейчас перезвоню».", "'Ahorita te marco' = te llamo en un momento."),
    t("'¿Más vale?' confirms agreement: 'Right? / You agree?'", "«¿Más vale?» — «верно? / согласен?»", "'¿Más vale?' = «¿verdad? / ¿no?»"),
    t("'El centro' = the historic downtown — every Mexican city has one.", "«El centro» — исторический центр города.", "'El centro' = el centro histórico."),
    t("'La calle' life: street vendors, music, and conversation everywhere.", "Уличная жизнь: продавцы, музыка, разговоры повсюду.", "La vida en 'la calle': vendedores, música y charla."),
    t("'Día de Muertos' (Nov 1–2) — honor loved ones with altars and marigolds.", "«Día de Muertos» (1–2 нояб.) — день памяти с алтарями.", "'Día de Muertos' — tradición de honrar a los difuntos."),
    t("'Lucha libre' — Mexican wrestling, a beloved national spectacle.", "«Lucha libre» — мексиканский реслинг, национальное зрелище.", "'Lucha libre' — espectáculo muy mexicano."),
    t("'Fútbol' unites Mexico — 'Goooooool!' is heard in every plaza.", "«Fútbol» объединяет Мексику — «Гооол!» на каждой площади.", "'Fútbol' une a México — ¡Goooool! en cada plaza."),
    t("'La banda' or 'la norteña' — regional music styles Mexicans love.", "«La banda» / «la norteña» — любимые музыкальные стили.", "'La banda' y 'la norteña' — música regional muy popular."),
    t("'Con permiso' — always say it when passing through a crowd.", "«Con permiso» — говорите, проходя сквозь толпу.", "'Con permiso' al pasar entre la gente."),
    t("'Disculpe' for strangers; 'perdón' for bumping into someone.", "«Disculpe» — незнакомцам; «perdón» — если задели.", "'Disculpe' con desconocidos; 'perdón' si tropiezas."),
    t("'¿Cuánto cuesta?' and '¿Me puede hacer precio?' at the market.", "«¿Cuánto cuesta?» и «¿Me hace precio?» на рынке.", "'¿Cuánto cuesta?' y '¿Me hace precio?' en el mercado."),
    t("'La propina' (tip) of 10–15% is appreciated at restaurants.", "«La propina» 10–15% в ресторанах приветствуется.", "'La propina' del 10–15% se agradece en restaurantes."),
    t("'El D.F.' or 'CDMX' — Mexico City, the accent you're learning.", "«El D.F.» / «CDMX» — Мехико, акцент который вы учите.", "'CDMX' — Ciudad de México, el acento que aprendes."),
    t("'Seseo': Mexicans pronounce 'c' and 'z' like 's' — 'gracias' = grasias.", "«Seseo»: «c» и «z» как «s» — «gracias» звучит «grasias».", "Seseo: la 'c' y 'z' suenan como 's' en México."),
    t("'Poquito' — 'just a little' — useful at every meal!", "«Poquito» — «совсем чуть-чуть» — полезно за столом!", "'Poquito' = «un poquito nomás» — ¡muy útil!"),
    t("'¿Le ayudo en algo?' — store clerk's friendly 'Can I help you?'", "«¿Le ayudo en algo?» — «могу помочь?» в магазине.", "'¿Le ayudo en algo?' en tiendas y mercados."),
    t("'Estoy crudo' = hungover (after too many chelas).", "«Estoy crudo» — «у меня похмелье».", "'Estoy crudo' = tener resaca."),
    t("'Echar la flojera' = to laze around — Sundays are for that.", "«Echar la flojera» — «бездельничать» — для воскресенья.", "'Echar la flojera' = descansar sin hacer nada."),
    t("'El mal del puerco' — food coma after a big comida.", "«El mal del puerco» — «синдром обжоры» после обеда.", "'El mal del puerco' = sueño después de comer mucho."),
    t("'Vámonos' = let's go! Perfect for leaving the house.", "«¡Vámonos!» — «пошли!»", "'¡Vámonos!' = ¡salimos!"),
    t("'Ahí nos vemos' = see you there — casual goodbye.", "«Ahí nos vemos» — «увидимся там».", "'Ahí nos vemos' = nos vemos allá."),
    t("'Cuídate mucho' — take good care (warm goodbye).", "«Cuídate mucho» — «береги себя» (теплое прощание).", "'Cuídate mucho' — despedida cariñosa."),
]


def mexican_tip_for_day(global_day: int) -> dict:
    """Pick a unique-feeling tip for each calendar day in the program."""
    idx = (global_day - 1) % len(DAILY_MEXICAN_TIPS)
    return DAILY_MEXICAN_TIPS[idx]
