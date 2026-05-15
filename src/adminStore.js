const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const DEFAULT_HOST_ID = "sweetiefox";
const promptKinds = ["greeting", "fact", "listener", "farewell"];

const defaultPromptConfig = {
  common: "Общие правила для всех ведущих AI Chill Radio. Пиши только готовый текст для озвучки, без markdown, списков, кавычек, эмодзи и технических комментариев. Все числа, годы, проценты, единицы измерения и сокращения произноси словами: не 30-40 секунд, а от тридцати до сорока секунд; не 3D, а три-дэ; не AI, а эй-ай, если это должно звучать именно так. Для естественной речи используй короткие фразы, живую пунктуацию и редкие паузы ElevenLabs в формате <break time=\"0.35s\" /> или <break time=\"0.55s\" />; не ставь паузы подряд и не делай их длиннее одной секунды. Для русского текста не используй SSML phoneme: он не подходит для нашей русской озвучки. Если слово может быть прочитано неверно, переформулируй его или поставь явное ударение в слове. Интонация должна быть спокойной, уверенной, теплой и радиоформатной: не лекция, не реклама и не сухая энциклопедия.",
  activeHostId: DEFAULT_HOST_ID,
  hosts: {
    [DEFAULT_HOST_ID]: {
      name: "SweetieFox",
      greeting: "Сделай уникальное приветствие для chill radio от ведущей SweetieFox. Атмосфера: спокойная музыка, интересные темы, мягкая улыбка и ощущение живого эфира. Два коротких предложения.",
      farewell: "Сделай уникальное прощание для chill radio от ведущей SweetieFox. Теплый финал эфира, спокойная улыбка, приглашение вернуться. Одно или два коротких предложения.",
      fact: "Сделай эфирный монолог на тридцать-сорок секунд по главной теме и обязательной подтеме. В первой фразе естественно объяви, к какой теме и подтеме перешел эфир, но каждый раз формулируй это по-новому. Дальше раскрой один конкретный механизм, пример, число или историю: подробно, понятно, без воды, без общих фраз и без ухода в соседние подтемы. Длина примерно семьдесят пять-девяносто пять слов. Стиль: спокойное умное chill radio, живая речь ведущей, без списков.",
      listener: "Ответь слушателю как ведущая SweetieFox: спокойно, женственно, мягко, с паузами и без спешки. Делай подробный эфирный ответ, но держи структуру живой радиоречи. Сначала коротко озвучь вопрос, затем ответь по сути.",
    },
  },
};

const defaultTopicTree = [
  ["космос", ["Марс", "Венера", "Юпитер", "Сатурн", "чёрные дыры", "экзопланеты", "кометы", "Луна", "звёзды", "космические миссии"]],
  ["океан", ["глубоководные рыбы", "кораллы", "киты", "течения", "биолюминесценция", "подводные вулканы", "солёность", "планктон", "Марианская впадина", "кораблекрушения"]],
  ["природа", ["грибы", "деревья", "пустыни", "ледники", "болота", "вулканы", "реки", "пещеры", "молнии", "сезоны"]],
  ["животные", ["вороны", "слоны", "кошки", "собаки", "пчёлы", "осьминоги", "пингвины", "летучие мыши", "дельфины", "муравьи"]],
  ["мозг", ["память", "внимание", "зрение", "запахи", "привычки", "эмоции", "музыка и мозг", "сон мозга", "иллюзии", "обучение"]],
  ["сон", ["фазы сна", "сны", "храп", "дневной сон", "бессонница", "лунатизм", "сон животных", "сновидения", "циркадные ритмы", "будильники"]],
  ["музыка", ["ритм", "бас", "джаз", "синтезаторы", "саундтреки", "тишина", "тембр", "радио", "винил", "музыкальная память"]],
  ["города", ["метро", "мосты", "небоскрёбы", "парки", "фонари", "старые улицы", "городской шум", "крыши", "площади", "подземелья"]],
  ["еда", ["кофе", "чай", "шоколад", "сыр", "хлеб", "острый вкус", "ферментация", "мороженое", "специи", "супы"]],
  ["история", ["древние письма", "карты", "монеты", "быт", "мореплаватели", "изобретатели", "старые профессии", "праздники", "дороги", "календарь"]],
  ["технологии", ["роботы", "спутники", "батареи", "интернет", "камера", "микросхемы", "нейросети", "сенсоры", "лазеры", "3D-печать"]],
  ["психология", ["мотивация", "выбор", "страх", "юмор", "общение", "внимательность", "ошибки мышления", "прокрастинация", "любопытство", "доверие"]],
  ["погода", ["облака", "туман", "радуга", "снег", "ветер", "штормы", "град", "давление", "жара", "северное сияние"]],
  ["путешествия", ["поезда", "аэропорты", "маяки", "острова", "горы", "пустынные дороги", "отели", "рынки", "порты", "навигация"]],
  ["кино", ["монтаж", "звук в кино", "каскадёры", "миниатюры", "реквизит", "немое кино", "анимация", "цвет", "дубляж", "титры"]],
  ["искусство", ["краски", "музеи", "скульптура", "фрески", "фотография", "граффити", "реставрация", "портреты", "абстракция", "рамки"]],
  ["спорт", ["дыхание", "баланс", "реакция", "марафон", "плавание", "шахматы", "велосипед", "йога", "футбол", "олимпиады"]],
  ["микромир", ["бактерии", "вирусы", "клетки", "ДНК", "микроскопы", "пыльца", "плесень", "дрожжи", "иммунитет", "биоплёнки"]],
  ["энергия", ["свет", "тепло", "электричество", "ветер", "солнечные панели", "молнии", "магниты", "волны", "топливо", "энергосбережение"]],
  ["изобретения", ["зонтик", "лифт", "пуговицы", "бумага", "часы", "карандаш", "велосипед", "холодильник", "радио", "молния-застёжка"]],
];

