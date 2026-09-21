# Careers-URL triage

Generated 2026-09-21. **Supersedes the 2026-09-08 version entirely** — that one
ranked 529 companies by an agent's judgement of which "employ audio engineers at
depth", and its population predates both the chrome filter and the clinical-hearing
filter. Nothing below is a judgement about a company's importance.

Read-only: producing this wrote nothing to the database or to the seed.

## What changed since the old file

The old file treated "the scrape fails" and "the stored rows are junk" as one
defect in the generic extractor. That was wrong. The dominant cause is that the
**seeded `careers_url` does not point at a job board** — it points at a homepage, an
about page, a staff-bio page or a press release. `page loaded but no job links found`
is usually the extractor correctly refusing to parse an about page.

Measured across the 732 scraped companies, URL shape predicts the outcome:

| seeded URL shape | companies | % grading healthy |
| --- | --- | --- |
| ATS host | 122 | 44.6% |
| careers vocabulary in host or path | 490 | 8.9% |
| neither | 110 | 1.7% |
| known-bad page | 10 | 0.0% |

## How this is ordered

Two measured quantities, no guesswork:

1. **Jobs actually found at a candidate URL.** `discover_careers_urls` probed each
   company's own domain and ran the real extractor against what it found. A count
   here means that many parseable jobs, not a guess.
2. **Category yield** — for each seed category, the share of its companies that
   contribute to the board multiplied by the median board rows of those that do.
   Headphones & Personal Audio scores 26% x 15; Audio Accessories & Cables has zero
   contributors out of 25.

   *Caveat worth holding:* category yield measures what currently works, and what
   currently works is partly an accident of which URLs happen to be right. A
   category where most URLs are broken looks unproductive for that reason. It is a
   tiebreaker here, never the primary sort.

## The finding that should change how you spend time here

I ran `check_url` against 10 of the 16 automatically proposed replacement URLs.
All 10 parse jobs. **Eight yield no audio jobs at all, and the other two yield four between them.**

| candidate | jobs parsed | audio jobs |
| --- | --- | --- |
| Nintendo | 54 | **3** |
| PACCAR | 211 | **1** |
| LG Electronics | 47 | 0 |
| ITU-R | 46 | 0 |
| Paradox Interactive | 20 | 0 |
| Volkswagen | 12 | 0 |
| AudioQuest | 5 | 0 |
| Rivian | 2 | 0 |
| TuneIn | 1 | 0 |
| Paradigm | 1 | 0 |

So a broken URL is real, and fixing it usually returns **nothing to the audio
board**. The URL being wrong and the company being worth scraping are separate
questions, and the second one is where the value is. Order by category, not by
how broken the URL looks.

A further five automated proposals are wrong on inspection and are excluded from
Tier 1 below: Bungie and Splice were checked in a previous session and return
zero, ZTE's proposal is Recruitee's own marketing site, Frontier Audio's is
Wellfound's candidate signup page, and University of York's is the student
careers service. That is 5 bad out of 16 before anyone opens a browser.

## Tier 1 — a replacement URL was found and it parses (9)

A candidate URL on the company's own domain returned jobs the real extractor
could read. Rows marked `checked` I ran through `check_url` myself; the audio
column is what it would actually add to the board. Rows marked `UNCHECKED` are
the tool's word only — run
`python -m scraper.check_url <url> --name "<company>"` before trusting one.

| company | category | verified? | jobs | **audio jobs** | replace with |
| --- | --- | --- | --- | --- | --- |
| Nintendo | Gaming, VR & Immersive Audio | checked | 54 | **3** | `https://careers.nintendo.com/jobs/` |
| PACCAR (Kenworth/Peterbilt) | Automotive OEMs | checked | 211 | **1** | `https://jobs.paccar.com/go/Engineering-Jobs/2706200/` |
| Hilson Moran | Acoustic Consulting & Engineering | UNCHECKED | 5 | ? | `https://www.tyrenshm.com/careers/vacancies/` |
| LG Electronics | Consumer Electronics & Tech | checked | 47 | **0** | `https://boards.greenhouse.io/lgelectronics` |
| Paradox Interactive | Gaming, VR & Immersive Audio | checked | 20 | **0** | `https://career.paradoxplaza.com/jobs` |
| Volkswagen | Automotive OEMs | checked | 12 | **0** | `https://www.volkswagen-karriere.de/de.html` |
| Rivian | Automotive OEMs | checked | 2 | **0** | `https://rivian.com/careers` |
| TuneIn | Streaming & Music Services | checked | 1 | **0** | `https://tunein.com/careers` |
| ITU-R | Audio IP & Licensing | checked | 46 | **0** | `https://jobs.itu.int/go/View-all-categories/8942455/` |

## Tier 2 — URL is provably not a job board, productive category (36)

No candidate found automatically, so these need a human to locate the board.
Ordered by category yield.

