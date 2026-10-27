// Lời Đồng Âm engine: rewrites English lyrics so every word is spelled differently but sung the same.
// Runs in the browser (loaded by index.html, defines the global Respell) and in Node (module.exports) for the tests.
const Respell = (() => {
  // Sound-alike spellings, best first. Every entry is meant to be sung exactly like the word.
  const RESPELL_SRC = `
you:yoo,yu;your:yor;you're:yur;yours:yorz;you'll:yool;you've:yoov;me:mee;he:hee;she:shee;they:thay;
of:uv;is:iz;was:wuz;his:hiz;has:haz;as:az;are:ar;were:wur;her:hur;what:wut,whut;when:wen;where:whair;
who:hoo;whose:hooz;there:thair;their:thair;they're:thair;would:wud;one:wun;once:wunce;some:sum;come:kum;
comes:kumz;coming:kumming;become:bekum;love:luv;loves:luvz;loved:luvd;lover:luvver;lovers:luvverz;
lovely:luvly;loving:luvving;above:abuv;because:becuz,bekuz;enough:enuff;tough:tuff;rough:ruff;though:tho;
through:thru;thought:thawt;brought:brawt;taught:tawt;caught:kawt;night:nite;nights:nites;tonight:tonite;
light:lite;lights:lites;bright:brite;right:rite;sight:site;might:mite;fight:fite;delight:delite;heart:hart;
hearts:harts;knew:nu;knows:noze;new:nu;our:owr;hour:owr;here:heer;hear:heer;dear:deer;near:neer;year:yeer;
years:yeerz;tears:teerz;fear:feer;clear:kleer;please:pleez;sleep:sleap;dream:dreem;dreams:dreemz;
believe:beleeve;peace:peese;holy:holee;rain:rane;days:dayz;praise:prayz;grace:grayce;amazing:amayzing;
place:playce;face:fayce;name:naym;same:saym;came:kaym;gave:gayv;save:sayv;saved:sayvd;said:sed;says:sez;
again:agen;friend:frend;friends:frendz;heaven:hevven;heavenly:hevvenly;heavens:hevvenz;ready:reddy;
head:hed;dead:ded;death:deth;breath:breth;every:evry;everything:evrything;everyone:evrywun;
everybody:evrybody;many:menny;any:enny;money:munny;honey:hunny;country:kuntry;young:yung;touch:tutch;
trouble:trubble;double:dubble;does:duz;done:dun;don't:dont;can't:cant;won't:wont;it's:its;that's:thats;
what's:wuts;let's:lets;there's:thairz;world:wurld;worlds:wurldz;word:wurd;words:wurdz;work:wurk;girl:gurl;
earth:urth;learn:lern;first:furst;bird:burd;birds:burdz;mother:muther;brother:bruther;other:uther;
another:anuther;nothing:nuthing;something:sumthing;wonder:wunder;wonderful:wunderful;mountain:mountin;
mountains:mountinz;fountain:fountin;shepherd:shepperd;shepherds:shepperdz;christmas:krissmas,chrismas;
jesus:jeezus;glory:glorey;angel:aynjel;angels:aynjelz;savior:sayvior;saviour:sayvior;receive:reseeve;
merry:merrie;happy:happie;calm:kahm;call:kawl;fall:fawl;small:smawl;tall:tawl;walk:wawk;talk:tawk;
child:chyld;mild:myld;wild:wyld;tender:tendur;virgin:vurgin;round:rownd;around:arownd;ground:grownd;
sound:sownd;found:fownd;out:owt;about:abowt;loud:lowd;proud:prowd;cloud:klowd;clouds:klowdz;mouth:mowth;
south:sowth;blue:bloo;true:troo,tru;do:doo;move:moov;prove:proov;lose:looz;choose:chooz;truth:trooth;
beautiful:byootiful;beauty:byooty;music:myoozik;eyes:eyez;high:hy;sky:skye;cry:kry;time:tyme;
times:tymes;life:lyfe;alive:alyve;fire:fyre;shine:shyne;line:lyne;mind:mynd;find:fynd;kind:kynd;
behind:behynd;side:syde;ride:ryde;wide:wyde;hide:hyde;smile:smyle;while:whyle;rise:ryze;wise:wyze;
white:whyte;like:lyke;goodbye:goodby;cold:kold;alone:aloan;boat:bote;coat:kote;only:onlee;baby:baybee;
lady:laydee;crazy:crayzee;easy:eezy;pretty:pritty;river:rivver;ever:evver;never:nevver;forever:forevver;
whatever:wutevver;cover:kuvver;lonely:lonelee;sorry:sorrie;story:storee;worry:wurry;hurry:hurree;
carry:karry;mary:mairy;city:sitty;pity:pitty;susanna:suzanna;knee:nee;knees:neez;clementine:klementine;
sunshine:sunshyne;before:befor;more:moar;shore:shoar;sure:shur;pure:pyoor;wrong:rong;bless:bles;
faith:fayth;saint:saynt;joyful:joyfull;triumphant:triumfant;ye:yee;herald:herrald;newborn:nuborn;
mercy:mersy;sinners:sinnerz;star:starr;stars:starz;arms:armz;will:wil;can:kan;from:frum;have:hav;
give:giv;this:thiss;feel:feal;bells:belz;jingle:jingel;blind:blynd;lost:lawst;precious:preshus;appear:appeer;
making:mayking;laugh:laff;laughing:laffing;laughter:laffter;sleigh:slay;boy:boi;oh:o;o:oh;be:bee;we:wee;
believed:beleeved;relieved:releeved;weary:weery;spirit:spirrit;spirits:spirrits;open:opun;baby's:baybee's;
so:soh;go:goh;no:noh;to:tu;sleighing:slaying;silent:sylent;roses:rozes`;

  // Real words that sound the same. Clearer for the singer, but they change what the line says.
  const HOMO_SRC = `
i:eye,aye;you:yew,ewe;your:yore;you'll:yule;he'll:heel;we'd:weed;i'll:aisle,isle;we:wee;be:bee;see:sea;
sea:see;seen:scene;so:sew;no:know;know:no;to:too;too:two;two:too;one:won;won:one;for:four,fore;four:for;
hour:our;our:hour;by:buy,bye;dear:deer;deer:dear;here:hear;hear:here;right:write,rite;write:right,rite;
night:knight;knight:night;peace:piece;sun:son;son:sun;some:sum;whole:hole;hole:whole;holy:wholly;
soul:sole;rain:reign;reign:rain;pain:pane;made:maid;way:weigh;ways:weighs;wait:weight;great:grate;
days:daze;praise:prays;pray:prey;heard:herd;born:borne;morning:mourning;morn:mourn;mourn:morn;war:wore;
flower:flour;flowers:flours;road:rode,rowed;rose:rows;blue:blew;knew:new;new:knew;time:thyme;
side:sighed;die:dye;lie:lye;tide:tied;while:wile;high:hi;eye:aye;sweet:suite;meet:meat;feet:feat;
need:knead;not:knot;in:inn;all:awl;ball:bawl;him:hymn;done:dun;none:nun;tears:tiers;poor:pore,pour;
raise:rays,raze;sleigh:slay;bear:bare;bare:bear;fair:fare;pair:pear;air:heir;there:their;their:there;
where:wear;wear:where;weather:whether;which:witch;plain:plane;dew:due;through:threw;threw:through;
grown:groan;thrown:throne;throne:thrown;low:lo;slow:sloe;sail:sale;tale:tail;vain:vein;waste:waist;
past:passed;passed:past;missed:mist;guest:guessed;heal:heel;real:reel;steal:steel;week:weak;weak:week;
sent:cent,scent;knows:nose;ring:wring;higher:hire;flew:flu;altar:alter;isle:aisle;aisle:isle;
rough:ruff;turn:tern;horse:hoarse`;

  const parse = src => {
    const map = new Map();
    for (const entry of src.replace(/\s+/g, '').split(';')) {
      if (!entry) continue;
      const [word, alts] = entry.split(':');
      map.set(word, alts.split(','));
    }
    return map;
  };
  const RESPELL = parse(RESPELL_SRC);
  const HOMO = parse(HOMO_SRC);

  const NO_RULES = new Set(('shepherd uphill haphazard loophole upholstery deny rely reply apply supply imply comply ' +
    'july ally multiply occupy over clover rover hover dover wound drought plaid said again certain captain ' +
    'bargain the and quiet come some done gone none one give live have shall friend friends put son won ton ' +
    'wind comes becomes ones whom wan naked stephen of colonel entry').split(' '));

  const C = '[bcdfghjklmnpqrstvxz]';
  const longWord = w => w.length >= 4;
  // One sung syllable, counting a silent final e as none (write, home).
  const oneSyllable = w => (w.replace(/e$/, '').match(/[aeiouy]+/g) || []).length <= 1;
  // Spelling rules that keep the sound, applied in order to words the lists above do not cover.
  const RULES = [
    [/^kn(?!ow)/, 'n'],
    [/^wr/, 'r', oneSyllable],
    [/(^|[^up])ph/g, '$1f'],
    [/([^ae])ight(s|ly)?$/, '$1ite$2'],
    [/ought(s)?$/, 'awt$1'],
    [/aught(s)?$/, 'awt$1'],
    [/ation(s)?$/, 'ayshun$1'],
    [/ition(s)?$/, 'ishun$1'],
    [/ution(s)?$/, 'ooshun$1'],
    [/ction(s)?$/, 'kshun$1'],
    [/([np])tion(s)?$/, '$1shun$2'],
    [/ound(s)?$/, 'ownd$1'],
    [/out(s)?$/, 'owt$1'],
    [/ieve(d|s)?$/, 'eeve$1'],
    [/ained$/, 'aynd'],
    [/^([^aeiouy]*)all(s|ing|ed)?$/, '$1awl$2'],
    [/^([^aeiouy]*)ie(ld|lds|f|fs|st|sts)$/, '$1ee$2'],
    [/^([^aeiouy]*)o([mnltdkz])e(s)?$/, '$1oa$2$3'],
    [/^([^aeiouy]*)i([bdfklmnptvz])e(s|d)?$/, '$1y$2e$3', w => !/^(giv|liv)/.test(w)],
    [/^([^aeiouy]*)a([bdklmnptvz])e(s|d)?$/, '$1ay$2$3', w => !/[td]ed$/.test(w)],
    [/^([^aeiouy]*[rljtdn])u([dlmnt])e(s)?$/, '$1oo$2$3'],
    [/^c(?=[alr]|o(?![uv]))/, 'k'],
    [/ck(s)?$/, 'k$1'],
    [/xt$/, 'kst'],
    [/x$/, 'ks'],
    [/^([^aeiouy]+)ue$/, '$1oo'],
    [/^([^aeiouy]*)ai([^aeiouy]+)$/, '$1ay$2'],
    [new RegExp(`(${C}[bdfhjklmnpqrstvxz])er(s)?$`), '$1ur$2'],
    [new RegExp(`(${C}${C})y$`), '$1ee', w => w.length >= 5 && !/(ply|fly|by|fy)$/.test(w)],
    [/ly$/, 'lee', w => w.length >= 5 && !/(ply|fly)$/.test(w)],
    [/([bdglmnr])s$/, '$1z', longWord],
    [/(ay|ey|oy|ow|ew)s$/, '$1z', longWord],
  ];
  // Last resort for short words: a doubled final consonant keeps the vowel short (sun -> sunn, hot -> hott).
  const DOUBLE = /^([^aeiouy]*[aeiou])([bdfglmnpt])$/;

  function ruleSpelling(word) {
    if (word.length < 2 || NO_RULES.has(word) || !/^[a-z]+$/.test(word)) return null;
    let out = word;
    for (const [re, rep, when] of RULES) {
      if (!when || when(out)) out = out.replace(re, rep);
    }
    if (out === word && word.length <= 4) out = word.replace(DOUBLE, '$1$2$2');
    return out === word ? null : out;
  }

  // Candidates for one lower-case word: [{text, kind}] where kind is custom | homo | respell | rule.
  function candidates(word, opts) {
    const key = word.replace(/’/g, "'");
    const list = [];
    const add = (text, kind) => {
      if (text && text !== key && !list.some(c => c.text === text)) list.push({ text, kind });
    };
    const custom = opts.custom && opts.custom.get(key);
    if (custom && custom.toLowerCase() === key) return list; // the user wants this word kept
    if (custom) add(custom, 'custom');
    if (opts.homophones) (HOMO.get(key) || []).forEach(t => add(t, 'homo'));
    (RESPELL.get(key) || []).forEach(t => add(t, 'respell'));
    if (!RESPELL.has(key)) add(ruleSpelling(key), 'rule');
    // summer's -> summur's: respell the part before a short ending.
    const m = !list.length && key.match(/^([a-z]+)('s|'ll|'d|'ve|'re)$/);
    if (m) candidates(m[1], { homophones: false }).forEach(c => add(c.text + m[2], c.kind));
    return list;
  }

  function applyCase(orig, repl) {
    if (orig.length > 1 && orig === orig.toUpperCase() && /[A-Z]/.test(orig)) return repl.toUpperCase();
    if (/^[A-Z]/.test(orig)) return repl.charAt(0).toUpperCase() + repl.slice(1);
    return repl;
  }

  const WORD = /[A-Za-z]+(?:['’][A-Za-z]+)*/g;
  const isTagLine = line => /^\s*\[[^\]]*\]\s*$/.test(line);

  // Lyrics text -> lines of parts. A word part keeps its candidates and the chosen one (pick: -1 = unchanged).
  function analyse(text, opts) {
    return text.replace(/\r\n?/g, '\n').split('\n').map(line => {
      if (isTagLine(line)) return { tag: true, parts: [{ s: line }] };
      const parts = [];
      let last = 0;
      for (const m of line.matchAll(WORD)) {
        if (m.index > last) parts.push({ s: line.slice(last, m.index) });
        const lower = m[0].toLowerCase();
        parts.push({ w: m[0], alts: candidates(lower, opts), pick: -1 });
        last = m.index + m[0].length;
      }
      if (last < line.length) parts.push({ s: line.slice(last) });
      return { tag: false, parts };
    });
  }

  const LEVELS = { light: 4, medium: 2, strong: 0 };
  const KIND_SCORE = { custom: 40, homo: 30, respell: 30, rule: 20 };

  function rng(seed) {
    let s = (seed * 2654435761) >>> 0 || 1;
    return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  }

  // Choose which words to change so that no run of untouched words is longer than the level allows.
  function plan(lines, level, seed) {
    const rand = rng(seed + 1);
    const words = lines.flatMap(l => l.parts.filter(p => p.w));
    words.forEach(p => {
      p.pick = -1;
      if (p.alts.length > 1 && seed > 0) p.order = Math.floor(rand() * Math.min(p.alts.length, 2));
      else p.order = 0;
    });
    const choose = p => { p.pick = p.order || 0; };
    const maxRun = LEVELS[level] ?? 2;
    words.forEach(p => { if (p.alts[0] && p.alts[0].kind === 'custom') p.pick = 0; });
    if (maxRun === 0) {
      words.forEach(p => { if (p.alts.length && p.pick < 0) choose(p); });
      return;
    }
    let lastChanged = -1;
    for (let i = 0; i < words.length; i++) {
      if (words[i].pick >= 0) { lastChanged = i; continue; }
      if (i - lastChanged <= maxRun) continue;
      let best = -1, bestScore = -Infinity;
      for (let j = lastChanged + 1; j <= i; j++) {
        const p = words[j];
        if (!p.alts.length) continue;
        const score = KIND_SCORE[p.alts[0].kind] + Math.min(p.w.length, 8) + (j - lastChanged) * 3 + rand() * 6;
        if (score > bestScore) { bestScore = score; best = j; }
      }
      if (best >= 0) { choose(words[best]); lastChanged = best; }
    }
  }

  const shown = p => (p.pick >= 0 ? applyCase(p.w, p.alts[p.pick].text) : p.w);

  function toText(lines) {
    return lines.map(l => l.parts.map(p => (p.w ? shown(p) : p.s)).join('')).join('\n');
  }

  function stats(lines) {
    let total = 0, changed = 0, run = 0, longest = 0, runWords = [], longestWords = [];
    for (const l of lines) {
      if (l.tag) continue;
      for (const p of l.parts) {
        if (!p.w) continue;
        total++;
        if (p.pick >= 0) { changed++; run = 0; runWords = []; continue; }
        run++;
        runWords.push(p.w);
        if (run > longest) { longest = run; longestWords = runWords.slice(); }
      }
    }
    return { total, changed, longest, longestWords };
  }

  function parseCustom(text) {
    const map = new Map();
    for (const line of (text || '').split('\n')) {
      const m = line.match(/^\s*([A-Za-z'’]+)\s*(?:=|->|→|:)\s*(\S.*?)\s*$/);
      if (m) map.set(m[1].toLowerCase().replace(/’/g, "'"), m[2]);
    }
    return map;
  }

  return { analyse, plan, toText, stats, shown, applyCase, parseCustom, ruleSpelling, LEVELS };
})();
if (typeof module !== 'undefined') module.exports = Respell;