const curatedTopicTree = [
  ["Космос", ["почему орбита — это постоянное падение", "как рождаются звезды в газовых облаках", "что показывает спектр света далекой звезды", "почему Марс потерял большую часть атмосферы", "как работают гравитационные маневры аппаратов", "что происходит у горизонта событий черной дыры", "как ищут экзопланеты по мерцанию звезд", "почему лед на Луне важен для будущих баз", "как космическая пыль становится планетами", "что измеряют телескопы за пределами видимого света", "почему время рядом с массивными объектами идет иначе", "как радиосигнал проходит миллионы километров"]],
  ["Океан", ["почему глубина меняет давление и жизнь", "как течения переносят тепло по планете", "что слышно под водой на больших расстояниях", "почему вода светится в темноте", "как формируются подводные горы и впадины", "что происходит у гидротермальных источников", "как соль влияет на плотность воды", "почему планктон держит пищевые цепочки", "как океан поглощает углекислый газ", "почему штормовые волны опаснее обычных", "как исследуют дно без света", "что рассказывают керны морских осадков"]],
  ["Мозг и внимание", ["почему память пересобирается при каждом вспоминании", "как внимание выбирает один сигнал среди шума", "почему мозг достраивает слепые зоны зрения", "как запахи быстро вызывают воспоминания", "почему привычка экономит энергию мышления", "как сон помогает сортировать опыт", "почему музыка меняет ощущение времени", "как мозг распознает лица", "почему иллюзии полезны для науки", "как стресс сужает фокус внимания", "почему обучение требует ошибок", "как тишина влияет на восприятие"]],
  ["Сон", ["зачем нужны разные фазы сна", "почему сны кажутся связными историями", "как свет вечером сбивает биологические часы", "почему короткий дневной сон может помогать", "что происходит с памятью ночью", "как кофеин задерживает усталость", "почему мозг иногда просыпается раньше тела", "как температура комнаты влияет на сон", "почему повторяющиеся сны запоминаются", "как шум меняет глубину сна", "почему утренний свет важен для режима", "как недосып влияет на решения"]],
  ["Технологии будущего", ["как роботы учатся двигаться в реальном мире", "почему батареи ограничивают мобильную технику", "как спутники видят Землю почти в реальном времени", "зачем датчикам нужна калибровка", "как нейросети распознают закономерности", "почему лазеры точны в измерениях", "как 3D-печать меняет прототипы", "зачем микросхемам нужны чистые комнаты", "как камеры считают глубину кадра", "почему автономным системам важны редкие ошибки", "как цифровые двойники помогают проектировать", "почему защита данных стала частью инженерии"]],
  ["Города", ["как метро задает ритм районам", "почему мосты проектируют с запасом движения", "как парки охлаждают город летом", "зачем улицам нужна хорошая навигация", "почему высотки раскачиваются на ветру", "как фонари меняют безопасность пространства", "что слышно в городском шуме", "как крыши становятся рабочей инфраструктурой", "почему старые кварталы часто удобны пешком", "как ливневки спасают улицы после дождя", "зачем городам нужны тихие зоны", "как транспортные узлы меняют привычки жителей"]],
  ["Еда и вкус", ["почему аромат важнее языка для вкуса", "как ферментация меняет продукт", "почему кофе раскрывается при разной обжарке", "как соль усиливает сладость", "почему хруст влияет на удовольствие", "как температура меняет вкус", "зачем сыру нужно созревание", "как специи работают с маслами", "почему хлеб пахнет по-разному после выпечки", "как горечь может стать приятной", "почему текстура важна не меньше вкуса", "как упаковка влияет на восприятие еды"]],
  ["История повседневности", ["как древние письма сохраняли бытовые детали", "почему карты раньше были инструментом власти", "как монеты рассказывают о торговле", "зачем календарям нужны реформы", "как дороги меняли скорость жизни", "почему профессии исчезают незаметно", "как бытовые предметы переживают эпохи", "что одежда говорит о технологиях", "как освещение изменило вечернее время", "почему рынки были центрами новостей", "как почта ускорила личные связи", "что старые рецепты говорят об экономике"]],
  ["Музыка", ["почему ритм цепляет тело раньше смысла", "как бас заполняет пространство", "зачем тишина нужна в композиции", "почему тембр отличает два одинаковых тона", "как саундтреки управляют ожиданием", "что делает синтезатор с волной", "почему джаз строится на слушании", "как радио меняло музыкальные вкусы", "зачем винилу характерный шум", "как память привязывает песни к моментам", "почему громкость не равна энергии", "как повтор делает мотив узнаваемым"]],
  ["Кино", ["как монтаж управляет вниманием", "почему звук создает пространство кадра", "как цвет меняет настроение сцены", "зачем реквизит рассказывает без слов", "почему немое кино было не совсем немым", "как миниатюры создавали большие миры", "что делает хороший дубляж незаметным", "как титры задают тон истории", "почему пауза сильнее объяснения", "как крупный план меняет эмпатию", "зачем каскадерам нужна точная математика", "как свет рисует характер персонажа"]],
  ["Искусство", ["почему краска стареет по-разному", "как музейный свет защищает экспонаты", "зачем скульптуре важна тень", "как фреска связана со стеной", "почему фотография изменила портрет", "как реставратор отличает слой от ошибки", "зачем абстракция убирает лишние детали", "почему рама влияет на восприятие", "как граффити работает с местом", "что видно в мазке художника", "почему масштаб меняет эмоцию", "как материал ограничивает идею"]],
  ["Погода и климат", ["как облака держатся в воздухе", "почему туман появляется у земли", "как давление связано с ветром", "почему радуга имеет порядок цветов", "как снег растет из кристаллов", "что делает грозу электрической", "почему жара опасна при влажности", "как океан влияет на сезоны", "зачем метеостанциям длинные ряды данных", "почему климат — это не погода дня", "как город усиливает тепло", "что показывает северное сияние"]],
  ["Путешествия", ["как вокзалы стали городскими воротами", "почему аэропорты похожи на отдельные города", "зачем маякам нужен особый ритм света", "как порты ускоряли обмен идеями", "почему рынки лучше путеводителя", "как горные дороги читают рельеф", "зачем навигации нужны резервные системы", "почему острова формируют отдельные привычки", "как гостиницы меняли приватность", "что дорога делает с ощущением времени", "почему карты не заменяют местный взгляд", "как багаж менял стиль путешествий"]],
  ["Микромир", ["как бактерии общаются химическими сигналами", "почему клетка похожа на город процессов", "как ДНК хранит инструкции", "зачем микроскопу нужен контраст", "почему плесень быстро осваивает поверхность", "как дрожжи превращают сахар", "что делает иммунитет до появления симптомов", "как пыльца путешествует в воздухе", "почему биопленки трудно убрать", "как вирусу нужна чужая клетка", "зачем лабораториям стерильность", "почему микромир меняет вкус еды"]],
  ["Энергия", ["почему свет несет энергию", "как тепло переходит между телами", "зачем электросети балансируют нагрузку", "почему ветер — это движение тепла", "как солнечная панель превращает свет в ток", "что происходит в аккумуляторе при зарядке", "почему магниты связаны с электричеством", "как волны переносят энергию без переноса воды", "зачем домам теплоизоляция", "почему топливо хранит химическую энергию", "как рекуперация возвращает часть потерь", "почему экономия энергии начинается с измерений"]],
  ["Изобретения", ["как лифт изменил высоту городов", "почему бумага стала технологией памяти", "как часы синхронизировали общество", "зачем карандашу графит, а не свинец", "почему велосипед оказался сложной инженерией", "как холодильник изменил питание", "что радио сделало с расстоянием", "почему молния-застежка долго приживалась", "как пуговица стала массовой деталью", "зачем зонту нужна гибкая конструкция", "как печатный станок ускорил идеи", "почему простые вещи часто изобретают долго"]],
  ["Язык и коммуникация", ["почему интонация меняет смысл", "как жесты помогают понять речь", "зачем словам нужны контексты", "почему новые слова быстро распространяются", "как письменность отделила мысль от момента", "почему перевод — это выбор, а не замена", "как пауза работает в разговоре", "зачем языку метафоры", "почему акцент хранит историю места", "как шрифт влияет на доверие", "что делает сообщение понятным", "почему молчание тоже передает смысл"]],
  ["Время", ["почему минута кажется разной", "как маятник помог точным часам", "зачем миру нужны часовые пояса", "почему календарь не идеально совпадает с небом", "как возраст меняет ощущение скорости дней", "зачем науке атомные часы", "почему ожидание растягивает время", "как музыка задает внутренний темп", "что такое задержка сигнала", "почему дедлайны меняют внимание", "как архивы сохраняют время", "зачем ритуалам повторение"]],
  ["Материалы", ["почему стекло бывает прочным и хрупким", "как бетон набирает прочность", "зачем стали добавляют углерод", "почему дерево работает вдоль волокон", "как керамика выдерживает жар", "что делает пластик гибким", "почему ткань дышит", "как композиты соединяют свойства", "зачем покрытия защищают металл", "почему резина возвращает форму", "как бумага держит чернила", "что показывает усталость материала"]],
  ["Человек и тело", ["как сердце подстраивается под нагрузку", "почему дыхание влияет на спокойствие", "как кожа чувствует температуру", "зачем мышцам нужна разминка", "почему баланс зависит от внутреннего уха", "как зрение адаптируется к темноте", "зачем телу нужна вода", "почему голос зависит от дыхания", "как осанка меняет работу мышц", "что происходит при усталости", "почему восстановление важнее рывка", "как привычки закрепляются через повторение"]],
];

