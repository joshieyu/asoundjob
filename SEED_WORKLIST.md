# Seed URL worklist

82 companies fail because the seeded careers URL is wrong, not because the
scraper cannot read the page. No scraper change fixes these.

YAP's audience is audio engineers, so this is ordered by which company
categories feed the hard-engineering job categories that are thinnest on the
board: audio_ee (12 jobs), audio_research (8), transducers (15),
acoustics_consulting (4) and nvh (2).

Professional Audio & Live Sound leads at 21 companies. Those firms - Calrec,
DiGiCo, QSC, Lab.gruppen, Peavey, Extron - hire DSP, audio systems and EE
engineers, so they feed the categories that matter here, not just live sound.
Consumer speaker and headphone makers follow because they are where transducer
and audio_ee roles live. Streaming, retail and education are last.

For each: find the real careers page, then edit careers_url in
data/audio_companies_final.json. If a company genuinely has no job board, set
verified: false instead - the loader now deactivates its stale rows.

## Professional Audio & Live Sound  (21)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Aston Microphones | aston-microphones | 404 / gone | https://www.astonmics.com/careers |
| Boss Corporation | boss-corporation | 404 / gone | https://www.roland.com/us/company/careers/ |
| Broadcast Electronics | broadcast-electronics | points at a product or shop page | https://www.bdcast.com/about/careers/ |
| Calrec Audio | calrec-audio | board is on another host; page links to it | https://calrec.com/careers/ |
| Danley Sound Labs | danley-sound-labs | 404 / gone | https://www.danleysoundlabs.com/careers/ |
| DiGiCo | digico | TLS or DNS failure | https://www.digico.tv/app.php/About-Us/careers |
| Extron Electronics | extron-electronics | TLS or DNS failure | https://www.extron.com/careers |
| FBT | fbt | points at a product or shop page | https://www.fbt.it/events/join-us-at-infocomm-2025-in-orlando/ |
| Fishman Transducers | fishman-transducers | points at a product or shop page | https://fishman.com/careers/ |
| Krotos Audio | krotos-audio | points at a product or shop page | https://www.krotosaudio.com/careers/ |
| Lab.gruppen | lab-gruppen | 404 / gone | https://www.labgruppen.com/careers |
| Peavey Electronics | peavey-electronics | points at a product or shop page | https://peavey.com/careers/ |
| QSC | qsc | board is on another host; page links to it | https://www.acuityinc.com/careers |
| RF Venue | rf-venue | points at a product or shop page | https://www.rfvenue.com/about#jobs |
| Supro | supro | 404 / gone | https://www.suprousa.com/careers/ |
| TC Electronic | tc-electronic | 404 / gone | https://www.musictribe.com/careers |
| TC Helicon | tc-helicon | 404 / gone | https://www.musictribe.com/careers |
| Turbosound | turbosound | 404 / gone | https://www.musictribe.com/careers |
| Walrus Audio | walrus-audio | points at a product or shop page | https://www.walrusaudio.com/pages/careers |
| Wisycom | wisycom | points at a product or shop page | https://wisycom.com/products/careers/ |
| Xilica | xilica | board is on another host; page links to it | https://www.xilica.com/careers/ |

## Acoustic Consulting & Engineering  (4)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Auralex Acoustics | auralex-acoustics | points at a product or shop page | https://auralex.com/careers/ |
| Kinetics Noise Control | kinetics-noise-control | board is on another host; page links to it | https://kineticsnoise.com/resources/careers |
| Talaske Acoustics | talaske-acoustics | 404 / gone | https://www.talaske.com/careers |
| WSDG (Walters-Storyk Design Group) | wsdg-walters-storyk-design-group | points at a product or shop page | https://wsdg.com/careers/ |

## Audio Testing & Measurement  (1)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| data physics | data-physics | board is on another host; page links to it | https://dataphysics.com/resources/careers/ |

## Automotive OEMs  (4)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| GAC Group | gac-group | TLS or DNS failure | https://www.gac-motor.com/en/careers |
| General Motors | general-motors | board is on another host; page links to it | https://search-careers.gm.com/ |
| Mercedes-Benz | mercedes-benz | board is on another host; page links to it | https://jobs.mercedes-benz.com/enUS |
| Volvo Trucks | volvo-trucks | board is on another host; page links to it | https://www.volvotrucks.com/en-en/about-us/who-we-are/career.html |

## Hi-Fi & Consumer Speakers  (8)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Cabasse | cabasse | points at a product or shop page | https://www.cabasse.com/carriere/ |
| Micromega | micromega | points at a product or shop page | https://micromega.com/pages/notices-et-modes-demploi |
| Peachtree Audio | peachtree-audio | points at a product or shop page | https://www.peachtreeaudio.com/pages/carina-phase-2-trade-opportun |
| Pro-Ject Audio | pro-ject-audio | points at a product or shop page | https://www.project-audio.com/de/jobs/ |
| Simaudio (Moon) | simaudio-moon | points at a product or shop page | https://simaudio.com/en/careers/ |
| Tannoy | tannoy | 404 / gone | https://www.musictribe.com/careers |
| Thorens | thorens | 404 / gone | https://www.thorens.com/en/careers/ |
| Triangle Loudspeakers | triangle-loudspeakers | points at a product or shop page | https://trianglehifi.us/ |

