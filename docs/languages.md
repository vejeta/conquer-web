<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->
# Conquer: audience, languages and offline TTS

Research of 27 September 2026 that guides which languages the site, the
tutorial and its narrated video are translated into next. How to add a
language: `web/i18n/README.md`.

## How this was checked

- **Verified** means I read it myself in a primary source (a GitHub README or LICENSE fetched as raw text, or a Kokoro voice file), or saw it in a search-result snippet from the page linked next to it.
- **Snippet only** marks figures that come from a search engine's summary of a page I could not open. The network proxy blocked direct fetches of most sites (huggingface.co, vejeta.com, hackaday.com, lists.debian.org, groups.google.com, ef.com, store.steampowered.com, wikipedia.org). GitHub and PyPI could be fetched. Check these figures before quoting them publicly.
- **[unverified]** marks things from my own knowledge that I could not confirm here.

---

## 1. Who played Conquer: where and when

**Timeline** (from the v5 repo's HISTORY.md, https://github.com/vejeta/conquerv5/blob/master/gpl-release/HISTORY.md, unless another link is given)

| Date | Event |
|---|---|
| 26 Oct 1987 | Ed Barlow posts "conquest – middle earth multi-player game, Part01/05" to comp.sources.games (v02i058). It was renamed Conquer soon after. |
| 23 Jan 1988 | First message from Adam Bryant (in rec.games.empire). |
| 16 Jun 1988 | v3 is posted to comp.sources.games (v04i042, 8 parts). Bug reports go to comp.sources.games.bugs. |
| 1989 | v4 README. Barlow is between jobs with no email, and Adam Bryant takes mail at `adb@bu-cs.bu.edu` (Boston University). There is a mailing list, `conquer-news@bu-cs.bu.edu`. Source: https://github.com/quixadhal/conquer/blob/master/README |
| 1989 | Contributors of that year: **Richard Caley**, University of Edinburgh (map utility), and **Martin Forssen** (PostScript map utilities). Source: https://github.com/vejeta/conquer |
| 1991–92 | v5 is a full rewrite by Adam Bryant, copyright 1992. A v5.0 beta (patchlevel 16) was on FTP at cs.bu.edu, with release planned for "summer '91". Snippet only, from a bit.listserv.games-l "Listing of Empire type games" post: https://groups.google.com/g/bit.listserv.games-l/c/0ybTuugcGWU |
| 1997 | "Conquest newsletter #2/#3" appear in rec.games.empire. |
| 2006–2025 | Relicensing to GPL v3, led by Juan Manuel Méndez Rey ("vejeta"). Bryant gave permission on 23 Feb 2011, Barlow on 12 Mar 2016, and Forssen on 15 Sep 2025. It was discussed on debian-legal in Oct 2006 and tracked as GNU Savannah task #5945. Source: https://github.com/vejeta/conquer |
| Nov 2025 | Hackaday runs "Resurrecting Conquer: A Game From The 1980s". Its snippet says "many students that had access to internet on their universities" built and patched the game. https://hackaday.com/2025/11/11/resurrecting-conquer-a-game-from-the-1980s/ |

**Who played it.** The players were Unix users on university and research networks: people on Usenet and ARPANET, reading comp.sources.games and rec.games.empire. The only institutions I can name from sources are Boston University (Bryant's address and the mailing list) and Edinburgh (Caley). I found no player counts and no country breakdown.

Spain is a documented later pocket of interest. The maintainer discussed the game on es.comp.os.unix, linux.debian.user.spanish and Barrapunto (HISTORY.md above), and wrote a Spanish-language history at https://vejeta.com/historia-del-conquer/. The Swedish-looking name "Forssen" is **not** evidence of a Swedish player base.

**Where the code lives now**

| Repository | What it is |
|---|---|
| https://github.com/vejeta/conquer | v4. GPL v3 in `gpl-release/`, the original in `original/`. Last push 2026-06-22, 17 stars (GitHub API). |
| https://github.com/vejeta/conquerv5 | v5, GPL v3. |
| https://github.com/vejeta/conquer-web | This web front end. |
| https://github.com/quixadhal/conquer | An earlier GitHub mirror of v4 with releases. |

- **Maintainer:** vejeta, Juan Manuel Méndez Rey (https://github.com/vejeta).
- **Distro packages:** I found no Conquer package in Debian, Ubuntu, Fedora, Arch or FreeBSD ports. vejeta runs an unofficial Debian repository (https://debian.vejeta.com/), but I could not confirm that it carries Conquer, because the site was blocked. The comp.sources.games archives are mirrored in many places, and a similar game, "dominion", was recovered from vol. 13 (https://github.com/fantastic-penguin/dominion).
- **Surviving communities:** I found no active Conquer player community, subreddit or Discord. The public trail is the Hackaday article and its comments, plus the GitHub repositories.

---

## 2. Who could play now (2026)

### Communities by interest

| Community | Where they gather | Languages | Fit |
|---|---|---|---|
| **BBS door games** (LORD, Trade Wars, Usurper, Solar Realms Elite) | Telnet BBS Guide lists "hundreds" of telnet BBSes, and new boards still open in 2026 (e.g. Centipede BBS). Also bbsgames.com. Sources: https://www.telnetbbsguide.com/ , https://web.bbsgames.com/ | Mostly English. Some German, Spanish and Portuguese boards [unverified]. | **Very high.** The same "one turn per day, text screen" loop. |
| **Pubnix / tildeverse** | tildeverse.org members: tilde.club, tilde.team, tilde.town, ctrl-c.club, cosmic.voyage, **texto-plano.xyz (Spanish-language)** and others. SDF had 47,572 users as of 2016. Sources: https://tildeverse.org/members/ , https://en.wikipedia.org/wiki/SDF_Public_Access_Unix_System | English, with a Spanish-language tilde | **Very high.** They already live in terminals and IRC. |
| **PBEM / turn-based multiplayer** | **Eressea**: running since 1996, about 80% German players, "a hard core of a few hundred", peak of nearly 3,000 (https://www.eressea.de/en/ ; https://en.wikipedia.org/wiki/Eressea_(video_game)). **Dominions 5/6**: llamaserver, Clockwork bot, several Discords, including a French-speaking one (https://illwiki.com/dom5/community-guide). **Diplomacy**: webDiplomacy (since 2004), Backstabbr, vDiplomacy (28,324 registered, 1,087 playing in one snapshot; https://www.vdiplomacy.com). Atlantis and Stars! communities persist but are small [unverified]. | English, **German** (Eressea), some French | **Highest fit.** They are used to slow turns and diplomacy. |
| **Roguelike players** | r/roguelikes, the roguelikes Discord, RogueBasin, #crawl on Libera, and DCSS servers in Germany and the USA. Source: https://crawl.develz.org/wordpress/howto | English. Russian and Chinese contingents [unverified]. | High for the ASCII, keyboard-driven style. Solo players, though. |
| **MUD players** | Mudlet (still releasing in 2026: https://www.mudlet.org/2026/06/4-21-mudlet-made-better/). **Chinese MUDs**: 北大侠客行 (pkuxkx), open since 1996 from Peking University, with 600+ daily active players claimed (https://pkuxkx.net/ ; https://www.chuapp.com/article/282887.html). There is a Chinese MUD directory at http://mudchina.github.io/. **Korea**: the first Hangul MUD (쥬라기공원, 1994), with about 200,000 regular MUD players by 1996 (https://ko.wikipedia.org/wiki/쥬라기_공원_(온라인_게임) ; https://felipepepe.medium.com/rpgs-in-south-korea-a-brief-history-of-package-online-and-mobile-games-759478508a1c) | English, **Chinese**, Korean (historical) | High. Proof that text multiplayer games live on in Chinese. |
| **Linux/terminal enthusiasts, retro computing** | Hacker News, Hackaday, r/commandline, r/unixporn, r/retrogaming, Lobsters [partly unverified] | English-dominant | Good for discovery, weaker for retention. |
| **Strategy gamers in general (4X, grand strategy)** | Steam, Paradox forums, Reddit, Discord, **Bilibili/Tieba/NGA in China** [unverified] | By Steam language share, see below | Large but fussy about looks. The niche that enjoys text is small. |

**Steam primary-language share, March 2026.** These are snippet-only figures relayed by aggregators (https://www.quantumrun.com/consulting/steam-language-statistics/ , https://www.gamingonlinux.com/2026/03/steam-survey-for-february-2026-shows-a-big-swing-to-simplified-chinese/):

| Language | Share |
|---|---|
| English | 39.1% |
| Simplified Chinese | 22.75% |
| Russian | 9.21% |
| Portuguese (Brazil) | 4.42% |
| Spanish (Spain) | about 4.2% (January) |
| German | 2.96% |
| French | 2.46% |
| Japanese | 2.24% |
| Polish | 1.82% |
| Korean | 1.69% |

Turkey is about 1.5–2% of Steam users by country (https://www.localizedirect.com/posts/turkish-game-localization). Valve said at GDC 2025 that Simplified Chinese passed English as a Steam UI language in 2024 (https://gamedevreports.substack.com/p/valve-chinese-language-surpassed-english).

**Internet users by language, 2025.** Snippet only, from https://en.wikipedia.org/wiki/Languages_used_on_the_Internet and aggregators:

| Language | Users |
|---|---|
| English | about 1.19 billion |
| Chinese | about 888 million |
| Spanish | about 364 million |
| Arabic | about 237 million |
| Portuguese | about 172 million |
| Indonesian | about 99 million or more |

### Regions: community size and how much English is a barrier

EF English Proficiency Index 2025 scores are snippet only (https://www.ef.com/wwen/epi/ , report PDF https://www.ef.com/assetscdn/WIBIwq6RdJvcD9bc8RMd/cefcom-epi-site/reports/2025/ef-epi-2025-english.pdf). As a reference point, Poland scores 600 (rank #15).

| Region | Strategy, retro and terminal scene | English as a barrier |
|---|---|---|
| **China** | Largest Steam language (above). A living Chinese text-MUD culture (pkuxkx). Discord is not reachable, so people gather on QQ groups, Bilibili and Tieba [unverified]. | **High.** EPI 464, "low". |
| **Japan** | 2.24% of Steam. A strong roguelike tradition (e.g. Shiren) [unverified]. | **High.** EPI 446, "very low". In one survey, only 23% of Japanese fans would buy an English-only version (https://alconost.com/en/blog/steam-language-mix-indies , snippet). |
| **Korea** | MUD history above. 1.69% of Steam. | Medium. EPI 522, rank #48 (https://www.ef.com/assetscdn/WIBIwq6RdJvcD9bc8RMd/cefcom-epi-site/fact-sheets/2025/ef-epi-fact-sheet-south-korea-english.pdf). |
| **India** | Large, young and PC-leaning (an HP study says 67% of Gen Z gamers prefer PC: https://www.digit.in/news/laptops/hp-study-genz-gamer-dominate.html). "Most of India's 550 million gamers would like to game in their local language", per the WinZO report (https://www.localizedirect.com/posts/indian-game-localization-factsheet). | Medium. EPI 484, rank #74. The terminal and Linux crowd is largely English-comfortable. |
| **Iran** | An active Steam community despite sanctions (https://steamcommunity.com/groups/Persian ; https://www.aljazeera.com/amp/economy/2019/12/23/locked-out-us-sanctions-are-ruining-online-gaming-in-iran). Fan localization groups are common (https://www.micjournal.org/article_164369_8614ec4dcfaeb2d05dd1403e2353a594.pdf). | Medium. EPI 492, rank #68. Players often have to reach sites through VPNs [unverified]. |
| **Russia** | 9.21% of Steam, the third language. A strong roguelike and hardcore-strategy following [unverified]. | High [unverified; EPI 2025 score not found]. |
| **Poland** | 1.82% of Steam. Strategy and PC culture is strong (CD Projekt, 11 bit) [unverified]. | **Low barrier.** EPI 600, rank #15. |
| **Turkey** | Players make up about 1.5–2% of Steam. Around 50 million gamers. Players demand Turkish, and backlash is reported when it is skipped (https://www.localizedirect.com/posts/turkish-game-localization). | High. EPI 488, "low". |
| **Brazil** | 4.42% of Steam. | High. EPI 482, "low". |
| **Indonesia** | About 99 million internet users in Indonesian. | Medium-high. EPI 471, rank #80. |
| **Arab world** | 375 million or more gamers in MENA. One vendor says "41% only play a game if it is available in Arabic", and a survey of 613 Arab gamers found 64.3% prefer UI and subtitles in Arabic over dubbing (https://www.localizedirect.com/posts/arabic-game-localization ; https://www.tandfonline.com/doi/full/10.1080/0907676X.2021.1926520). | High. Saudi Arabia's EPI is 404, rank #115. |

---

## 3. Recommended languages

**Cost notes for this repository**

- **The game stays in English.** The Conquer binary's screens and help are in English, and only the landing page, guide, tutorial, coach and the terminal menu (`conquer/i18n/`) are localized. Every new language therefore delivers a partly translated experience. This favours audiences that read some English.
- **CJK** needs web fonts (Noto Sans SC, TC, JP or KR) and double-width cells in the 80x24 menu. The menu runs under ncursesw with a UTF-8 locale. xterm.js must handle East Asian Wide characters, and older xterm.js had bugs with CJK width (https://github.com/xtermjs/xterm.js/issues/62). Each menu line has only half as many visible characters.
- **Arabic and Farsi** need `dir="rtl"` pages and mirrored layouts. A terminal menu in RTL is a real problem: xterm.js has no bidi support [unverified; stated from knowledge]. Keep the terminal menu in English, or in transliterated or left-to-right Arabic, for those languages.
- **Hindi (Devanagari)** needs complex text shaping. Terminal emulators, xterm.js included, render conjuncts and matras poorly [unverified]. The web pages themselves render fine.

**Recommended tiers**

| Tier | Language | Reason |
|---|---|---|
| **0 (done)** | English, Spanish | Spanish also covers LatAm, the maintainer's own community and texto-plano. |
| **1** | **Simplified Chinese** | Biggest non-English strategy audience, low English, a proven text-MUD culture. Cost: CJK width in the menu. |
| **1** | **Portuguese (Brazil)** | 4.4% of Steam, low English, Latin script, and cheap because it sits close to Spanish. |
| **1** | **Russian** | 9.2% of Steam, a roguelike and hardcore-strategy crowd, Cyrillic has no layout cost. |
| **1** | **German** | Eressea, whose players are about 80% German, is the closest living analogue to Conquer, and the retro and BBS scene is strong. English is good in Germany, but German PBEM players are used to German rules. |
| **2** | **Japanese** | Low English and willing to pay, but a small audience for a Western text wargame. CJK cost. |
| **2** | **French** | 2.5% of Steam and a French Dominions Discord. Latin script. |
| **2** | **Turkish** | Very localization-sensitive, and Latin script is cheap. The web pages must handle dotted and dotless İ/ı correctly. |
| **2** | **Polish** | Strong strategy culture. English is already good (EPI 600), so this is goodwill more than reach. |
| **3** | **Korean** | MUD heritage, but English is medium and the community is on its own platforms. CJK cost. |
| **3** | **Italian** | Moderate reach and cheap. English is only medium. |
| **3** | **Indonesian** | Large and growing, but no evidence of a strategy or terminal niche. Latin script, so cheap. |
| **4** | **Farsi** | A motivated community with a tradition of fan translation, but RTL cost, sanctions and access friction. Do it only if a volunteer translator appears. |
| **4** | **Arabic** | Huge reach and a real preference for Arabic UI, but RTL cost and weak fit with a niche Unix wargame. Same "volunteer-driven" advice. |
| **4** | **Hindi** | See below. |
| **Not yet** | **Traditional Chinese** | Taiwan and Hong Kong users read Simplified with some friction. Add it only as an OpenCC-converted variant after Simplified exists [conversion approach from knowledge]. |

**Position on each language asked about**

- **Chinese.** Do Simplified first. Traditional can be derived with OpenCC plus a light review.
- **Japanese and Korean.** Worth doing only after the web CJK work is paid for by Chinese. Japanese comes before Korean.
- **Hindi.** English is enough for the Indian audience this game can realistically reach: Linux, terminal and PBEM users who already use English. The Hindi-demand statistics describe mobile and new internet users, not people who play Unix wargames. Hindi is low priority.
- **Farsi and Arabic.** RTL doubles the layout work, and the terminal menu cannot be RTL. Add them later, or only with a native volunteer.
- **Russian, Polish, Turkish, Indonesian, German, French, Portuguese (Brazil), Italian.** All use Latin or Cyrillic script, so each costs only the translation. Order them as in the tiers above.

---

## 4. Offline TTS for the narrated tutorial

**State at the time of this research.** The tutorial used Kokoro via kokoro-onnx with `bm_george` for English and `em_alex` for Spanish (since replaced by Qwen3-TTS, see `tools/tutorial/README.md`). Kokoro's own voice metadata grades these voices **C** and **D** respectively (https://github.com/hexgrad/kokoro/blob/main/kokoro.js/src/voices.js).

**Model licenses and languages.** All verified from the repository README or LICENSE on GitHub unless marked otherwise.

| Model | License (code / weights) | Languages | Publish OK? | Notes |
|---|---|---|---|---|
| **Kokoro-82M v1.0** | Apache-2.0 weights | en-US, en-GB, es, fr, hi, it, ja, pt-BR, zh | **Yes** | Fixed voices, no cloning, runs on CPU. Quality grades from voices.js: best English `af_heart` A, `af_bella` A-, `bf_emma` B-; French `ff_siwis` B-; Hindi `hf_alpha`/`hf_beta`/`hm_omega`/`hm_psi` C; Italian `if_sara`/`im_nicola` C; Japanese `jf_alpha` C+; Chinese `zf_*`/`zm_*` D; Spanish `ef_dora`/`em_alex`/`em_santa` D; pt-BR `pf_dora`/`pm_alex`/`pm_santa` D. https://github.com/hexgrad/kokoro |
| **Piper** (piper1-gpl) | GPL-3.0 engine. **Per-voice licenses** in each voice's MODEL_CARD. | 40+ languages, including ar_JO, fa_IR, hi_IN, id_ID, pl_PL, ru_RU, tr_TR, zh_CN, de, fr, it, pt_BR | **Per voice** | Robotic next to newer models. The docs say "Some voices may have restrictive licenses", so check each MODEL_CARD. Voices include fa_IR-{amir,ganji,gyro,reza_ibrahim}, ar_JO-kareem, hi_IN-{pratham,priyamvada}, tr_TR-{dfki,fahrettin,fettah}, pl_PL-{gosia,darkman,mc_speech}, ru_RU-{irina,denis,dmitri,ruslan}, pt_BR-{faber,cadu,jeff}, de_DE-thorsten (CC0 [unverified]). https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md ; https://github.com/rhasspy/piper/blob/master/VOICES.md |
| **MeloTTS** | MIT | en (US/UK/IN/AU), es, fr, zh (mixed with en), ja, ko | **Yes** | Real-time on CPU. Mid quality. https://github.com/myshell-ai/MeloTTS |
| **Chatterbox Multilingual V3** (0.5B) | MIT | ar, da, de, el, en, es, fi, fr, he, hi, it, ja, ko, ms, nl, no, pl, pt, ru, sv, sw, tr, zh. Dedicated finetunes for zh-cmn, es-es, es-mx, pt-br, pt-pt, hi. | **Yes** | Zero-shot voice cloning, so you need a reference voice you have rights to. Every output carries an imperceptible **PerTh watermark**. https://github.com/resemble-ai/chatterbox |
| **Qwen3-TTS** (0.6B / 1.7B) | Apache-2.0 | zh, en, ja, ko, de, fr, ru, pt, es, it | **Yes** | Built-in speakers: Vivian, Serena, Uncle_Fu, Dylan, Eric (zh); Ryan, Aiden (en); Ono_Anna (ja); Sohee (ko). Also voice design from text and cloning. https://github.com/QwenLM/Qwen3-TTS |
| **VoxCPM2** (2B, April 2026) | Apache-2.0 code and weights | 30 languages: ar, my, zh, da, nl, en, fi, fr, de, el, he, hi, id, it, ja, km, ko, lo, ms, no, pl, pt, ru, es, sw, sv, tl, th, tr, vi | **Yes** | 48 kHz output, voice design and cloning. No Farsi. https://github.com/OpenBMB/VoxCPM |
| **OmniVoice** (k2-fsa) | Apache-2.0 | 646 languages. Training hours include Persian 366 h, Turkish 125 h, Hindi 117 h, Standard Arabic 1,484 h, Polish 912 h. | **Yes** | Cloning is the stable mode. Voice design was trained on zh and en only. https://github.com/k2-fsa/OmniVoice/blob/master/docs/languages.md |
| **MOSS-TTS family** | Apache-2.0 | zh, en, ja, European languages. The Nano model is multilingual. | **Yes** | https://github.com/OpenMOSS/MOSS-TTS |
| **CosyVoice 3** (Fun-CosyVoice3-0.5B) | Apache-2.0 repo | zh, en, ja, ko, de, es, fr, it, ru, plus 18 or more Chinese dialects | **Yes** (repo license; weights card not checked) | Best-in-class for Chinese. https://github.com/FunAudioLLM/CosyVoice |
| **Indic Parler-TTS** | Apache-2.0 | 21 languages, including Hindi and Indian English. 69 named voices. | **Yes** | Snippet only (HF blocked): https://huggingface.co/ai4bharat/indic-parler-tts |
| **Parler-TTS** (Mini/Large) | Apache-2.0 | English | Yes | https://github.com/huggingface/parler-tts |
| **IndicF5** | MIT (snippet) | 11 Indian languages | Yes, but it is cloning-only | Needs a licensed reference voice. https://huggingface.co/ai4bharat/IndicF5 |
| **F5-TTS** | MIT code, **CC-BY-NC weights** (Emilia training data) | zh, en | **No** | https://github.com/SWivid/F5-TTS |
| **Fish Audio S2 Pro / OpenAudio** | **Fish Audio Research License**: non-commercial use free, commercial use needs a paid license. Requires "Built with Fish Audio" attribution. You own the outputs. | 80+ languages | **Only non-commercial** | A free hobby site is arguably "non-commercial", but it is a revocable license, so avoid it. https://github.com/fishaudio/fish-speech/blob/main/LICENSE |
| **XTTS-v2** (Coqui) | MPL-2.0 code, **CPML weights (non-commercial)**. Coqui shut down in January 2024, so no commercial license can be bought. | 17 languages | **No** | https://github.com/coqui-ai/TTS/issues/3490 |
| **Meta MMS-TTS** | **CC-BY-NC 4.0** | 1,100+ languages | **No** | https://huggingface.co/facebook/mms-tts |
| **IndexTTS** | bilibili Model Use License (custom) | zh, en | Check the terms | https://github.com/index-tts/index-tts |
| **VibeVoice** (Microsoft) | MIT, but the TTS code was removed in September 2025 and is described as "research only" | — | **Avoid** | https://github.com/microsoft/VibeVoice |

**Voice-rights rule for cloning models.** Chatterbox, VoxCPM, OmniVoice, IndicF5 and Qwen Base all clone a reference voice. Use a voice you own, such as the maintainer's own recording, or a CC0 or CC-BY speaker. Alternatively, use a model's built-in or designed voice (Qwen3-TTS speakers, VoxCPM or Qwen voice design, Kokoro voices).

**Best option per target language**

| Language | Best offline option that clears the license bar | Second choice | Fallback |
|---|---|---|---|
| English (upgrade) | Kokoro `af_heart` (A) or `bf_emma` (B-) instead of `bm_george` (C). Or Qwen3-TTS `Ryan`/`Aiden`. | Chatterbox V3 | — |
| Spanish (upgrade) | Chatterbox es-es finetune (with your own reference voice), or Qwen3-TTS / VoxCPM2 | Kokoro `em_alex` (D, current) | — |
| Simplified Chinese | Qwen3-TTS `Vivian`/`Serena`/`Uncle_Fu`, or CosyVoice 3 | Chatterbox zh-cmn, MeloTTS ZH | zh subtitles over English audio |
| Traditional Chinese | Same audio as Simplified (Mandarin), with Traditional subtitles | — | Subtitles |
| Portuguese (Brazil) | Chatterbox pt-br finetune | VoxCPM2 / Qwen3-TTS (pt). Kokoro `pf_dora` is only D. | Subtitles |
| Russian | Qwen3-TTS (ru), VoxCPM2 | Chatterbox, Piper `ru_RU-irina`/`denis` (check the model cards) | Subtitles |
| German | Qwen3-TTS (de), VoxCPM2 | Chatterbox, Piper `de_DE-thorsten` | Subtitles |
| French | Qwen3-TTS (fr) | Kokoro `ff_siwis` (B-), MeloTTS FR | Subtitles |
| Japanese | Qwen3-TTS `Ono_Anna` | Kokoro `jf_alpha` (C+), MeloTTS JP | Subtitles |
| Korean | Qwen3-TTS `Sohee` | MeloTTS KR, Chatterbox | Subtitles |
| Italian | Qwen3-TTS (it), VoxCPM2 | Kokoro `if_sara`/`im_nicola` (C) | Subtitles |
| Polish | VoxCPM2, Chatterbox | Piper `pl_PL-gosia`/`darkman` (check the model cards) | Subtitles |
| Turkish | VoxCPM2, Chatterbox | Piper `tr_TR-fahrettin`/`fettah` (check the model cards), OmniVoice | Subtitles |
| Indonesian | VoxCPM2 | OmniVoice, Piper `id_ID` | Subtitles |
| Hindi | Indic Parler-TTS (Apache, named speakers) or Chatterbox hi finetune | Kokoro `hf_alpha` (C), IndicF5 with your own voice | **Subtitles over English audio are fine for this audience** |
| Arabic | VoxCPM2, Chatterbox (ar) | OmniVoice, Piper `ar_JO-kareem` | Subtitles |
| Farsi | OmniVoice (Apache, 366 h of Persian, cloning) | Piper `fa_IR-amir`/`ganji`/`gyro` (check the model cards) | Subtitles |

**Cloud services: terms for publishing the audio**

| Service | Terms |
|---|---|
| **Azure Speech** | Prebuilt neural voices can be used commercially on the **paid tier**. No royalties are owed, but AI-voice disclosure is expected. Source: Microsoft Q&A, e.g. https://learn.microsoft.com/en-us/answers/questions/5792674/ |
| **Google Cloud TTS** | Google claims no ownership of the content. Check the service terms for the voice types you use (https://cloud.google.com/text-to-speech/docs/data-logging). |
| **ElevenLabs** | The free plan requires attribution and does not allow commercial use. Paid plans (from about $5–6 a month) grant commercial rights that remain after cancelling (https://help.elevenlabs.io/hc/en-us/articles/13313564601361). |

All three are online services, so they fail the offline requirement. They are listed only as fallbacks.

---

## Recommendation

Add languages in this order:

1. Simplified Chinese, Portuguese (Brazil), Russian and German first.
2. French, Japanese, Turkish and Polish next.
3. Korean, Italian and Indonesian after that.
4. Hold Farsi, Arabic and Hindi until a native volunteer appears. English is sufficient for the Indian terminal audience, and RTL scripts cannot be shown properly in the terminal menu.

For every language, translate the web pages, coach and subtitles first. Only narrate a language once its subtitles exist.

For voices, replace the current C/D-graded Kokoro narrators:

- **Qwen3-TTS** (Apache-2.0) covers zh, en, ja, ko, de, fr, ru, pt, es and it with named built-in speakers.
- **VoxCPM2** (Apache-2.0, 30 languages) or **Chatterbox Multilingual V3** (MIT, watermarked) covers pl, tr, id, ar and hi. Use a reference voice the project owns.
- **OmniVoice** (Apache-2.0) or a license-checked Piper voice covers Farsi.
- Keep Kokoro only where it grades B- or better (en `af_heart`/`bf_emma`, fr `ff_siwis`).

Do not use F5-TTS, XTTS-v2, MMS or Fish Audio S2 for published audio. Their weights are licensed for non-commercial use only.