const defaultAdminConfig = {
  stationName: "AI Chill Radio",
  topics: curatedTopicTree.map(([name, subtopics]) => ({ id: createTopicId(name), name, subtopics })),
  prompts: defaultPromptConfig,
  voice: {
    model: "eleven_multilingual_v2",
    stability: 0.5,
    similarityBoost: 0.75,
    style: 0,
    speed: 1,
    speakerBoost: true,
  },
  audioMix: {
    musicLevel: 0.72,
    voiceLevel: 1,
    duckingRatio: 0.18,
    preludeSeconds: 0,
    duckFadeSeconds: 1.6,
    restoreFadeSeconds: 1.4,
    postludeSeconds: 3,
  },
  factPolicy: {
    archiveAfterTotal: 200,
    useArchiveWhenReady: false,
  },
  topicCycle: {
    minIntervalMinutes: 5,
    maxIntervalMinutes: 6,
    order: "topic-first",
  },
};

async function readAdminConfig(config) {
  await ensureAdminConfig(config);
  const raw = await fs.promises.readFile(config.adminConfigPath, "utf8");
  return mergeAdminConfig(JSON.parse(raw));
}

async function writeAdminConfig(config, input) {
  const merged = mergeAdminConfig(input);
  await fs.promises.mkdir(path.dirname(config.adminConfigPath), { recursive: true });
  await fs.promises.writeFile(config.adminConfigPath, JSON.stringify(merged, null, 2), "utf8");
  return merged;
}