| company | category | scope | fails | seeded URL |
| --- | --- | --- | --- | --- |
| Jaybird | Headphones & Personal Audio | native | 12 | `https://support.logi.com/hc/en-us` |
| Plantronics | Headphones & Personal Audio | native | 12 | `https://www.hp.com/us-en/poly.html` |
| Raal Requisite | Headphones & Personal Audio | native | 12 | `https://requisiteaudio.com/` |
| Shozy | Headphones & Personal Audio | native | 12 | `https://www.shozyaudio.com/password` |
| Turtle Beach | Headphones & Personal Audio | native | 12 | `https://www.turtlebeach.com/pages/influencers` |
| JLab Audio | Headphones & Personal Audio | native | 3 | `https://www.jlab.com/products/epic-keyboard-mouse-bundle` |
| Poly (HP) | Headphones & Personal Audio | native | 0 | `https://www.hp.com/us-en/poly.html` |
| Inventis | Hearing Aid & Hearing Tech | native | 20 | `https://inventis.it/it-it/soluzioni/medicina-del-lavoro` |
| Decibels | Hearing Aid & Hearing Tech | native | 19 | `https://www.domaineasy.com/buy-domain/www.decibels.com` |
| Eargo | Hearing Aid & Hearing Tech | native | 18 | `https://www.eargo.com/` |
| EarQ | Hearing Aid & Hearing Tech | native | 12 | `https://www.cq-partners.com/what-we-do/business-planning/training-develo` |
| Embrace Hearing | Hearing Aid & Hearing Tech | native | 12 | `https://embracehearing.com/user-guides` |
| Lexie Hearing | Hearing Aid & Hearing Tech | native | 12 | `https://www.lexiehearing.com/us` |
| WS Audiology (Signia/Widex) | Hearing Aid & Hearing Tech | native | 3 | `https://www.wsa.com/` |
| Nuheara | Hearing Aid & Hearing Tech | native | 0 | `https://www.nuheara.com/team-behind-the-tech/` |
| Akustiks | Acoustic Consulting & Engineering | native | 12 | `https://akustiks.com/` |
| Hush Acoustics | Acoustic Consulting & Engineering | native | 12 | `https://www.hushacoustics.co.uk/technical-resources/environmental/` |
| Threshold Acoustics | Acoustic Consulting & Engineering | native | 12 | `https://threshold.llc/team` |
| Cadence Design Systems | Consumer Electronics & Tech | partial | 19 | `https://www.cadence.com/en_US/home/errors/accessdenied.html` |
| Creative Technology | Consumer Electronics & Tech | partial | 12 | `https://us.creative.com:443/` |
| Honor | Consumer Electronics & Tech | partial | 12 | `https://www.honor.com/global/404/` |
| ZTE | Consumer Electronics & Tech | partial | 12 | `https://www.zte.com.cn/china/404.html` |
| CEVA | Consumer Electronics & Tech | partial | 3 | `https://www.ceva-ip.com/` |
| Fujitsu | Consumer Electronics & Tech | partial | 2 | `https://global.fujitsu/en-global` |
| AIVA | AI/ML Audio | native | 24 | `https://www.aiva.ai/` |
| Hit'n'Mix | AI/ML Audio | native | 12 | `https://hitnmix.com` |
| Echo Digital Audio | Audio Interfaces & Converters | native | 12 | `http://www.echoaudio.com/about/` |
| Qu-Bit Electronix | Electronic Musical Instruments | native | 12 | `https://www.qubitelectronix.com/team` |
| Roland | Electronic Musical Instruments | native | 12 | `https://www.youtube.com/watch?v=jaO0LffIs1A` |
| Soma Laboratory | Electronic Musical Instruments | native | 12 | `https://somasynths.com/team/` |
| Spitch | Voice & Speech Technology | native | 19 | `https://spitch.ai/de/` |
| Voiceflow | Voice & Speech Technology | native | 19 | `https://www.voiceflow.com/about#careers` |
| Voiser | Voice & Speech Technology | native | 18 | `https://www.voiser.net/` |
| SoapBox Labs | Voice & Speech Technology | native | 3 | `https://www.curriculumassociates.com/about/ailabs` |
| Vintage King Audio | Audio Retailers & Distributors | partial | 12 | `https://vintageking.com/recording/studio-furniture/19-outboard-racks` |
| Musician's Friend | Audio Retailers & Distributors | partial | 0 | `https://www.musiciansfriend.com/pages/ways-to-pay` |

## Tier 3 — URL is provably not a job board, low-yield category (76)

Same defect, but no company in these categories contributes much to the board
today. Worth fixing only after tiers 1 and 2, and worth asking whether some of
these belong in the seed at all.

