// Tests for the Lời Đồng Âm engine. Run: node --test tests/engine.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const Respell = require(path.join(__dirname, '..', 'loi-dong-am', 'engine.js'));

const SONGS = {
  amazing: `[Verse 1]
Amazing grace, how sweet the sound
That saved a wretch like me
I once was lost, but now am found
Was blind, but now I see

[Verse 2]
'Twas grace that taught my heart to fear
And grace my fears relieved
How precious did that grace appear
The hour I first believed`,
  silent: `[Verse]
Silent night, holy night
All is calm, all is bright
Round yon Virgin, mother and child
Holy infant so tender and mild
Sleep in heavenly peace
Sleep in heavenly peace`,
  susanna: `[Verse]
I come from Alabama with my banjo on my knee
I'm going to Louisiana, my true love for to see
It rained all night the day I left, the weather it was dry
The sun so hot I froze to death, Susanna, don't you cry`,
};

const run = (text, { level = 'medium', homophones = true, seed = 0, custom = '' } = {}) => {
  const lines = Respell.analyse(text, { homophones, custom: Respell.parseCustom(custom) });
  Respell.plan(lines, level, seed);
  return { lines, text: Respell.toText(lines), stats: Respell.stats(lines) };
};

// Every spelling a word can get, with homophones on.
const spellings = word => Respell.analyse(word, { homophones: true, custom: new Map() })[0].parts[0].alts.map(a => a.text);

test('respells common words so they still sound the same', () => {
  const expected = {
    night: 'nite', grace: 'grayce', love: 'luv', heart: 'hart', enough: 'enuff', through: 'thru', world: 'wurld',
    phone: 'foan', nation: 'nayshun', action: 'akshun', sound: 'sownd', knife: 'nyfe', field: 'feeld',
    home: 'hoam', time: 'tyme', rule: 'rool', happy: 'happie', lonely: 'lonelee', dreams: 'dreemz', sun: 'sunn',
    calling: 'kawling', summer: 'summur', "summer's": "summur's",
  };
  for (const [word, spelling] of Object.entries(expected)) {
    assert.ok(spellings(word).includes(spelling), `${word} should offer ${spelling}, got ${spellings(word)}`);
  }
});

test('never offers a spelling that is sung differently', () => {
  // Each of these was produced by an earlier version of the rules.
  const wrong = {
    know: 'now', knows: 'nowz', known: 'nown', knowing: 'nowing', age: 'ayg', page: 'payg', died: 'deed',
    tried: 'treed', lies: 'lees', view: 'veew', client: 'kleent', lives: 'lyves', gives: 'gyves', stated: 'staytd',
    naked: 'naykd', whom: 'whomm', of: 'off', cover: 'kover', couple: 'kouple', cousin: 'kousin', danger: 'dangur',
    cancer: 'kancur', passenger: 'passengur', colonel: 'kolonel', entry: 'entree', comes: 'koamz', ones: 'oanz',
    coming: 'koming', writing: 'riting', stephen: 'stefen', deny: 'denee', apply: 'applee', body: 'bodee',
    city: 'citee', again: 'agayn', said: 'sayd', give: 'gyve', have: 'hayv', none: 'noan', shall: 'shawl',
  };
  for (const [word, bad] of Object.entries(wrong)) {
    assert.ok(!spellings(word).includes(bad), `${word} must not become ${bad}`);
  }
});

test('keeps tags, punctuation, line breaks and capitals', () => {
  const { text } = run(SONGS.amazing, { level: 'strong' });
  const src = SONGS.amazing.split('\n');
  const out = text.split('\n');
  assert.equal(out.length, src.length);
  assert.equal(out[0], '[Verse 1]');
  assert.equal(out[6], '[Verse 2]');
  out.forEach((line, i) => assert.equal(line.replace(/[A-Za-z']/g, ''), src[i].replace(/[A-Za-z']/g, ''), `line ${i}`));
  assert.match(text, /^Amayzing grayce/m);
  assert.equal(run('SILENT NIGHT', { level: 'strong', homophones: false }).text, 'SYLENT NITE');
});

test('a stronger level changes at least as many words', () => {
  for (const [name, song] of Object.entries(SONGS)) {
    const light = run(song, { level: 'light' }).stats.changed;
    const medium = run(song, { level: 'medium' }).stats.changed;
    const strong = run(song, { level: 'strong' }).stats.changed;
    assert.ok(light <= medium && medium <= strong, `${name}: ${light} ${medium} ${strong}`);
  }
});

test('medium leaves at most two original words in a row when it can', () => {
  for (const name of ['amazing', 'silent']) {
    const { stats } = run(SONGS[name], { level: 'medium' });
    assert.ok(stats.longest <= 2, `${name}: ${stats.longest} words in a row: ${stats.longestWords.join(' ')}`);
  }
});

test('homophones can be turned off', () => {
  const on = run(SONGS.silent, { level: 'strong', homophones: true }).text;
  const off = run(SONGS.silent, { level: 'strong', homophones: false }).text;
  assert.match(on, /knight/);
  assert.doesNotMatch(off, /knight|wholly|piece/);
});

test('another seed gives another version', () => {
  const versions = Object.values(SONGS).map(song => [run(song, { seed: 0 }).text, run(song, { seed: 1 }).text]);
  assert.ok(versions.some(([a, b]) => a !== b));
});

test('the personal list wins, and "word = word" keeps a word', () => {
  const custom = 'lord = lawrd\ngrace = grace\n';
  const { text } = run('Lord, your grace', { level: 'light', custom });
  assert.match(text, /^Lawrd,/);
  assert.match(run('grace grace grace grace grace', { level: 'strong', custom }).text, /^grace grace grace grace grace$/);
  assert.equal(Respell.parseCustom('Night -> Nite\nbad line\nheart: hart').get('night'), 'Nite');
  assert.equal(Respell.parseCustom('heart: hart').get('heart'), 'hart');
});

test('copes with empty text and odd characters', () => {
  assert.equal(run('').text, '');
  assert.equal(run('\n\n').text, '\n\n');
  const odd = 'Don’t <b>cry</b> & 123 — “sing”';
  assert.equal(run(odd, { level: 'strong' }).text.replace(/[A-Za-z’]/g, ''), odd.replace(/[A-Za-z’]/g, ''));
});