async function ensureAdminConfig(config) {
  await fs.promises.mkdir(path.dirname(config.adminConfigPath), { recursive: true });
  if (!fs.existsSync(config.adminConfigPath)) {
    await fs.promises.writeFile(config.adminConfigPath, JSON.stringify(defaultAdminConfig, null, 2), "utf8");
  }
}

function mergeAdminConfig(input = {}) {
  const minTopicInterval = clampNumber(input.topicCycle?.minIntervalMinutes, defaultAdminConfig.topicCycle.minIntervalMinutes, 1, 240);
  const maxTopicInterval = clampNumber(input.topicCycle?.maxIntervalMinutes, defaultAdminConfig.topicCycle.maxIntervalMinutes, 1, 240);
  return {
    stationName: String(input.stationName || defaultAdminConfig.stationName).slice(0, 80),
    topics: normalizeTopicTree(input.topics),
    prompts: normalizePromptConfig(input.prompts),
    voice: {
      model: normalizeVoiceModel(input.voice?.model, defaultAdminConfig.voice.model),
      stability: clampNumber(input.voice?.stability, defaultAdminConfig.voice.stability, 0, 1),
      similarityBoost: clampNumber(input.voice?.similarityBoost, defaultAdminConfig.voice.similarityBoost, 0, 1),
      style: clampNumber(input.voice?.style, defaultAdminConfig.voice.style, 0, 1),
      speed: clampNumber(input.voice?.speed, defaultAdminConfig.voice.speed, 0.7, 1.2),
      speakerBoost: Boolean(input.voice?.speakerBoost ?? defaultAdminConfig.voice.speakerBoost),
    },
    audioMix: {
      musicLevel: clampNumber(input.audioMix?.musicLevel, defaultAdminConfig.audioMix.musicLevel, 0, 2),
      voiceLevel: clampNumber(input.audioMix?.voiceLevel, defaultAdminConfig.audioMix.voiceLevel, 0, 2),
      duckingRatio: clampNumber(input.audioMix?.duckingRatio, defaultAdminConfig.audioMix.duckingRatio, 0, 1),
      preludeSeconds: clampNumber(input.audioMix?.preludeSeconds, defaultAdminConfig.audioMix.preludeSeconds, 0, 30),
      duckFadeSeconds: clampNumber(input.audioMix?.duckFadeSeconds, defaultAdminConfig.audioMix.duckFadeSeconds, 0.2, 10),
      restoreFadeSeconds: clampNumber(input.audioMix?.restoreFadeSeconds, defaultAdminConfig.audioMix.restoreFadeSeconds, 0.2, 10),
      postludeSeconds: clampNumber(input.audioMix?.postludeSeconds, defaultAdminConfig.audioMix.postludeSeconds, 0, 30),
    },
    factPolicy: {
      archiveAfterTotal: Math.round(clampNumber(input.factPolicy?.archiveAfterTotal, defaultAdminConfig.factPolicy.archiveAfterTotal, 10, 2000)),
      useArchiveWhenReady: Boolean(input.factPolicy?.useArchiveWhenReady ?? defaultAdminConfig.factPolicy.useArchiveWhenReady),
    },
    topicCycle: {
      minIntervalMinutes: minTopicInterval,
      maxIntervalMinutes: Math.max(minTopicInterval, maxTopicInterval),
      order: normalizeTopicCycleOrder(input.topicCycle?.order),
    },
  };
}