| company | category | scope | fails | seeded URL |
| --- | --- | --- | --- | --- |
| Actran (MSC Software) | Audio Testing & Measurement | native | 21 | `https://hexagon.com/company/newsroom/press-releases/2025/hexagon-agrees-` |
| SOUNDFlow | Audio Testing & Measurement | native | 20 | `https://voxxintl.zendesk.com/hc/en-us` |
| OmniMic | Audio Testing & Measurement | native | 18 | `https://www.omnimic.com/lander` |
| Free Field Technologies | Audio Testing & Measurement | native | 1 | `https://hexagon.com/company/newsroom/press-releases/2025/hexagon-agrees-` |
| LMS (Siemens) | Audio Testing & Measurement | native | 0 | `https://www.siemens.com/en-us/` |
| Immersive Audio | Gaming, VR & Immersive Audio | native | 19 | `https://www.immersiveaudio.com/lander` |
| Deep Silver | Gaming, VR & Immersive Audio | native | 12 | `https://www.animefactory.it/` |
| NCSoft | Gaming, VR & Immersive Audio | native | 12 | `https://www.nc.com/` |
| Larian Studios | Gaming, VR & Immersive Audio | native | 3 | `https://eu.merch.larian.com/products/divinity-original-sin-the-boardgame` |
| Nexon | Gaming, VR & Immersive Audio | native | 3 | `https://www.nexon.com/main/en/error?aspxerrorpath=%2Fen%2Fcareers` |
| Spatial | Gaming, VR & Immersive Audio | native | 3 | `https://www.spatial.io/team` |
| Dear Reality | Gaming, VR & Immersive Audio | native | 2 | `https://www.sennheiser.com/en-us/immersive/dear-reality` |
| GungHo Online | Gaming, VR & Immersive Audio | native | 2 | `https://www.gungho.com/investments/#opportunities` |
| Ubisoft | Gaming, VR & Immersive Audio | native | 0 | `https://www.ubisoft.com/en-us/company/404` |
| RF Venue | Professional Audio & Live Sound | native | 19 | `https://www.rfvenue.com/about#jobs` |
| Audio Ltd | Professional Audio & Live Sound | native | 18 | `https://www.sounddevices.com/` |
| Line 6 | Professional Audio & Live Sound | native | 18 | `https://yamahaguitargroup.com/company/#careers` |
| Wheatstone | Professional Audio & Live Sound | native | 18 | `https://wheatstone.com/contact-us/` |
| Electro-Voice | Professional Audio & Live Sound | native | 13 | `https://ev.com:443/new-cars` |
| Fulcrum Acoustic | Professional Audio & Live Sound | native | 12 | `https://www.fulcrum-acoustic.com/projects/benson-center-for-arts-and-lea` |
| McCauley Sound | Professional Audio & Live Sound | native | 12 | `https://www.mccauleysound.com/` |
| Two Notes Audio | Professional Audio & Live Sound | native | 12 | `http://twonotes.com/` |
| Digigram | Professional Audio & Live Sound | native | 3 | `https://www.digigram.com/` |
| Fractal Audio Systems | Professional Audio & Live Sound | native | 3 | `https://www.fractalaudio.com/p-fx8-multieffects-pedalboard/` |
| Mackie DL | Professional Audio & Live Sound | native | 3 | `https://mackie.com/` |
| Evertz Microsystems | Professional Audio & Live Sound | native | 0 | `https://evertz.com/` |
| Zaxcom | Professional Audio & Live Sound | native | 0 | `https://zaxcom.com/ibc-2026/` |
| Blaupunkt | Car Audio | native | 12 | `https://www.blaupunkt.com/en-us/` |
| Rock Heritage | Recording Studios & Post Houses | native | 19 | `https://www.rockheritage.com/lander` |
| Flik | Recording Studios & Post Houses | native | 12 | `https://www.flik.com/404-page-not-found/` |
| Rumblefish | Recording Studios & Post Houses | native | 12 | `https://www.rumblefish.com/team/` |
| Universal Production Music | Recording Studios & Post Houses | native | 12 | `https://www.universalproductionmusic.com:443/en-us` |
| Musicbed | Recording Studios & Post Houses | native | 3 | `https://www.musicbed.com/` |
| The Music Bed | Recording Studios & Post Houses | native | 0 | `https://www.musicbed.com/` |
| Equator Sound | Audio Plugins & Virtual Instruments | native | 19 | `https://www.equatorsound.com/lander` |
| Dehumaniser | Audio Plugins & Virtual Instruments | native | 12 | `https://afdam.com/` |
| Devicemarket | Audio Plugins & Virtual Instruments | native | 12 | `https://devicemarket.com/` |
| EastWest Sounds | Audio Plugins & Virtual Instruments | native | 12 | `https://www.soundsonline.com/` |
| Hearing Health Foundation | Audio Health & Wellness | native | 12 | `https://hearinghealthfoundation.org/help` |
| QuietOn | Audio Health & Wellness | native | 12 | `https://quieton.com` |
| Hyundai Motor | Automotive OEMs | partial | 12 | `https://www.hyundai.com/worldwide/en` |
| Kawasaki Motors | Automotive OEMs | partial | 2 | `https://www.kawasaki.com/en-us/` |
| EarMaster | Music Education Technology | partial | 19 | `https://www.earmaster.com/company/work-at-earmaster.html` |
| University of York Audio Lab | Music Education Technology | partial | 18 | `https://www.york.ac.uk/study/work/` |
| Groove3 | Music Education Technology | partial | 12 | `https://www.groove3.com/` |
| Puremix | Music Education Technology | partial | 12 | `https://www.puremix.com/` |
| JamPlay | Music Education Technology | partial | 0 | `https://jamplay.com:443/` |
| NYU Music Technology | Music Education Technology | partial | 0 | `https://www.nyu.edu/about/university-initiatives/nyu-irl.html` |
| dCS | Hi-Fi & Consumer Speakers | native | 18 | `https://dcsaudio.com/` |
| Triangle Loudspeakers | Hi-Fi & Consumer Speakers | native | 18 | `https://trianglehifi.us/` |
| Davis Acoustics | Hi-Fi & Consumer Speakers | native | 12 | `https://davis-acoustics.com/en/teamnv/` |
| Harbeth Audio | Hi-Fi & Consumer Speakers | native | 12 | `https://harbeth.co.uk/` |
| Heco Audio | Hi-Fi & Consumer Speakers | native | 12 | `https://heco-audio.de/Ambient-Line/` |
| Hegel Music Systems | Hi-Fi & Consumer Speakers | native | 12 | `https://www.hegel.com/en/` |
| SVS | Hi-Fi & Consumer Speakers | native | 12 | `https://www.svsound.com/pages/about-us` |
| System Audio | Hi-Fi & Consumer Speakers | native | 12 | `https://www.system-audio.com/product-category/active-wireless-speakers/` |
| KEF | Hi-Fi & Consumer Speakers | native | 3 | `https://us.kef.com/` |
| BeatMaker (Intua) | DAW & Music Production Software | native | 12 | `https://intua.net/` |
| Endlesss | DAW & Music Production Software | native | 12 | `https://endlesss.fm/` |
| McDSP | DAW & Music Production Software | native | 12 | `https://mcdsp.com/` |
| Magix (Samplitude/Sequoia) | DAW & Music Production Software | native | 3 | `https://www.magix.com/us/` |
| Stem | Streaming & Music Services | partial | 20 | `https://stem.is/` |
| Ditto Music | Streaming & Music Services | partial | 19 | `https://login.dittomusic.com/en/` |
| Bandsintown | Streaming & Music Services | partial | 18 | `https://www.bandsintown.com/a/7488894` |
| Deezer | Streaming & Music Services | partial | 12 | `https://www.deezer-investors.com/` |
| Luminary | Streaming & Music Services | partial | 12 | `https://luminarypodcasts.com/?country=US` |
| Sounds.com | Streaming & Music Services | partial | 3 | `https://www.native-instruments.com:443/` |
| Beyma | Transducer & Driver Manufacturers | native | 18 | `https://www.beyma.com/en/home/` |
| Omnimount | Audio Accessories & Cables | native | 18 | `https://www.ergotron.com/omnimount` |
| Funktion-One | DJ Equipment | native | 12 | `https://funktion-one.com/about/` |
| Klotz | Audio Accessories & Cables | native | 12 | `https://www.klotz-ais.com/` |
| Virtual DJ (Atomix) | DJ Equipment | native | 12 | `https://virtualdj.com/atomixproductions/` |
| Middle Atlantic | Audio Accessories & Cables | native | 3 | `https://www.legrandav.com/products/middle_atlantic_products` |
| Radial Engineering | Audio Accessories & Cables | native | 3 | `https://www.radialeng.com/keyboard` |
| Ultimate Support | Audio Accessories & Cables | native | 3 | `https://www.ultimatesupport.com/collections/guitar-stands-pedalboards-ac` |
| Sanus | Audio Accessories & Cables | native | 0 | `https://www.sanus.com/en_US/` |