## Headphones & Personal Audio  (6)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Audeze | audeze | 404 / gone | https://www.audeze.com/pages/careers |
| Audio-Technica | audio-technica | board is on another host; page links to it | https://www.audio-technica.com/en-us/careers |
| Hidizs | hidizs | points at a product or shop page | https://www.hidizs.net/pages/influencer-recruit |
| Master & Dynamic | master-dynamic | points at a product or shop page | https://www.masterdynamic.com/pages/halliburton-opportunity |
| Shanling | shanling | 404 / gone | https://www.shenzhenaudio.com/pages/careers |
| Shokz | shokz | points at a product or shop page | https://shokz.com/pages/careers |

## Car Audio  (1)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Sundown Audio | sundown-audio | points at a product or shop page | https://sundownaudio.com/pages/careers |

## Audio Accessories & Cables  (4)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Anker Cables | anker-cables | 404 / gone | https://www.anker.com/careers |
| Gator Cases | gator-cases | points at a product or shop page | https://gatorco.com/careers/ |
| PS Audio | ps-audio | points at a product or shop page | https://www.psaudio.com/pages/careers |
| SKB Cases | skb-cases | points at a product or shop page | https://www.skbcases.com/pages/careers |

## Audio Plugins & Virtual Instruments  (5)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Arturia | arturia | board is on another host; page links to it | https://jobs.arturia.com/ |
| Audified | audified | points at a product or shop page | https://audified.com/careers/ |
| Equator Sound | equator-sound | TLS or DNS failure | https://www.equatorsound.com/lander |
| Flux Audio | flux-audio | points at a product or shop page | https://www.flux.audio/2024/05/30/join-flux-at-infocomm-2024-in-la |
| Spitfire Audio | spitfire-audio | board is on another host; page links to it | https://www.spitfireaudio.com/en-us/pages/careers |

## DAW & Music Production Software  (3)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Audiotool | audiotool | 404 / gone | https://www.audiotool.com/careers |
| DaVinci Resolve Audio (Blackmagic) | davinci-resolve-audio-blackmagic | 404 / gone | https://www.blackmagicdesign.com/careers |
| Native Instruments | native-instruments | points at a product or shop page | https://www.native-instruments.com/pages/careers |

## Voice & Speech Technology  (3)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| ReadSpeaker | readspeaker | board is on another host; page links to it | https://www.readspeaker.com/careers/ |
| Respeecher | respeecher | board is on another host; page links to it | https://www.respeecher.com/careers |
| Spitch | spitch | board is on another host; page links to it | https://spitch.ai/de/ |

## Electronic Musical Instruments  (4)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Expressive E | expressive-e | board is on another host; page links to it | https://www.expressivee.com/category/3-careers |
| Kurzweil Music Systems | kurzweil-music-systems | 404 / gone | https://kurzweil.com/careers/ |
| Sequential | sequential | points at a product or shop page | https://sequential.com/about/careers/ |
| Waldorf Music | waldorf-music | points at a product or shop page | https://waldorfmusic.com/de/jobs/ |

## Gaming, VR & Immersive Audio  (2)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Embracer Group | embracer-group | board is on another host; page links to it | https://www.embracer.com/about/join-our-team/ |
| Take-Two Interactive | take-two-interactive | TLS or DNS failure | https://careers.take2games.com/jobs |

## AI/ML Audio  (1)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Tortoise TTS | tortoise-tts | points at a product or shop page | https://worldturtleday.org/join-the-movement/ |

## Audio Health & Wellness  (3)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| SleepPhones | sleepphones | 404 / gone | https://www.sleepphones.com/careers |
| Sound Sleep | sound-sleep | points at a product or shop page | https://soundsleep.com/careers/ |
| Sound+ Sleep | sound-sleep-2 | points at a product or shop page | https://www.soundofsleep.com/jobs/ |

## Audio IP & Licensing  (1)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| AES (Audio Engineering Society) | aes-audio-engineering-society | board is on another host; page links to it | https://aes.careerwebsite.com/home/index.cfm/ |

## Audio Retailers & Distributors  (1)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Guitar Center | guitar-center | board is on another host; page links to it | https://www.guitarcenter.com/careers |

## Consumer Electronics & Tech  (1)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Audio Precision | audio-precision | board is on another host; page links to it | https://www.ap.com/careers |

## DJ Equipment  (1)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| DJ.Studio | dj-studio | 404 / gone | https://dj.studio/careers |

## Hearing Aid & Hearing Tech  (1)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| Olive Union | olive-union | 404 / gone | https://www.oliveunion.com/pages/careers |

## Music Education Technology  (1)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| University of York Audio Lab | university-of-york-audio-lab | 404 / gone | https://www.york.ac.uk/study/work/ |

## Recording Studios & Post Houses  (2)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| ESPN Audio | espn-audio | 404 / gone | https://www.espn.com/careers |
| KPM Music | kpm-music | points at a product or shop page | https://jobs.kpmmusic.com/en/ |

## Streaming & Music Services  (4)

| Company | slug | Why it fails | Seeded URL |
|---|---|---|---|
| AWAL (Sony) | awal-sony | 404 / gone | https://www.awal.com/jobs |
| Dice FM | dice-fm | board is on another host; page links to it | https://boards.eu.greenhouse.io/dicefm-careers |
| PRX | prx | board is on another host; page links to it | https://www.prx.org/company/about/#jobs |
| TuneCore | tunecore | board is on another host; page links to it | https://www.tunecore.com/careers |