function normalizeTopicCycleOrder(value) {
  return value === "subtopic-first" ? "subtopic-first" : "topic-first";
}

function normalizeTopicTree(value) {
  const source = Array.isArray(value) ? value : defaultAdminConfig.topics;
  const usedIds = new Set();
  const topics = source.map((item) => {
    if (typeof item === "string") {
      const name = String(item).trim();
      return {
        id: ensureUniqueTopicId(createTopicId(name), usedIds),
        name,
        subtopics: defaultSubtopicsFor(item),
      };
    }

    const name = String(item?.name || "").trim();
    return {
      id: ensureUniqueTopicId(normalizeTopicId(item?.id) || createTopicId(name), usedIds),
      name,
      subtopics: normalizeSubtopics(item?.subtopics),
    };
  }).filter((item) => item.name && item.subtopics.length);

  return topics.length ? topics.slice(0, 80) : defaultAdminConfig.topics;
}

function normalizeSubtopics(value) {
  const source = Array.isArray(value) ? value : [];
  const subtopics = source.map((item) => String(item).trim()).filter(Boolean);
  return [...new Set(subtopics)].slice(0, 40);
}

function defaultSubtopicsFor(topic) {
  const normalized = String(topic || "").toLowerCase();
  const found = curatedTopicTree.find(([name]) => String(name).toLowerCase() === normalized);
  return found ? found[1] : ["деталь", "история", "число", "механизм", "открытие", "рекорд", "миф", "контраст", "наблюдение", "будущее"];
}