## Tier 4 — NOT a URL problem (195)

The seeded URL does look like a careers page, or the company still has live board
rows, and the scrape fails anyway. Mostly parser, JavaScript or blocking problems,
which belong on a different list from this one.

**But not all of them** — the shape test has false negatives, because `recruit` and
`opportunit` match any path containing them. Hidizs sits here on
`/pages/influencer-recruit`, which recruits influencers, not engineers, and Master &
Dynamic on `/pages/halliburton-opportunity`, which is an oilfield services company.
Both are URL errors wearing careers vocabulary. Skim this tier for more of them
before assuming it is all parser work.

| company | category | scope | fails | seeded URL |
| --- | --- | --- | --- | --- |
| BLON | Headphones & Personal Audio | native | 20 | `https://www.blonaudio.com/Job.html` |
| Hidizs | Headphones & Personal Audio | native | 19 | `https://www.hidizs.net/pages/influencer-recruit` |
| THX Ltd | Headphones & Personal Audio | native | 19 | `https://www.thx.com/careers` |
| Audeze | Headphones & Personal Audio | native | 18 | `https://www.audeze.com/pages/careers` |
| Audio-Technica | Headphones & Personal Audio | native | 18 | `https://www.audio-technica.com/en-us/careers` |
| Master & Dynamic | Headphones & Personal Audio | native | 18 | `https://www.masterdynamic.com/pages/halliburton-opportunity` |
| Shanling | Headphones & Personal Audio | native | 18 | `https://www.shenzhenaudio.com/pages/careers` |
| Shokz | Headphones & Personal Audio | native | 18 | `https://shokz.com/pages/careers` |
| Warwick Acoustics | Headphones & Personal Audio | native | 18 | `https://warwickacoustics.com/careers/` |
| Skullcandy | Headphones & Personal Audio | native | 2 | `https://www.skullcandy.com/pages/join-us` |
| Earlens | Hearing Aid & Hearing Tech | native | 19 | `https://www.earlens.com/work-with-us` |
| Natus Medical | Hearing Aid & Hearing Tech | native | 19 | `https://natus.com/careers/` |
| Olive Union | Hearing Aid & Hearing Tech | native | 18 | `https://www.oliveunion.com/pages/careers` |
| Treble | Hearing Aid & Hearing Tech | native | 5 | `https://treblehealth.com/careers/` |
| Vivosonic | Hearing Aid & Hearing Tech | native | 3 | `https://www.vivosonic.com/careers` |
| Sandy Brown Associates | Acoustic Consulting & Engineering | native | 21 | `https://www.sandybrown.com/careers/` |
| WSDG (Walters-Storyk Design Group) | Acoustic Consulting & Engineering | native | 19 | `https://wsdg.com/careers/` |
| Auralex Acoustics | Acoustic Consulting & Engineering | native | 18 | `https://auralex.com/careers/` |
| Kinetics Noise Control | Acoustic Consulting & Engineering | native | 18 | `https://kineticsnoise.com/resources/careers` |
| Talaske Acoustics | Acoustic Consulting & Engineering | native | 18 | `https://www.talaske.com/careers` |
| Theatre Projects | Acoustic Consulting & Engineering | native | 18 | `https://theatreprojects.com/careers/` |
| Stantec | Acoustic Consulting & Engineering | native | 5 | `https://www.stantec.com/en/careers` |
| Huawei | Consumer Electronics & Tech | partial | 20 | `https://career.huawei.com/cn` |
| DSP Concepts | Consumer Electronics & Tech | partial | 18 | `https://dspconcepts.com/careers` |
| Oppo | Consumer Electronics & Tech | partial | 18 | `https://careers.oppo.com/university/oppo/` |
| Vivo | Consumer Electronics & Tech | partial | 17 | `https://career.vivo.com/home` |
| Realtek Semiconductor | Consumer Electronics & Tech | partial | 12 | `https://www.realtek.com/en/careers` |
| Fairphone | Consumer Electronics & Tech | partial | 3 | `https://www.fairphone.com/team` |
| Auddia | AI/ML Audio | native | 18 | `https://www.auddia.com/careers` |
| Tortoise TTS | AI/ML Audio | native | 18 | `https://worldturtleday.org/join-the-movement/` |
| Audioshake | AI/ML Audio | native | 3 | `https://www.audioshake.ai/audioshake-careers` |
| LANDR | AI/ML Audio | native | 2 | `https://www.landr.com/careers` |
| Antelope Audio | Audio Interfaces & Converters | native | 4 | `https://en.antelopeaudio.com/careers/` |
| Expressive E | Electronic Musical Instruments | native | 19 | `https://www.expressivee.com/category/3-careers` |
| Make Noise | Electronic Musical Instruments | native | 19 | `https://www.makenoisemusic.com/careers/` |
| WMD (William Matthew Device) | Electronic Musical Instruments | native | 18 | `https://wmdevices.com/pages/careers` |
| Korg | Electronic Musical Instruments | native | 17 | `https://career.korg.com/` |
| Bastl Instruments | Electronic Musical Instruments | native | 3 | `https://bastl-instruments.com/careers` |
| Pandorabots | Voice & Speech Technology | native | 19 | `https://www.pandorabots.com/careers/` |
| Respeecher | Voice & Speech Technology | native | 19 | `https://www.respeecher.com/careers` |
| Murf AI | Voice & Speech Technology | native | 18 | `https://murf.ai/ai-voice-agent/ai-recruiter` |
| ReadSpeaker | Voice & Speech Technology | native | 18 | `https://www.readspeaker.com/careers/` |
| Baidu (DuerOS) | Voice & Speech Technology | native | 12 | `https://talent.baidu.com/en/` |
| ElevenLabs | Voice & Speech Technology | native | 6 | `https://elevenlabs.io/careers` |
| Cisco Webex | Voice & Speech Technology | native | 2 | `https://careers.cisco.com/global/en` |
| Guitar Center | Audio Retailers & Distributors | partial | 18 | `https://www.guitarcenter.com/careers` |
| Takealot Audio | Audio Retailers & Distributors | partial | 18 | `https://www.takealot.com/careers` |
| SoundCam | Audio Testing & Measurement | native | 19 | `https://www.soundcam.com/en/careers` |
| Crystal Instruments | Audio Testing & Measurement | native | 18 | `https://www.crystalinstruments.com/careers` |
| DEWESoft | Audio Testing & Measurement | native | 6 | `https://dewesoft.com/careers` |
| Polytec | Audio Testing & Measurement | native | 3 | `https://www.polytec.com/en/career` |
| Keysight Technologies | Audio Testing & Measurement | native | 2 | `https://jobs.keysight.com/external/jobs` |
| Pico Interactive | Gaming, VR & Immersive Audio | native | 20 | `https://www.picoxr.com/global/careers` |
| Epic Games | Gaming, VR & Immersive Audio | native | 19 | `https://www.epicgames.com/site/careers` |
| Firaxis Games | Gaming, VR & Immersive Audio | native | 18 | `https://firaxis.com/careers/` |
| Tencent Games | Gaming, VR & Immersive Audio | native | 18 | `https://jobs.tencent.com/` |
| Embracer Group | Gaming, VR & Immersive Audio | native | 17 | `https://www.embracer.com/about/join-our-team/` |
| Smilegate | Gaming, VR & Immersive Audio | native | 17 | `https://careers.smilegate.com/` |
| Magic Leap | Gaming, VR & Immersive Audio | native | 6 | `https://resources.magicleap.cloud/careers` |
| Bethesda | Gaming, VR & Immersive Audio | native | 3 | `https://www.elderscrollsonline.com/en-us/joinus` |
| Bigscreen | Gaming, VR & Immersive Audio | native | 3 | `https://www.bigscreenvr.com/careers` |
| Resolution Games | Gaming, VR & Immersive Audio | native | 3 | `https://jobs.resolutiongames.com/` |
| Skydance Interactive | Gaming, VR & Immersive Audio | native | 3 | `https://skydance.com/careers/` |
| Bungie | Gaming, VR & Immersive Audio | native | 2 | `https://careers.bungie.com/` |
| Valve Corporation | Gaming, VR & Immersive Audio | native | 0 | `https://www.valvesoftware.com/en/` |
| Fishman Transducers | Professional Audio & Live Sound | native | 20 | `https://fishman.com/careers/` |
| Schoeps Mikrofone | Professional Audio & Live Sound | native | 20 | `https://schoeps.de/ueber-uns/jobs-praktika.html` |
| Dalet Digital Media | Professional Audio & Live Sound | native | 19 | `https://jobs.dalet.com/` |
| Deity Microphones | Professional Audio & Live Sound | native | 19 | `https://deitymic.com/careers/` |
| EAW | Professional Audio & Live Sound | native | 19 | `https://eaw.com/join-eaw-aes/` |
| Nagra | Professional Audio & Live Sound | native | 19 | `https://careers.nagra.com/` |
| Ashly Audio | Professional Audio & Live Sound | native | 18 | `https://ashly.com/careers/` |
| Boss Corporation | Professional Audio & Live Sound | native | 18 | `https://www.roland.com/us/company/careers/` |
| Danley Sound Labs | Professional Audio & Live Sound | native | 18 | `https://www.danleysoundlabs.com/careers/` |
| Kemper Amps | Professional Audio & Live Sound | native | 18 | `https://www.kemper-amps.com/jobs` |
| Tascam | Professional Audio & Live Sound | native | 18 | `https://www.tascam.com/us/careers` |
| Walrus Audio | Professional Audio & Live Sound | native | 18 | `https://www.walrusaudio.com/pages/careers` |
| DAS Audio | Professional Audio & Live Sound | native | 12 | `https://www.dasaudio.com/trabaja-con-nosotros/` |
| Two Rock Amplification | Professional Audio & Live Sound | native | 12 | `https://www.tworock.com/careers/` |
| RCS Sound Software | Professional Audio & Live Sound | native | 5 | `https://www.rcsworks.com/company/careers-at-rcs/` |
| Renkus-Heinz | Professional Audio & Live Sound | native | 5 | `https://www.renkus-heinz.com/careers` |
| Alcons Audio | Professional Audio & Live Sound | native | 3 | `https://www.alconsaudio.com/careers` |
| Calrec Audio | Professional Audio & Live Sound | native | 3 | `https://careers.calrec.com` |
| Lawo | Professional Audio & Live Sound | native | 3 | `https://lawo.com/company/career-at-lawo/` |
| Xilica | Professional Audio & Live Sound | native | 3 | `https://www.xilica.com/careers/` |
| Harmonic | Professional Audio & Live Sound | native | 2 | `https://careers.harmonicinc.com/` |
| Steg | Car Audio | native | 20 | `https://steg.com/site-and-buildings/talent/` |
| Aquatic AV | Car Audio | native | 19 | `https://www.aquaticav.com/pages/careers` |
| Dynaudio Automotive | Car Audio | native | 19 | `https://job.dynaudio.com/` |
| Hertz Car Audio | Car Audio | native | 19 | `https://www.hertzaudiovideo.com/en/careers` |
| Sundown Audio | Car Audio | native | 19 | `https://sundownaudio.com/pages/careers` |
| Meridian Audio Automotive | Car Audio | native | 18 | `https://www.meridian-audio.com/the-future-of-sound/work-with-meridian/` |
| JL Audio | Car Audio | native | 3 | `https://www.jlaudio.com/careers` |
| Stetsom | Car Audio | native | 3 | `https://jobs.quickin.io/stetsom?src=Pagina_de_Carreiras` |
| Audison | Car Audio | native | 1 | `https://elettromedia.com/careers` |
| McIntosh Automotive | Car Audio | native | 1 | `https://www.mcintoshlabs.com/home/about/employment` |
| Skar Audio | Car Audio | native | 1 | `https://www.skaraudio.com/jobs` |
| ESPN Audio | Recording Studios & Post Houses | native | 20 | `https://www.espn.com/careers` |
| DeWolfe Music | Recording Studios & Post Houses | native | 19 | `https://jobs.dewolfemusic.com/` |
| Extreme Music | Recording Studios & Post Houses | native | 19 | `https://www.extrememusic.com/talent/hans-zimmer` |
| Sunset Sound | Recording Studios & Post Houses | native | 19 | `https://www.sunsetsound.com/careers` |
| Artlist | Recording Studios & Post Houses | native | 18 | `https://artlist.io/careers` |
| KPM Music | Recording Studios & Post Houses | native | 18 | `https://jobs.kpmmusic.com/en/` |
| Netflix Post | Recording Studios & Post Houses | native | 18 | `https://www.netflix.com/NotFound?prev=https%3A%2F%2Fwww.netflix.com%2Fca` |
| NBCUniversal Audio | Recording Studios & Post Houses | native | 2 | `https://www.nbcuniversal.com/careers` |
| Flux Audio | Audio Plugins & Virtual Instruments | native | 20 | `https://www.flux.audio/2024/05/30/join-flux-at-infocomm-2024-in-las-vega` |
| Best Service | Audio Plugins & Virtual Instruments | native | 19 | `https://www.bestservice.com/careers` |
| ProjectSAM | Audio Plugins & Virtual Instruments | native | 19 | `https://jobs.projectsam.com/` |
| Vienna Symphonic Library | Audio Plugins & Virtual Instruments | native | 19 | `https://www.vsl.co.at/careers` |
| Audified | Audio Plugins & Virtual Instruments | native | 18 | `https://audified.com/careers/` |
| Gravity Audio | Audio Plugins & Virtual Instruments | native | 18 | `https://gravityaudio.net/careers` |
| Melda MAudioDynamics | Audio Plugins & Virtual Instruments | native | 18 | `https://www.meldaproduction.com/about/jobs` |
| Toontrack | Audio Plugins & Virtual Instruments | native | 18 | `https://www.toontrack.com/news/join-the-drumception-contest/` |
| MeldaProduction | Audio Plugins & Virtual Instruments | native | 1 | `https://www.meldaproduction.com/about/jobs` |
| SnoreLab | Audio Health & Wellness | native | 18 | `https://www.snorelab.com/careers` |
| Sound Oasis | Audio Health & Wellness | native | 18 | `https://www.soundoasis.com/careers` |
| Navistar (Traton) | Automotive OEMs | partial | 19 | `https://careers.navistar.com/` |
| Fisker | Automotive OEMs | partial | 18 | `https://www.fiskerinc.com/careers` |
| General Motors | Automotive OEMs | partial | 18 | `https://search-careers.gm.com/` |
| Mercedes-Benz | Automotive OEMs | partial | 18 | `https://jobs.mercedes-benz.com/enUS` |
| Kia | Automotive OEMs | partial | 3 | `https://www.kia.com/us/en/careers` |
| Lamborghini | Automotive OEMs | partial | 3 | `https://www.lamborghini.com/en-en/company/careers` |
| AGCO | Automotive OEMs | partial | 2 | `https://careers.agcocorp.com/` |
| BrightDrop (GM) | Automotive OEMs | partial | 2 | `https://www.gd.com/careers/` |
| CNH Industrial | Automotive OEMs | partial | 2 | `https://join.cnh.com/` |
| Musicnotes | Music Education Technology | partial | 17 | `https://www.musicnotes.com/careers` |
| TrueFire | Music Education Technology | partial | 4 | `https://truefire.com/careers` |
| Stanford CCRMA | Music Education Technology | partial | 3 | `https://careersearch.stanford.edu/` |
| Geneva Lab | Hi-Fi & Consumer Speakers | native | 20 | `https://www.genevalab.com/company/careers` |
| Peachtree Audio | Hi-Fi & Consumer Speakers | native | 20 | `https://www.peachtreeaudio.com/pages/carina-phase-2-trade-opportunity` |
| Pro-Ject Audio | Hi-Fi & Consumer Speakers | native | 20 | `https://www.project-audio.com/de/jobs/` |
| Quadral | Hi-Fi & Consumer Speakers | native | 20 | `https://jobs.quadral.com/` |
| Cabasse | Hi-Fi & Consumer Speakers | native | 19 | `https://www.cabasse.com/carriere/` |
| Canton | Hi-Fi & Consumer Speakers | native | 19 | `https://www.canton.de/unternehmen/karriere/` |
| Cary Audio | Hi-Fi & Consumer Speakers | native | 19 | `https://caryaudio.com/join-us-at-the-2015-rocky-mountain-audio-fest/` |
| Clearaudio | Hi-Fi & Consumer Speakers | native | 19 | `https://www.clearaudio.de/karriere/` |
| iFi Audio | Hi-Fi & Consumer Speakers | native | 19 | `https://ifi-audio.com/pages/job-board` |
| Manley Labs | Hi-Fi & Consumer Speakers | native | 19 | `https://www.manley.com/careers` |
| StormAudio | Hi-Fi & Consumer Speakers | native | 19 | `https://www.stormaudio.com/join-our-team/` |
| VPI Industries | Hi-Fi & Consumer Speakers | native | 19 | `https://www.vpiindustries.com/about/careers` |
| Esoteric | Hi-Fi & Consumer Speakers | native | 18 | `https://www.esoteric.com/careers` |
| Micromega | Hi-Fi & Consumer Speakers | native | 18 | `https://micromega.com/pages/notices-et-modes-demploi` |
| Mola Mola | Hi-Fi & Consumer Speakers | native | 18 | `http://www.molamola.be/en/careers` |
| MTX Audio | Hi-Fi & Consumer Speakers | native | 18 | `https://www.mitekusa.com/careers/` |
| NHT Loudspeakers | Hi-Fi & Consumer Speakers | native | 18 | `https://www.nhthifi.com/pages/careers` |
| Thorens | Hi-Fi & Consumer Speakers | native | 18 | `https://www.thorens.com/en/careers/` |
| VTL | Hi-Fi & Consumer Speakers | native | 18 | `https://www.vtl.com/careers` |
| MBL Radialstrahler | Hi-Fi & Consumer Speakers | native | 11 | `https://www.mbl.de/en/jobs` |
| Ortofon | Hi-Fi & Consumer Speakers | native | 10 | `https://www.ortofon.com/about-us/career` |
| Audiolab | Hi-Fi & Consumer Speakers | native | 3 | `https://iaggroup.com/jobs/current-vacancies/` |
| Roon Labs | Hi-Fi & Consumer Speakers | native | 3 | `https://roon.app/en/jobs` |
| Naim Audio | Hi-Fi & Consumer Speakers | native | 0 | `https://www.naimaudio.com/` |
| Ableton | DAW & Music Production Software | native | 20 | `https://www.ableton.com/en/jobs/` |
| Antares Audio Technologies | DAW & Music Production Software | native | 19 | `https://www.antarestech.com/careers` |
| Audius | DAW & Music Production Software | native | 19 | `https://audius.co/careers` |
| Slate Digital | DAW & Music Production Software | native | 19 | `https://slatedigital.com/careers/` |
| Audiomack | DAW & Music Production Software | native | 18 | `https://audiomack.com/careers` |
| Audiotool | DAW & Music Production Software | native | 18 | `https://www.audiotool.com/careers` |
| DaVinci Resolve Audio (Blackmagic) | DAW & Music Production Software | native | 17 | `https://www.blackmagicdesign.com/careers` |
| Splice | DAW & Music Production Software | native | 3 | `https://splice.com/careers` |
| AWAL (Sony) | Streaming & Music Services | partial | 20 | `https://www.awal.com/jobs` |
| Gaana (Times Internet) | Streaming & Music Services | partial | 20 | `https://gaana.com/music-label/sound-talent-media` |
| Genie Music | Streaming & Music Services | partial | 20 | `https://www.geniemusic.co.kr/people/recruit.do` |
| Libsyn | Streaming & Music Services | partial | 20 | `https://libsyn.com/careers/` |
| VK Music | Streaming & Music Services | partial | 20 | `https://vk.ru/careers` |
| Bandcamp | Streaming & Music Services | partial | 19 | `https://www.songtradr.com/careers` |
| Qobuz | Streaming & Music Services | partial | 19 | `https://www.qobuz.com/us-en/careers` |
| Songkick | Streaming & Music Services | partial | 19 | `https://www.songkick.com/jobs` |
| Last.fm (CBS) | Streaming & Music Services | partial | 18 | `https://www.last.fm/about/jobs` |
| Pandora (SiriusXM) | Streaming & Music Services | partial | 18 | `https://careers.siriusxm.com/careers/` |
| Resident Advisor | Streaming & Music Services | partial | 18 | `https://ra.co/about/jobs` |
| Ghostly International | Streaming & Music Services | partial | 12 | `https://ghostly.com/pages/careers` |
| Joox (Tencent) | Streaming & Music Services | partial | 12 | `https://careers.tencent.com/` |
| Napster (Rhapsody) | Streaming & Music Services | partial | 5 | `https://www.napster.com/careers` |
| LiveOne | Streaming & Music Services | partial | 3 | `https://www.liveone.com/careers.html` |
| Tracklib | Streaming & Music Services | partial | 3 | `https://careers.tracklib.com/` |
| Songtradr | Streaming & Music Services | partial | 1 | `https://www.songtradr.com/careers` |
| Alliance for Open Media | Audio IP & Licensing | partial | 21 | `https://aomedia.org/join/` |
| Algoriddim (djay) | DJ Equipment | native | 20 | `https://www.algoriddim.com/jobs` |
| Firelight Technologies (FMOD) | Audio Middleware & SDK | native | 20 | `https://www.fmod.com/careers` |
| PS Audio | Audio Accessories & Cables | native | 20 | `https://www.psaudio.com/pages/careers` |
| Serato | DJ Equipment | native | 20 | `https://serato.com/careers#current-openings` |
| SKB Cases | Audio Accessories & Cables | native | 20 | `https://www.skbcases.com/pages/careers` |
| Gator Cases | Audio Accessories & Cables | native | 19 | `https://gatorco.com/careers/` |
| Pelican Cases | Audio Accessories & Cables | native | 19 | `https://www.pelican.com/us/en/careers` |
| Audiokinetic (Wwise) | Audio Middleware & SDK | native | 18 | `https://www.audiokinetic.com/en/about/careers/` |
| B&C Speakers | Transducer & Driver Manufacturers | native | 18 | `https://www.bcspeakers.com/en/work-with-us` |
| BDI | Audio Accessories & Cables | native | 18 | `https://www.bdiusa.com/careers` |
| DJ.Studio | DJ Equipment | native | 18 | `https://dj.studio/careers` |
| Ecler | DJ Equipment | native | 18 | `https://www.ecler.com/why-ecler/work-with-us/` |
| Hercules DJ | DJ Equipment | native | 18 | `https://www.hercules.com/en-us/join-the-dj-affiliate-program-now/` |
| MPEG (ISO/IEC) | Audio IP & Licensing | partial | 18 | `https://www.mpeg.org/joint-jpeg-mpeg-workshop-on-radiance-fields/` |
| Tymphany | Transducer & Driver Manufacturers | native | 6 | `https://tymphany.com/JoinUs.html` |
| Volumio | Smart Home & IoT Audio | native | 5 | `https://volumio.com/careers/` |
| Canare | Audio Accessories & Cables | native | 3 | `https://www.canare.com/jobs` |