function createTopicId(value) {
  const hash = crypto.createHash("sha1").update(String(value || "")).digest("hex").slice(0, 12);
  return `topic-${hash}`;
}

function normalizeTopicId(value) {
  const normalized = String(value || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
  return normalized || null;
}

function ensureUniqueTopicId(baseId, usedIds) {
  const base = normalizeTopicId(baseId) || createTopicId("topic");
  let candidate = base;
  let suffix = 2;
  while (usedIds.has(candidate)) {
    candidate = `${base}-${suffix}`;
    suffix += 1;
  }
  usedIds.add(candidate);
  return candidate;
}

function normalizePrompt(value, fallback) {
  const prompt = String(value || fallback).trim();
  return prompt.slice(0, 5000);
}

function normalizePromptConfig(value = {}) {
  const input = value && typeof value === "object" ? value : {};
  const defaultHost = defaultPromptConfig.hosts[DEFAULT_HOST_ID];
  const sourceHosts = input.hosts && typeof input.hosts === "object" ? input.hosts : {};
  const legacyHost = {
    name: input.hostName || defaultHost.name,
    greeting: input.greeting,
    fact: input.fact,
    listener: input.listener,
    farewell: input.farewell,
  };
  const hostIds = new Set([DEFAULT_HOST_ID, ...Object.keys(sourceHosts)]);
  const hosts = {};

  for (const rawId of hostIds) {
    const hostId = normalizeHostId(rawId) || DEFAULT_HOST_ID;
    const source = sourceHosts[rawId] || (hostId === DEFAULT_HOST_ID ? legacyHost : {});
    const fallback = hostId === DEFAULT_HOST_ID ? defaultHost : legacyHost;
    hosts[hostId] = {
      name: String(source?.name || fallback.name || hostId).trim().slice(0, 80),
      greeting: normalizePrompt(source?.greeting, fallback.greeting || defaultHost.greeting),
      fact: normalizePrompt(source?.fact, fallback.fact || defaultHost.fact),
      listener: normalizePrompt(source?.listener, fallback.listener || defaultHost.listener),
      farewell: normalizePrompt(source?.farewell, fallback.farewell || defaultHost.farewell),
    };
  }

  const requestedHostId = normalizeHostId(input.activeHostId) || DEFAULT_HOST_ID;
  const activeHostId = hosts[requestedHostId] ? requestedHostId : DEFAULT_HOST_ID;
  return {
    common: normalizePrompt(input.common, defaultPromptConfig.common),
    activeHostId,
    hosts,
  };
}

function getActivePromptSet(admin = {}) {
  const prompts = normalizePromptConfig(admin.prompts);
  const hostId = prompts.activeHostId;
  const host = prompts.hosts[hostId] || prompts.hosts[DEFAULT_HOST_ID];
  return {
    common: prompts.common,
    hostId,
    hostName: host.name || hostId,
    ...Object.fromEntries(promptKinds.map((key) => [key, host[key]])),
  };
}

function normalizeHostId(value) {
  return String(value || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

function normalizeVoiceModel(value, fallback) {
  const model = String(value || fallback || "").trim();
  return [
    "eleven_multilingual_v2",
    "eleven_flash_v2_5",
  ].includes(model) ? model : fallback;
}

function clampNumber(value, fallback, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(Math.max(number, min), max);
}

module.exports = { DEFAULT_HOST_ID, defaultAdminConfig, getActivePromptSet, readAdminConfig, writeAdminConfig };