## Leave alone — the page says there are no openings (37)

These were fetched and their own text says they have no current vacancies, or they
only invite speculative applications. The scrape failing is **correct**. Do not
demote them and do not change their URLs.

- Baracoda — `https://baracoda.com/careers`
- Tempo Semiconductor — `https://temposemi.com/about/careers/`
- Metric Halo — `https://www.mhsoftware.com/using-connectdaily-5-0s-new-pooled-resource-f`
- Sequential — `https://sequential.com/about/careers/`
- Waldorf Music — `https://waldorfmusic.com/de/jobs/`
- Joué — `https://www.joueclub.fr/contenu/recrutement.html`
- Acapela Group — `https://www.acapela-group.com/voiceai-people-behind-technology-at-acapel`
- World Wide Stereo — `https://www.worldwidestereo.com/pages/careers`
- Audio Precision — `https://www.audioprecision.com/careers`
- Annapurna Interactive — `https://www.annapurna.com/jobs`
- Fast Travel Games — `https://www.fasttravelgames.com/career`
- AMS Neve — `https://www.ams-neve.com/careers/`
- Rupert Neve Designs — `https://rupertneve.com/careers`
- dB Technologies — `https://www.dbtechnologies.com/us/our-world/careers`
- Empress Effects — `https://empresseffects.com/pages/job-openings`
- Goodhertz — `https://goodhertz.com/jobs/`
- RCF — `https://www.rcf.it/en/work-with-us`
- DiGiGrid — `https://digigrid.net/recruitment`
- Fox Post Production — `https://www.fox.com/detail/series/SER273417EDMY/senate-hearing-developin`
- Cherry Audio — `https://cherryaudio.com/company/jobs`
- Spectrasonics — `https://www.spectrasonics.net/company/employment.php`
- Cycling '74 — `https://cycling74.com/careers`
- Orchestral Tools — `https://www.orchestraltools.com/company/careers`
- SPL (plugins) — `https://spl.audio/en/`
- Sound+ Sleep — `https://www.soundofsleep.com/jobs/`
- Energica Motor — `https://energicamotor.com/careers`
- Rega Research — `https://www.rega.co.uk/careers`
- DALI Speakers — `https://www.dali-speakers.com/en/about-dali/careers-at-dali/`
- Simaudio (Moon) — `https://simaudio.com/en/careers/`
- Acoustica Mixcraft — `https://acoustica.com/company/jobs`
- Waves Audio — `https://www.waves.com/careers`
- PRX — `https://www.prx.org/company/about/#jobs`
- Audioboom — `https://audioboom.com/about/jobs`
- Monstercat — `https://www.monstercat.com/careers`
- Reloop — `https://www.reloop.com/jobcenter`
- AudioQuest — `https://www.audioquest.com/pages/careers`
- Void Acoustics — `https://voidacoustics.com/careers/`

## Counts

- Tier 1 (candidate found): 9
- Tier 2 (needs a human, productive category): 36
- Tier 3 (needs a human, low-yield category): 76
- Tier 4 (not a URL problem): 195
- Leave alone (correctly has no openings): 37

