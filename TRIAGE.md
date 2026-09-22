# Careers-URL triage

Rebuilt 2026-09-22 from the database as it stood after that day's cycle. **This
replaces the version of the same day, which was wrong in four ways**: its Tier 0
listed companies whose scrape had succeeded (DiGiCo is healthy with board jobs),
its Tier 4 listed healthy companies (Valve, Naim Audio), it listed companies you
had already checked by hand, and it mixed data from two different days.

Read-only: producing this wrote nothing to the database or the seed.

## What is left out, and why

- **133 companies that work** — their last scrape succeeded and they have
  jobs on the board. None of them appear below, whatever their URL looks like.
- Companies whose scrape succeeds on a real-looking careers page and simply has no
  audio jobs (`idle`, `thin`). That is a question about the company, not the URL.
- Companies you marked `source: manual` appear **only** in section B.

## How to read the order

Within each section: native-scope companies first, then by **category yield** —
the share of a category's companies that reach the board times the median rows of
those that do (Headphones & Personal Audio 26% x 15; Audio Accessories & Cables
0 of 25) — then by how long it has been failing. Category yield is a tiebreaker:
it measures what works today, which is partly an accident of which URLs are right.

One measured caution before spending time here: of ten replacement URLs checked
with `check_url`, all ten parsed jobs and **eight yielded no audio job at all**;
Nintendo and PACCAR yielded four between them. A wrong URL is real, and fixing it
often adds nothing to the board. Favour the top of each section.

Check any replacement before saving it:
`python -m scraper.check_url <url> --name "<company>"`

## A. The careers URL is dead (16)

Highest confidence. The company's last scrape failed, and a request to **the seeded
careers URL itself** returned 404/410 or could not connect — not an ATS guess, not
a later page. Taken from the 2026-09-22 cycle log. From the next cycle these
errors are stored in the database and shown in the admin panel directly.

| company | category | scope | status | error | seeded careers URL | found by discovery |
| --- | --- | --- | --- | --- | --- | --- |
| Olive Union | Hearing Aid & Hearing Tech | native | failed 19x | HTTP 404 | `https://www.oliveunion.com/pages/careers` |  |
| Audeze | Headphones & Personal Audio | native | failed 19x | HTTP 404 | `https://www.audeze.com/pages/careers` |  |
| Shanling | Headphones & Personal Audio | native | failed 19x | HTTP 404 | `https://www.shenzhenaudio.com/pages/careers` |  |
| Talaske Acoustics | Acoustic Consulting & Engineering | native | failed 19x | HTTP 404 | `https://www.talaske.com/careers` |  |
| Boss Corporation | Professional Audio & Live Sound | native | failed 19x | HTTP 404 | `https://www.roland.com/us/company/careers/` |  |
| Danley Sound Labs | Professional Audio & Live Sound | native | failed 19x | HTTP 404 | `https://www.danleysoundlabs.com/careers/` |  |
| Flik | Recording Studios & Post Houses | native | failed 13x | HTTP 404 | `https://www.flik.com/404-page-not-found/` |  |
| Thorens | Hi-Fi & Consumer Speakers | native | failed 19x | HTTP 404 | `https://www.thorens.com/en/careers/` |  |
| Ortofon | Hi-Fi & Consumer Speakers | native | failed 11x | HTTP 404 | `https://www.ortofon.com/about-us/career` |  |
| Audiotool | DAW & Music Production Software | native | failed 19x | HTTP 404 | `https://www.audiotool.com/careers` |  |
| DaVinci Resolve Audio (Blackmagic) | DAW & Music Production Software | native | failed 18x | HTTP 404 | `https://www.blackmagicdesign.com/careers` |  |
| DJ.Studio | DJ Equipment | native | failed 19x | HTTP 404 | `https://dj.studio/careers` |  |
| GAC Group | Automotive OEMs | partial | failed 18x | SSLError | `https://www.gac-motor.com/en/careers` |  |
| University of York Audio Lab | Music Education Technology | partial | failed 19x | HTTP 404 | `https://www.york.ac.uk/study/work/` |  |
| TrueFire | Music Education Technology | partial | failed 5x | HTTP 404 | `https://truefire.com/careers` |  |
| AWAL (Sony) | Streaming & Music Services | partial | failed 21x | HTTP 404 | `https://www.awal.com/jobs` |  |

## B. You already checked these by hand, and they still fail (5)

These carry `source: manual`, so a human chose the URL. They are here because the
scrape still fails, which usually means the site changed after you checked it or
the page needs a parser we do not have. Worth a look before anything else you
have already signed off.

| company | category | scope | status | error | seeded careers URL | found by discovery |
| --- | --- | --- | --- | --- | --- | --- |
| DiGiGrid | Professional Audio & Live Sound | native | failed 7x |  | `https://digigrid.net/recruitment` |  |
| Keysight Technologies | Audio Testing & Measurement | native | failed 3x |  | `https://jobs.keysight.com/external/jobs` |  |
| McIntosh Automotive | Car Audio | native | failed 2x |  | `https://www.mcintoshlabs.com/home/about/employment` |  |
| Tymphany | Transducer & Driver Manufacturers | native | failed 7x |  | `https://tymphany.com/JoinUs.html` |  |
| Rivian | Automotive OEMs | partial | failed 4x | HTTP 404 | `https://rivian.com/careers-home/` | `https://rivian.com/careers` (checked: 2 jobs, **0 audio**) |

## C. Not a careers page, and the scrape fails (102)

The seeded URL is a homepage, about page, product page or similar — judged from
the URL alone — and the last scrape failed. Needs a human to find the real board.

| company | category | scope | status | seeded careers URL | found by discovery |
| --- | --- | --- | --- | --- | --- |
| Inventis | Hearing Aid & Hearing Tech | native | failed 21x | `https://inventis.it/it-it/soluzioni/medicina-del-lavoro` |  |
| Decibels | Hearing Aid & Hearing Tech | native | failed 20x | `https://www.domaineasy.com/buy-domain/www.decibels.com` |  |
| Eargo | Hearing Aid & Hearing Tech | native | failed 19x | `https://www.eargo.com/` |  |
| EarQ | Hearing Aid & Hearing Tech | native | failed 13x | `https://www.cq-partners.com/what-we-do/business-planning/training-development/` |  |
| Embrace Hearing | Hearing Aid & Hearing Tech | native | failed 13x | `https://embracehearing.com/user-guides` |  |
| Lexie Hearing | Hearing Aid & Hearing Tech | native | failed 13x | `https://www.lexiehearing.com/us` |  |
| WS Audiology (Signia/Widex) | Hearing Aid & Hearing Tech | native | failed 4x | `https://www.wsa.com/` |  |
| Jaybird | Headphones & Personal Audio | native | failed 13x | `https://support.logi.com/hc/en-us` |  |
| Plantronics | Headphones & Personal Audio | native | failed 13x | `https://www.hp.com/us-en/poly.html` |  |
| Raal Requisite | Headphones & Personal Audio | native | failed 13x | `https://requisiteaudio.com/` |  |
| Shozy | Headphones & Personal Audio | native | failed 13x | `https://www.shozyaudio.com/password` |  |
| Turtle Beach | Headphones & Personal Audio | native | failed 13x | `https://www.turtlebeach.com/pages/influencers` |  |
| JLab Audio | Headphones & Personal Audio | native | failed 4x | `https://www.jlab.com/products/epic-keyboard-mouse-bundle` |  |
| Akustiks | Acoustic Consulting & Engineering | native | failed 13x | `https://akustiks.com/` |  |
| Hush Acoustics | Acoustic Consulting & Engineering | native | failed 13x | `https://www.hushacoustics.co.uk/technical-resources/environmental/` |  |
| Threshold Acoustics | Acoustic Consulting & Engineering | native | failed 13x | `https://threshold.llc/team` |  |
| AIVA | AI/ML Audio | native | failed 25x | `https://www.aiva.ai/` |  |
| Hit'n'Mix | AI/ML Audio | native | failed 13x | `https://hitnmix.com` |  |
| Echo Digital Audio | Audio Interfaces & Converters | native | failed 13x | `http://www.echoaudio.com/about/` |  |
| Spitch | Voice & Speech Technology | native | failed 20x | `https://spitch.ai/de/` |  |
| Voiceflow | Voice & Speech Technology | native | failed 20x | `https://www.voiceflow.com/about#careers` |  |
| Voiser | Voice & Speech Technology | native | failed 19x | `https://www.voiser.net/` |  |
| SoapBox Labs | Voice & Speech Technology | native | failed 4x | `https://www.curriculumassociates.com/about/ailabs` |  |
| Qu-Bit Electronix | Electronic Musical Instruments | native | failed 13x | `https://www.qubitelectronix.com/team` |  |
| Roland | Electronic Musical Instruments | native | failed 13x | `https://www.youtube.com/watch?v=jaO0LffIs1A` |  |
| Soma Laboratory | Electronic Musical Instruments | native | failed 13x | `https://somasynths.com/team/` |  |
| RF Venue | Professional Audio & Live Sound | native | failed 20x | `https://www.rfvenue.com/about#jobs` |  |
| Audio Ltd | Professional Audio & Live Sound | native | failed 19x | `https://www.sounddevices.com/` |  |
| Line 6 | Professional Audio & Live Sound | native | failed 19x | `https://yamahaguitargroup.com/company/#careers` |  |
| Wheatstone | Professional Audio & Live Sound | native | failed 19x | `https://wheatstone.com/contact-us/` |  |
| Electro-Voice | Professional Audio & Live Sound | native | failed 14x | `https://ev.com:443/new-cars` |  |
| Fulcrum Acoustic | Professional Audio & Live Sound | native | failed 13x | `https://www.fulcrum-acoustic.com/projects/benson-center-for-arts-and-learning` |  |
| McCauley Sound | Professional Audio & Live Sound | native | failed 13x | `https://www.mccauleysound.com/` |  |
| Two Notes Audio | Professional Audio & Live Sound | native | failed 13x | `http://twonotes.com/` |  |
| Digigram | Professional Audio & Live Sound | native | failed 4x | `https://www.digigram.com/` |  |
| Fractal Audio Systems | Professional Audio & Live Sound | native | failed 4x | `https://www.fractalaudio.com/p-fx8-multieffects-pedalboard/` |  |
| Mackie DL | Professional Audio & Live Sound | native | failed 4x | `https://mackie.com/` |  |
| Actran (MSC Software) | Audio Testing & Measurement | native | failed 22x | `https://hexagon.com/company/newsroom/press-releases/2025/hexagon-agrees-sale-of-` |  |
| SOUNDFlow | Audio Testing & Measurement | native | failed 21x | `https://voxxintl.zendesk.com/hc/en-us` |  |
| OmniMic | Audio Testing & Measurement | native | failed 19x | `https://www.omnimic.com/lander` |  |
| Free Field Technologies | Audio Testing & Measurement | native | failed 1x | `https://hexagon.com/company/newsroom/press-releases/2025/hexagon-agrees-sale-of-` |  |
| Immersive Audio | Gaming, VR & Immersive Audio | native | failed 20x | `https://www.immersiveaudio.com/lander` |  |
| Deep Silver | Gaming, VR & Immersive Audio | native | failed 13x | `https://www.animefactory.it/` |  |
| NCSoft | Gaming, VR & Immersive Audio | native | failed 13x | `https://www.nc.com/` |  |
| Larian Studios | Gaming, VR & Immersive Audio | native | failed 4x | `https://eu.merch.larian.com/products/divinity-original-sin-the-boardgame` |  |
| Nexon | Gaming, VR & Immersive Audio | native | failed 4x | `https://www.nexon.com/main/en/error?aspxerrorpath=%2Fen%2Fcareers` |  |
| Spatial | Gaming, VR & Immersive Audio | native | failed 4x | `https://www.spatial.io/team` |  |
| Dear Reality | Gaming, VR & Immersive Audio | native | failed 3x | `https://www.sennheiser.com/en-us/immersive/dear-reality` |  |
| GungHo Online | Gaming, VR & Immersive Audio | native | failed 3x | `https://www.gungho.com/investments/#opportunities` |  |
| Blaupunkt | Car Audio | native | failed 13x | `https://www.blaupunkt.com/en-us/` |  |
| Rock Heritage | Recording Studios & Post Houses | native | failed 20x | `https://www.rockheritage.com/lander` |  |
| Rumblefish | Recording Studios & Post Houses | native | failed 13x | `https://www.rumblefish.com/team/` |  |
| Universal Production Music | Recording Studios & Post Houses | native | failed 13x | `https://www.universalproductionmusic.com:443/en-us` |  |
| Musicbed | Recording Studios & Post Houses | native | failed 4x | `https://www.musicbed.com/` |  |
| Equator Sound | Audio Plugins & Virtual Instruments | native | failed 20x | `https://www.equatorsound.com/lander` |  |
| Dehumaniser | Audio Plugins & Virtual Instruments | native | failed 13x | `https://afdam.com/` |  |
| Devicemarket | Audio Plugins & Virtual Instruments | native | failed 13x | `https://devicemarket.com/` |  |
| EastWest Sounds | Audio Plugins & Virtual Instruments | native | failed 13x | `https://www.soundsonline.com/` |  |
| Hearing Health Foundation | Audio Health & Wellness | native | failed 13x | `https://hearinghealthfoundation.org/help` |  |
| QuietOn | Audio Health & Wellness | native | failed 13x | `https://quieton.com` |  |
| dCS | Hi-Fi & Consumer Speakers | native | failed 19x | `https://dcsaudio.com/` |  |
| Triangle Loudspeakers | Hi-Fi & Consumer Speakers | native | failed 19x | `https://trianglehifi.us/` |  |
| Davis Acoustics | Hi-Fi & Consumer Speakers | native | failed 13x | `https://davis-acoustics.com/en/teamnv/` |  |
| Harbeth Audio | Hi-Fi & Consumer Speakers | native | failed 13x | `https://harbeth.co.uk/` |  |
| Heco Audio | Hi-Fi & Consumer Speakers | native | failed 13x | `https://heco-audio.de/Ambient-Line/` |  |
| Hegel Music Systems | Hi-Fi & Consumer Speakers | native | failed 13x | `https://www.hegel.com/en/` |  |
| SVS | Hi-Fi & Consumer Speakers | native | failed 13x | `https://www.svsound.com/pages/about-us` |  |
| System Audio | Hi-Fi & Consumer Speakers | native | failed 13x | `https://www.system-audio.com/product-category/active-wireless-speakers/` |  |
| KEF | Hi-Fi & Consumer Speakers | native | failed 4x | `https://us.kef.com/` |  |
| BeatMaker (Intua) | DAW & Music Production Software | native | failed 13x | `https://intua.net/` |  |
| Endlesss | DAW & Music Production Software | native | failed 13x | `https://endlesss.fm/` |  |
| McDSP | DAW & Music Production Software | native | failed 13x | `https://mcdsp.com/` |  |
| Magix (Samplitude/Sequoia) | DAW & Music Production Software | native | failed 4x | `https://www.magix.com/us/` |  |
| Beyma | Transducer & Driver Manufacturers | native | failed 19x | `https://www.beyma.com/en/home/` |  |
| Omnimount | Audio Accessories & Cables | native | failed 19x | `https://www.ergotron.com/omnimount` |  |
| Funktion-One | DJ Equipment | native | failed 13x | `https://funktion-one.com/about/` |  |
| Klotz | Audio Accessories & Cables | native | failed 13x | `https://www.klotz-ais.com/` |  |
| Virtual DJ (Atomix) | DJ Equipment | native | failed 13x | `https://virtualdj.com/atomixproductions/` |  |
| Middle Atlantic | Audio Accessories & Cables | native | failed 4x | `https://www.legrandav.com/products/middle_atlantic_products` |  |
| Radial Engineering | Audio Accessories & Cables | native | failed 4x | `https://www.radialeng.com/keyboard` |  |
| Ultimate Support | Audio Accessories & Cables | native | failed 4x | `https://www.ultimatesupport.com/collections/guitar-stands-pedalboards-accessorie` |  |
| Cadence Design Systems | Consumer Electronics & Tech | partial | failed 20x | `https://www.cadence.com/en_US/home/errors/accessdenied.html` |  |
| Creative Technology | Consumer Electronics & Tech | partial | failed 13x | `https://us.creative.com:443/` |  |
| Honor | Consumer Electronics & Tech | partial | failed 13x | `https://www.honor.com/global/404/` |  |
| ZTE | Consumer Electronics & Tech | partial | failed 13x | `https://www.zte.com.cn/china/404.html` |  |
| CEVA | Consumer Electronics & Tech | partial | failed 4x | `https://www.ceva-ip.com/` |  |
| Fairphone | Consumer Electronics & Tech | partial | failed 4x; 1 old board rows kept | `https://www.fairphone.com/team` |  |
| Fujitsu | Consumer Electronics & Tech | partial | failed 3x | `https://global.fujitsu/en-global` |  |
| Vintage King Audio | Audio Retailers & Distributors | partial | failed 13x | `https://vintageking.com/recording/studio-furniture/19-outboard-racks` |  |
| Hyundai Motor | Automotive OEMs | partial | failed 13x | `https://www.hyundai.com/worldwide/en` |  |
| Volkswagen | Automotive OEMs | partial | failed 13x | `https://www.volkswagen.de/de.html` | `https://www.volkswagen-karriere.de/de.html` (checked: 12 jobs, **0 audio**) |
| Kawasaki Motors | Automotive OEMs | partial | failed 3x | `https://www.kawasaki.com/en-us/` |  |
| EarMaster | Music Education Technology | partial | failed 20x | `https://www.earmaster.com/company/work-at-earmaster.html` |  |
| Groove3 | Music Education Technology | partial | failed 13x | `https://www.groove3.com/` |  |
| Puremix | Music Education Technology | partial | failed 13x | `https://www.puremix.com/` |  |
| Stem | Streaming & Music Services | partial | failed 21x | `https://stem.is/` |  |
| Ditto Music | Streaming & Music Services | partial | failed 20x | `https://login.dittomusic.com/en/` |  |
| Bandsintown | Streaming & Music Services | partial | failed 19x | `https://www.bandsintown.com/a/7488894` |  |
| Deezer | Streaming & Music Services | partial | failed 13x | `https://www.deezer-investors.com/` |  |
| Luminary | Streaming & Music Services | partial | failed 13x | `https://luminarypodcasts.com/?country=US` |  |
| Sounds.com | Streaming & Music Services | partial | failed 4x | `https://www.native-instruments.com:443/` |  |
| TuneIn | Streaming & Music Services | partial | failed 4x | `https://tunein.com/` | `https://tunein.com/careers` (checked: 1 jobs, **0 audio**) |

## D. Not a careers page, and the scrape runs on the wrong page (11)

The scrape "succeeds" but it is reading a homepage or similar, so it stores
navigation or non-audio rows and puts nothing on the board.

| company | category | scope | status | seeded careers URL |
| --- | --- | --- | --- | --- |
| Nuheara | Hearing Aid & Hearing Tech | native | scrapes, grade idle | `https://www.nuheara.com/team-behind-the-tech/` |
| Poly (HP) | Headphones & Personal Audio | native | scrapes, grade silent | `https://www.hp.com/us-en/poly.html` |
| Evertz Microsystems | Professional Audio & Live Sound | native | scrapes, grade idle | `https://evertz.com/` |
| Zaxcom | Professional Audio & Live Sound | native | scrapes, grade idle | `https://zaxcom.com/ibc-2026/` |
| LMS (Siemens) | Audio Testing & Measurement | native | scrapes, grade idle | `https://www.siemens.com/en-us/` |
| Ubisoft | Gaming, VR & Immersive Audio | native | scrapes, grade idle | `https://www.ubisoft.com/en-us/company/404` |
| The Music Bed | Recording Studios & Post Houses | native | scrapes, grade silent | `https://www.musicbed.com/` |
| Sanus | Audio Accessories & Cables | native | scrapes, grade idle | `https://www.sanus.com/en_US/` |
| Musician's Friend | Audio Retailers & Distributors | partial | scrapes, grade idle | `https://www.musiciansfriend.com/pages/ways-to-pay` |
| JamPlay | Music Education Technology | partial | scrapes, grade idle | `https://jamplay.com:443/` |
| NYU Music Technology | Music Education Technology | partial | scrapes, grade idle | `https://www.nyu.edu/about/university-initiatives/nyu-irl.html` |

## E. Careers-looking URL that stores navigation instead of jobs (45)

Graded `furniture`: rows arrive, but they are menu items and section links. Usually
a landing page *about* careers, one click away from the actual list of openings.

| company | category | scope | status | seeded careers URL |
| --- | --- | --- | --- | --- |
| Amplifon | Hearing Aid & Hearing Tech | native | scrapes, grade furniture | `https://careers.amplifon.com/en/sites/CX_1` |
| HearingLife | Hearing Aid & Hearing Tech | native | scrapes, grade furniture | `https://www.hearinglife.com/careers` |
| MED-EL | Hearing Aid & Hearing Tech | native | scrapes, grade furniture | `https://jobs.medel.com/?utm_source=medelcom&utm_medium=website` |
| Astro Gaming | Headphones & Personal Audio | native | scrapes, grade furniture | `https://jobs.hp.com/` |
| LucidSound | Headphones & Personal Audio | native | scrapes, grade furniture | `https://www.accobrands.com/careers/` |
| Bilfinger Acoustics | Acoustic Consulting & Engineering | native | scrapes, grade furniture | `https://www.bilfinger.com/en/careers/` |
| HOK | Acoustic Consulting & Engineering | native | scrapes, grade furniture | `https://www.hok.com/people/careers/` |
| Sweco | Acoustic Consulting & Engineering | native | scrapes, grade furniture | `https://www.swecogroup.com/careers/` |
| Avaya | Voice & Speech Technology | native | scrapes, grade furniture | `https://careers.avaya.com/` |
| Cisco Webex | Voice & Speech Technology | native | scrapes, grade furniture | `https://careers.cisco.com/global/en` |
| Aiphone | Professional Audio & Live Sound | native | scrapes, grade furniture | `https://www.aiphone.com/careers/` |
| Crestron Electronics | Professional Audio & Live Sound | native | scrapes, grade furniture | `https://careers.crestron.com/` |
| ANSYS (Acoustics) | Audio Testing & Measurement | native | scrapes, grade furniture | `https://ansys.synopsys.com/careers` |
| National Instruments | Audio Testing & Measurement | native | scrapes, grade furniture | `https://www.emerson.com/en/corporate/careers` |
| Siemens Digital Industries | Audio Testing & Measurement | native | scrapes, grade furniture | `https://jobs.siemens.com/en_US/externaljobs` |
| Ninja Theory | Gaming, VR & Immersive Audio | native | scrapes, grade furniture | `https://www.ninjatheory.com/careers/opportunities` |
| Rockstar Games | Gaming, VR & Immersive Audio | native | scrapes, grade furniture | `https://www.rockstargames.com/careers` |
| Two Big Ears | Gaming, VR & Immersive Audio | native | scrapes, grade furniture | `https://www.metacareers.com/` |
| Varjo | Gaming, VR & Immersive Audio | native | scrapes, grade furniture | `https://varjo.com/jobs` |
| Continental Automotive | Car Audio | native | scrapes, grade furniture | `https://www.aumovio.com/en/career.html` |
| JVC | Car Audio | native | scrapes, grade furniture | `https://www.jvckenwood.com/jp/recruit/career/` |
| SleepPhones | Audio Health & Wellness | native | scrapes, grade furniture | `https://www.sleepphones.com/careers` |
| Steinberg | DAW & Music Production Software | native | scrapes, grade furniture | `https://www.steinberg.net/careers/` |
| Anker Cables | Audio Accessories & Cables | native | scrapes, grade furniture | `https://www.anker.com/careers` |
| Furman Power | Audio Accessories & Cables | native | scrapes, grade furniture | `https://www.tucows.com/careers/overview` |
| Motorola Mobility | Consumer Electronics & Tech | partial | scrapes, grade furniture | `https://jobs.lenovo.com/en_US/careers` |
| NEC | Consumer Electronics & Tech | partial | scrapes, grade furniture | `https://careers.nec.com/` |
| NVIDIA | Consumer Electronics & Tech | partial | scrapes, grade furniture | `https://www.nvidia.com/en-us/about-nvidia/careers/` |
| ON Semiconductor | Consumer Electronics & Tech | partial | scrapes, grade furniture | `https://www.onsemi.com/careers` |
| Synopsys | Consumer Electronics & Tech | partial | scrapes, grade furniture | `https://careers.synopsys.com/` |
| Texas Instruments | Consumer Electronics & Tech | partial | scrapes, grade furniture | `https://careers.ti.com/en/sites/CX` |
| Daimler Truck | Automotive OEMs | partial | scrapes, grade furniture | `https://www.daimlertruck.com/en/career` |
| Jaguar Land Rover | Automotive OEMs | partial | scrapes, grade furniture | `https://careers.jaguarlandrover.com/` |
| John Deere | Automotive OEMs | partial | scrapes, grade furniture | `https://jobs.deere.com/` |
| Lucid Motors | Automotive OEMs | partial | scrapes, grade furniture | `https://lucidmotors.com/careers` |
| Mazda | Automotive OEMs | partial | scrapes, grade furniture | `https://www.mazda.com/ja/careers/` |
| NIO | Automotive OEMs | partial | scrapes, grade furniture | `https://www.nio.com/careers` |
| Stellantis | Automotive OEMs | partial | scrapes, grade furniture | `https://careers.stellantis.com/` |
| Tata Motors | Automotive OEMs | partial | scrapes, grade furniture | `https://www.tatamotors.com/careers/` |
| Berklee Online | Music Education Technology | partial | scrapes, grade furniture | `https://www.berklee.edu/career-center/online-job-listings` |
| Fraunhofer IDMT | Music Education Technology | partial | scrapes, grade furniture | `https://www.idmt.fraunhofer.de/de/jobs.html` |
| Musicians Institute | Music Education Technology | partial | scrapes, grade furniture | `https://www.mi.edu/artist-career-services/` |
| UC Berkeley CNMAT | Music Education Technology | partial | scrapes, grade furniture | `https://jobs.berkeley.edu/` |
| University of Miami Music | Music Education Technology | partial | scrapes, grade furniture | `https://careers.miami.edu/us/en` |
| Bluetooth SIG | Audio IP & Licensing | partial | scrapes, grade furniture | `https://www.bluetooth.com/careers/` |

## F. Careers-looking URL that still fails (185)

Lowest priority as a URL fix. Mostly JavaScript boards or pages we cannot parse,
which editing the URL will not help. But the shape test is fooled by any path
containing `recruit` or `opportunit` — Hidizs points at an influencer-recruitment
page and Master & Dynamic at `halliburton-opportunity` — so skim for those. An
HTTP 403 in the error column means blocking: that is a blocked-list decision.

| company | category | scope | status | error | seeded careers URL | found by discovery |
| --- | --- | --- | --- | --- | --- | --- |
| Baracoda | Hearing Aid & Hearing Tech | native | failed 20x |  | `https://baracoda.com/careers` |  |
| Earlens | Hearing Aid & Hearing Tech | native | failed 20x |  | `https://www.earlens.com/work-with-us` |  |
| Natus Medical | Hearing Aid & Hearing Tech | native | failed 20x |  | `https://natus.com/careers/` |  |
| Treble | Hearing Aid & Hearing Tech | native | failed 6x |  | `https://treblehealth.com/careers/` |  |
| Vivosonic | Hearing Aid & Hearing Tech | native | failed 4x |  | `https://www.vivosonic.com/careers` |  |
| BLON | Headphones & Personal Audio | native | failed 21x |  | `https://www.blonaudio.com/Job.html` |  |
| Corsair | Headphones & Personal Audio | native | failed 20x |  | `https://edix.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs` |  |
| Hidizs | Headphones & Personal Audio | native | failed 20x |  | `https://www.hidizs.net/pages/influencer-recruit` |  |
| THX Ltd | Headphones & Personal Audio | native | failed 20x |  | `https://www.thx.com/careers` |  |
| Audio-Technica | Headphones & Personal Audio | native | failed 19x |  | `https://www.audio-technica.com/en-us/careers` |  |
| Master & Dynamic | Headphones & Personal Audio | native | failed 19x |  | `https://www.masterdynamic.com/pages/halliburton-opportunity` |  |
| Shokz | Headphones & Personal Audio | native | failed 19x |  | `https://shokz.com/pages/careers` |  |
| Warwick Acoustics | Headphones & Personal Audio | native | failed 19x |  | `https://warwickacoustics.com/careers/` |  |
| Skullcandy | Headphones & Personal Audio | native | failed 3x |  | `https://www.skullcandy.com/pages/join-us` |  |
| Sandy Brown Associates | Acoustic Consulting & Engineering | native | failed 22x |  | `https://www.sandybrown.com/careers/` |  |
| WSDG (Walters-Storyk Design Group) | Acoustic Consulting & Engineering | native | failed 20x |  | `https://wsdg.com/careers/` |  |
| Auralex Acoustics | Acoustic Consulting & Engineering | native | failed 19x |  | `https://auralex.com/careers/` |  |
| Kinetics Noise Control | Acoustic Consulting & Engineering | native | failed 19x |  | `https://kineticsnoise.com/resources/careers` |  |
| Tempo Semiconductor | Audio Semiconductors | native | failed 19x |  | `https://temposemi.com/about/careers/` |  |
| Theatre Projects | Acoustic Consulting & Engineering | native | failed 19x |  | `https://theatreprojects.com/careers/` |  |
| Stantec | Acoustic Consulting & Engineering | native | failed 6x |  | `https://www.stantec.com/en/careers` |  |
| Hilson Moran | Acoustic Consulting & Engineering | native | failed 3x |  | `https://www.hilsonmoran.com/careers/` | `https://www.tyrenshm.com/careers/vacancies/` (unchecked) |
| Ramboll Group | Acoustic Consulting & Engineering | native | failed 3x; 16 old board rows kept |  | `https://careers.smartrecruiters.com/Ramboll3` |  |
| Auddia | AI/ML Audio | native | failed 19x |  | `https://www.auddia.com/careers` |  |
| Tortoise TTS | AI/ML Audio | native | failed 19x |  | `https://worldturtleday.org/join-the-movement/` |  |
| Audioshake | AI/ML Audio | native | failed 4x |  | `https://www.audioshake.ai/audioshake-careers` |  |
| LANDR | AI/ML Audio | native | failed 3x |  | `https://www.landr.com/careers` |  |
| Antelope Audio | Audio Interfaces & Converters | native | failed 5x |  | `https://en.antelopeaudio.com/careers/` |  |
| Pandorabots | Voice & Speech Technology | native | failed 20x |  | `https://www.pandorabots.com/careers/` |  |
| Respeecher | Voice & Speech Technology | native | failed 20x |  | `https://www.respeecher.com/careers` |  |
| Murf AI | Voice & Speech Technology | native | failed 19x |  | `https://murf.ai/ai-voice-agent/ai-recruiter` |  |
| Baidu (DuerOS) | Voice & Speech Technology | native | failed 13x |  | `https://talent.baidu.com/en/` |  |
| ElevenLabs | Voice & Speech Technology | native | failed 7x |  | `https://elevenlabs.io/careers` |  |
| Modeltalker | Voice & Speech Technology | native | failed 3x |  | `https://epyz.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/` |  |
| Expressive E | Electronic Musical Instruments | native | failed 20x |  | `https://www.expressivee.com/category/3-careers` |  |
| Make Noise | Electronic Musical Instruments | native | failed 20x |  | `https://www.makenoisemusic.com/careers/` |  |
| WMD (William Matthew Device) | Electronic Musical Instruments | native | failed 19x |  | `https://wmdevices.com/pages/careers` |  |
| Korg | Electronic Musical Instruments | native | failed 18x |  | `https://career.korg.com/` |  |
| Bastl Instruments | Electronic Musical Instruments | native | failed 4x |  | `https://bastl-instruments.com/careers` |  |
| Fishman Transducers | Professional Audio & Live Sound | native | failed 21x |  | `https://fishman.com/careers/` |  |
| Schoeps Mikrofone | Professional Audio & Live Sound | native | failed 21x |  | `https://schoeps.de/ueber-uns/jobs-praktika.html` |  |
| Dalet Digital Media | Professional Audio & Live Sound | native | failed 20x |  | `https://jobs.dalet.com/` |  |
| Deity Microphones | Professional Audio & Live Sound | native | failed 20x |  | `https://deitymic.com/careers/` |  |
| EAW | Professional Audio & Live Sound | native | failed 20x |  | `https://eaw.com/join-eaw-aes/` |  |
| Nagra | Professional Audio & Live Sound | native | failed 20x |  | `https://careers.nagra.com/` |  |
| Ashly Audio | Professional Audio & Live Sound | native | failed 19x |  | `https://ashly.com/careers/` |  |
| EarthQuaker Devices | Professional Audio & Live Sound | native | failed 19x |  | `https://recruiting.paylocity.com/Recruiting/Jobs/All/8dbec9ab-9f30-416a-9b1b-97e` |  |
| Kemper Amps | Professional Audio & Live Sound | native | failed 19x |  | `https://www.kemper-amps.com/jobs` |  |
| Tascam | Professional Audio & Live Sound | native | failed 19x |  | `https://www.tascam.com/us/careers` |  |
| Walrus Audio | Professional Audio & Live Sound | native | failed 19x |  | `https://www.walrusaudio.com/pages/careers` |  |
| DAS Audio | Professional Audio & Live Sound | native | failed 13x |  | `https://www.dasaudio.com/trabaja-con-nosotros/` |  |
| Two Rock Amplification | Professional Audio & Live Sound | native | failed 13x |  | `https://www.tworock.com/careers/` |  |
| RCS Sound Software | Professional Audio & Live Sound | native | failed 6x |  | `https://www.rcsworks.com/company/careers-at-rcs/` |  |
| Alcons Audio | Professional Audio & Live Sound | native | failed 4x |  | `https://www.alconsaudio.com/careers` |  |
| Lawo | Professional Audio & Live Sound | native | failed 4x |  | `https://lawo.com/company/career-at-lawo/` |  |
| Xilica | Professional Audio & Live Sound | native | failed 4x |  | `https://www.xilica.com/careers/` |  |
| Harmonic | Professional Audio & Live Sound | native | failed 3x |  | `https://careers.harmonicinc.com/` |  |
| SoundCam | Audio Testing & Measurement | native | failed 20x |  | `https://www.soundcam.com/en/careers` |  |
| Crystal Instruments | Audio Testing & Measurement | native | failed 19x |  | `https://www.crystalinstruments.com/careers` |  |
| DEWESoft | Audio Testing & Measurement | native | failed 7x |  | `https://dewesoft.com/careers` |  |
| Polytec | Audio Testing & Measurement | native | failed 4x |  | `https://www.polytec.com/en/career` |  |
| Pico Interactive | Gaming, VR & Immersive Audio | native | failed 21x |  | `https://www.picoxr.com/global/careers` |  |
| Epic Games | Gaming, VR & Immersive Audio | native | failed 20x |  | `https://www.epicgames.com/site/careers` |  |
| Firaxis Games | Gaming, VR & Immersive Audio | native | failed 19x |  | `https://firaxis.com/careers/` |  |
| Tencent Games | Gaming, VR & Immersive Audio | native | failed 19x |  | `https://jobs.tencent.com/` |  |
| Smilegate | Gaming, VR & Immersive Audio | native | failed 18x |  | `https://careers.smilegate.com/` |  |
| Magic Leap | Gaming, VR & Immersive Audio | native | failed 7x |  | `https://resources.magicleap.cloud/careers` |  |
| Bethesda | Gaming, VR & Immersive Audio | native | failed 4x |  | `https://www.elderscrollsonline.com/en-us/joinus` |  |
| Bigscreen | Gaming, VR & Immersive Audio | native | failed 4x |  | `https://www.bigscreenvr.com/careers` |  |
| Resolution Games | Gaming, VR & Immersive Audio | native | failed 4x |  | `https://jobs.resolutiongames.com/` |  |
| Skydance Interactive | Gaming, VR & Immersive Audio | native | failed 4x |  | `https://skydance.com/careers/` |  |
| Bungie | Gaming, VR & Immersive Audio | native | failed 3x |  | `https://careers.bungie.com/` |  |
| Nintendo | Gaming, VR & Immersive Audio | native | failed 3x |  | `https://careers.nintendo.com/` | `https://careers.nintendo.com/jobs/` (checked: 54 jobs, **3 audio**) |
| Paradox Interactive | Gaming, VR & Immersive Audio | native | failed 3x |  | `https://www.paradoxinteractive.com/career` | `https://career.paradoxplaza.com/jobs` (checked: 20 jobs, **0 audio**) |
| Steg | Car Audio | native | failed 21x |  | `https://steg.com/site-and-buildings/talent/` |  |
| Aquatic AV | Car Audio | native | failed 20x |  | `https://www.aquaticav.com/pages/careers` |  |
| Dynaudio Automotive | Car Audio | native | failed 20x |  | `https://job.dynaudio.com/` |  |
| Hertz Car Audio | Car Audio | native | failed 20x |  | `https://www.hertzaudiovideo.com/en/careers` |  |
| Sundown Audio | Car Audio | native | failed 20x |  | `https://sundownaudio.com/pages/careers` |  |
| Meridian Audio Automotive | Car Audio | native | failed 19x |  | `https://www.meridian-audio.com/the-future-of-sound/work-with-meridian/` |  |
| JL Audio | Car Audio | native | failed 4x |  | `https://www.jlaudio.com/careers` |  |
| Stetsom | Car Audio | native | failed 4x |  | `https://jobs.quickin.io/stetsom?src=Pagina_de_Carreiras` |  |
| Audison | Car Audio | native | failed 2x; 5 old board rows kept | HTTP 202 | `https://elettromedia.com/careers` |  |
| ESPN Audio | Recording Studios & Post Houses | native | failed 21x |  | `https://www.espn.com/careers` |  |
| DeWolfe Music | Recording Studios & Post Houses | native | failed 20x |  | `https://jobs.dewolfemusic.com/` |  |
| Extreme Music | Recording Studios & Post Houses | native | failed 20x |  | `https://www.extrememusic.com/talent/hans-zimmer` |  |
| Sunset Sound | Recording Studios & Post Houses | native | failed 20x |  | `https://www.sunsetsound.com/careers` |  |
| Artlist | Recording Studios & Post Houses | native | failed 19x |  | `https://artlist.io/careers` |  |
| KPM Music | Recording Studios & Post Houses | native | failed 19x |  | `https://jobs.kpmmusic.com/en/` |  |
| Netflix Post | Recording Studios & Post Houses | native | failed 19x |  | `https://www.netflix.com/NotFound?prev=https%3A%2F%2Fwww.netflix.com%2Fcareers` |  |
| NBCUniversal Audio | Recording Studios & Post Houses | native | failed 3x |  | `https://www.nbcuniversal.com/careers` |  |
| Flux Audio | Audio Plugins & Virtual Instruments | native | failed 21x |  | `https://www.flux.audio/2024/05/30/join-flux-at-infocomm-2024-in-las-vegas-for-an` |  |
| Best Service | Audio Plugins & Virtual Instruments | native | failed 20x |  | `https://www.bestservice.com/careers` |  |
| ProjectSAM | Audio Plugins & Virtual Instruments | native | failed 20x |  | `https://jobs.projectsam.com/` |  |
| Vienna Symphonic Library | Audio Plugins & Virtual Instruments | native | failed 20x |  | `https://www.vsl.co.at/careers` |  |
| Audified | Audio Plugins & Virtual Instruments | native | failed 19x |  | `https://audified.com/careers/` |  |
| Gravity Audio | Audio Plugins & Virtual Instruments | native | failed 19x |  | `https://gravityaudio.net/careers` |  |
| Melda MAudioDynamics | Audio Plugins & Virtual Instruments | native | failed 19x |  | `https://www.meldaproduction.com/about/jobs` |  |
| Toontrack | Audio Plugins & Virtual Instruments | native | failed 19x |  | `https://www.toontrack.com/news/join-the-drumception-contest/` |  |
| MeldaProduction | Audio Plugins & Virtual Instruments | native | failed 1x |  | `https://www.meldaproduction.com/about/jobs` |  |
| SnoreLab | Audio Health & Wellness | native | failed 19x |  | `https://www.snorelab.com/careers` |  |
| Sound Oasis | Audio Health & Wellness | native | failed 19x |  | `https://www.soundoasis.com/careers` |  |
| Geneva Lab | Hi-Fi & Consumer Speakers | native | failed 21x |  | `https://www.genevalab.com/company/careers` |  |
| Peachtree Audio | Hi-Fi & Consumer Speakers | native | failed 21x |  | `https://www.peachtreeaudio.com/pages/carina-phase-2-trade-opportunity` |  |
| Pro-Ject Audio | Hi-Fi & Consumer Speakers | native | failed 21x |  | `https://www.project-audio.com/de/jobs/` |  |
| Quadral | Hi-Fi & Consumer Speakers | native | failed 21x |  | `https://jobs.quadral.com/` |  |
| Cabasse | Hi-Fi & Consumer Speakers | native | failed 20x |  | `https://www.cabasse.com/carriere/` |  |
| Canton | Hi-Fi & Consumer Speakers | native | failed 20x |  | `https://www.canton.de/unternehmen/karriere/` |  |
| Cary Audio | Hi-Fi & Consumer Speakers | native | failed 20x |  | `https://caryaudio.com/join-us-at-the-2015-rocky-mountain-audio-fest/` |  |
| Clearaudio | Hi-Fi & Consumer Speakers | native | failed 20x |  | `https://www.clearaudio.de/karriere/` |  |
| iFi Audio | Hi-Fi & Consumer Speakers | native | failed 20x |  | `https://ifi-audio.com/pages/job-board` |  |
| Manley Labs | Hi-Fi & Consumer Speakers | native | failed 20x |  | `https://www.manley.com/careers` |  |
| StormAudio | Hi-Fi & Consumer Speakers | native | failed 20x |  | `https://www.stormaudio.com/join-our-team/` |  |
| VPI Industries | Hi-Fi & Consumer Speakers | native | failed 20x |  | `https://www.vpiindustries.com/about/careers` |  |
| Esoteric | Hi-Fi & Consumer Speakers | native | failed 19x |  | `https://www.esoteric.com/careers` |  |
| Micromega | Hi-Fi & Consumer Speakers | native | failed 19x |  | `https://micromega.com/pages/notices-et-modes-demploi` |  |
| Mola Mola | Hi-Fi & Consumer Speakers | native | failed 19x |  | `http://www.molamola.be/en/careers` |  |
| MTX Audio | Hi-Fi & Consumer Speakers | native | failed 19x |  | `https://www.mitekusa.com/careers/` |  |
| NHT Loudspeakers | Hi-Fi & Consumer Speakers | native | failed 19x |  | `https://www.nhthifi.com/pages/careers` |  |
| VTL | Hi-Fi & Consumer Speakers | native | failed 19x |  | `https://www.vtl.com/careers` |  |
| MBL Radialstrahler | Hi-Fi & Consumer Speakers | native | failed 12x |  | `https://www.mbl.de/en/jobs` |  |
| Audiolab | Hi-Fi & Consumer Speakers | native | failed 4x |  | `https://iaggroup.com/jobs/current-vacancies/` |  |
| Roon Labs | Hi-Fi & Consumer Speakers | native | failed 4x |  | `https://roon.app/en/jobs` |  |
| Antares Audio Technologies | DAW & Music Production Software | native | failed 20x |  | `https://www.antarestech.com/careers` |  |
| Audius | DAW & Music Production Software | native | failed 20x |  | `https://audius.co/careers` |  |
| Slate Digital | DAW & Music Production Software | native | failed 20x |  | `https://slatedigital.com/careers/` |  |
| Audiomack | DAW & Music Production Software | native | failed 19x |  | `https://audiomack.com/careers` |  |
| Splice | DAW & Music Production Software | native | failed 4x |  | `https://splice.com/careers` |  |
| Algoriddim (djay) | DJ Equipment | native | failed 21x |  | `https://www.algoriddim.com/jobs` |  |
| Firelight Technologies (FMOD) | Audio Middleware & SDK | native | failed 21x |  | `https://www.fmod.com/careers` |  |
| PS Audio | Audio Accessories & Cables | native | failed 21x |  | `https://www.psaudio.com/pages/careers` |  |
| Serato | DJ Equipment | native | failed 21x |  | `https://serato.com/careers#current-openings` |  |
| SKB Cases | Audio Accessories & Cables | native | failed 21x |  | `https://www.skbcases.com/pages/careers` |  |
| Gator Cases | Audio Accessories & Cables | native | failed 20x |  | `https://gatorco.com/careers/` |  |
| Pelican Cases | Audio Accessories & Cables | native | failed 20x |  | `https://www.pelican.com/us/en/careers` |  |
| Audiokinetic (Wwise) | Audio Middleware & SDK | native | failed 19x |  | `https://www.audiokinetic.com/en/about/careers/` |  |
| B&C Speakers | Transducer & Driver Manufacturers | native | failed 19x |  | `https://www.bcspeakers.com/en/work-with-us` |  |
| BDI | Audio Accessories & Cables | native | failed 19x |  | `https://www.bdiusa.com/careers` |  |
| Ecler | DJ Equipment | native | failed 19x |  | `https://www.ecler.com/why-ecler/work-with-us/` |  |
| Hercules DJ | DJ Equipment | native | failed 19x |  | `https://www.hercules.com/en-us/join-the-dj-affiliate-program-now/` |  |
| Switchcraft | Audio Accessories & Cables | native | failed 13x |  | `https://myjobs.adp.com/heico/cx/job-listing?keyword=Switchcraft` |  |
| Volumio | Smart Home & IoT Audio | native | failed 6x |  | `https://volumio.com/careers/` |  |
| Canare | Audio Accessories & Cables | native | failed 4x |  | `https://www.canare.com/jobs` |  |
| Huawei | Consumer Electronics & Tech | partial | failed 21x |  | `https://career.huawei.com/cn` |  |
| DSP Concepts | Consumer Electronics & Tech | partial | failed 19x |  | `https://dspconcepts.com/careers` |  |
| Oppo | Consumer Electronics & Tech | partial | failed 19x |  | `https://careers.oppo.com/university/oppo/` |  |
| Vivo | Consumer Electronics & Tech | partial | failed 18x |  | `https://career.vivo.com/home` |  |
| Knowles Corporation | Consumer Electronics & Tech | partial | failed 13x |  | `https://myjobs.adp.com/knowles/cx` |  |
| Realtek Semiconductor | Consumer Electronics & Tech | partial | failed 13x |  | `https://www.realtek.com/en/careers` |  |
| LG Electronics | Consumer Electronics & Tech | partial | failed 3x |  | `https://lge-careers.com/` | `https://boards.greenhouse.io/lgelectronics` (checked: 47 jobs, **0 audio**) |
| Guitar Center | Audio Retailers & Distributors | partial | failed 19x | HTTP 403 | `https://www.guitarcenter.com/careers` |  |
| Takealot Audio | Audio Retailers & Distributors | partial | failed 19x |  | `https://www.takealot.com/careers` |  |
| World Wide Stereo | Audio Retailers & Distributors | partial | failed 19x |  | `https://www.worldwidestereo.com/pages/careers` |  |
| Best Buy | Audio Retailers & Distributors | partial | failed 1x |  | `https://jobs.bestbuy.com/bby` |  |
| Navistar (Traton) | Automotive OEMs | partial | failed 20x |  | `https://careers.navistar.com/` |  |
| Energica Motor | Automotive OEMs | partial | failed 19x |  | `https://energicamotor.com/careers` |  |
| Fisker | Automotive OEMs | partial | failed 19x |  | `https://www.fiskerinc.com/careers` |  |
| General Motors | Automotive OEMs | partial | failed 19x | HTTP 403 | `https://search-careers.gm.com/` |  |
| Mercedes-Benz | Automotive OEMs | partial | failed 19x |  | `https://jobs.mercedes-benz.com/enUS` |  |
| Lamborghini | Automotive OEMs | partial | failed 4x |  | `https://www.lamborghini.com/en-en/company/careers` |  |
| AGCO | Automotive OEMs | partial | failed 3x |  | `https://careers.agcocorp.com/` |  |
| BrightDrop (GM) | Automotive OEMs | partial | failed 3x |  | `https://www.gd.com/careers/` |  |
| CNH Industrial | Automotive OEMs | partial | failed 3x |  | `https://join.cnh.com/` |  |
| PACCAR (Kenworth/Peterbilt) | Automotive OEMs | partial | failed 3x |  | `https://jobs.paccar.com/` | `https://jobs.paccar.com/go/Engineering-Jobs/2706200/` (checked: 211 jobs, **1 audio**) |
| Musicnotes | Music Education Technology | partial | failed 18x | HTTP 403 | `https://www.musicnotes.com/careers` |  |
| Flowkey | Music Education Technology | partial | failed 7x |  | `https://flowkey.breezy.hr/` |  |
| Stanford CCRMA | Music Education Technology | partial | failed 4x |  | `https://careersearch.stanford.edu/` |  |
| Anghami | Streaming & Music Services | partial | failed 21x |  | `https://anghami.zenats.com/en/careers_page` |  |
| Gaana (Times Internet) | Streaming & Music Services | partial | failed 21x |  | `https://gaana.com/music-label/sound-talent-media` |  |
| Genie Music | Streaming & Music Services | partial | failed 21x |  | `https://www.geniemusic.co.kr/people/recruit.do` |  |
| Libsyn | Streaming & Music Services | partial | failed 21x |  | `https://libsyn.com/careers/` |  |
| VK Music | Streaming & Music Services | partial | failed 21x |  | `https://vk.ru/careers` |  |
| Bandcamp | Streaming & Music Services | partial | failed 20x |  | `https://www.songtradr.com/careers` |  |
| Qobuz | Streaming & Music Services | partial | failed 20x |  | `https://www.qobuz.com/us-en/careers` |  |
| Songkick | Streaming & Music Services | partial | failed 20x |  | `https://www.songkick.com/jobs` |  |
| Last.fm (CBS) | Streaming & Music Services | partial | failed 19x |  | `https://www.last.fm/about/jobs` |  |
| Pandora (SiriusXM) | Streaming & Music Services | partial | failed 19x |  | `https://careers.siriusxm.com/careers/` |  |
| Resident Advisor | Streaming & Music Services | partial | failed 19x |  | `https://ra.co/about/jobs` |  |
| Ghostly International | Streaming & Music Services | partial | failed 13x |  | `https://ghostly.com/pages/careers` |  |
| Joox (Tencent) | Streaming & Music Services | partial | failed 13x |  | `https://careers.tencent.com/` |  |
| Tracklib | Streaming & Music Services | partial | failed 4x |  | `https://careers.tracklib.com/` |  |
| Songtradr | Streaming & Music Services | partial | failed 1x |  | `https://www.songtradr.com/careers` |  |
| Alliance for Open Media | Audio IP & Licensing | partial | failed 22x |  | `https://aomedia.org/join/` |  |
| MPEG (ISO/IEC) | Audio IP & Licensing | partial | failed 19x |  | `https://www.mpeg.org/joint-jpeg-mpeg-workshop-on-radiance-fields/` |  |
| ITU-R | Audio IP & Licensing | partial | failed 4x |  | `https://jobs.itu.int/` | `https://jobs.itu.int/go/View-all-categories/8942455/` (checked: 46 jobs, **0 audio**) |

## Leave alone — the page says there are no openings (46)

Fetched, and the page's own text says there are no current vacancies or only
invites speculative applications. The scrape failing, or finding nothing, is
correct. Do not change these URLs.

- Metric Halo — `https://www.mhsoftware.com/using-connectdaily-5-0s-new-pooled-resource-feature/`
- Acapela Group — `https://www.acapela-group.com/voiceai-people-behind-technology-at-acapela-group/`
- ReadSpeaker — `https://www.readspeaker.com/careers/`
- Sequential — `https://sequential.com/about/careers/`
- Waldorf Music — `https://waldorfmusic.com/de/jobs/`
- Joué — `https://www.joueclub.fr/contenu/recrutement.html`
- AMS Neve — `https://www.ams-neve.com/careers/`
- Rupert Neve Designs — `https://rupertneve.com/careers`
- dB Technologies — `https://www.dbtechnologies.com/us/our-world/careers`
- Empress Effects — `https://empresseffects.com/pages/job-openings`
- Goodhertz — `https://goodhertz.com/jobs/`
- RCF — `https://www.rcf.it/en/work-with-us`
- Renkus-Heinz — `https://www.renkus-heinz.com/careers`
- QSC — `https://qsccareersemea-qsc.icims.com/jobs/`
- Audio Precision — `https://www.audioprecision.com/careers`
- Annapurna Interactive — `https://www.annapurna.com/jobs`
- Fast Travel Games — `https://www.fasttravelgames.com/career`
- Embracer Group — `https://www.embracer.com/about/join-our-team/`
- HTC (Vive) — `https://globalcareers-htcvive.icims.com/jobs/intro?hashed=-435804063&mobile=fals`
- Sega — `https://careers.sega.co.uk/vacancies`
- Sports Interactive — `https://careers.sega.co.uk/vacancies`
- Skar Audio — `https://www.skaraudio.com/jobs`
- Fox Post Production — `https://www.fox.com/detail/series/SER273417EDMY/senate-hearing-developing-workfo`
- BMG Production Music — `https://careers.smartrecruiters.com/BMG`
- Cherry Audio — `https://cherryaudio.com/company/jobs`
- Spectrasonics — `https://www.spectrasonics.net/company/employment.php`
- Cycling '74 — `https://cycling74.com/careers`
- Orchestral Tools — `https://www.orchestraltools.com/company/careers`
- SPL (plugins) — `https://spl.audio/en/`
- Sound+ Sleep — `https://www.soundofsleep.com/jobs/`
- Rega Research — `https://www.rega.co.uk/careers`
- DALI Speakers — `https://www.dali-speakers.com/en/about-dali/careers-at-dali/`
- Simaudio (Moon) — `https://simaudio.com/en/careers/`
- Acoustica Mixcraft — `https://acoustica.com/company/jobs`
- Waves Audio — `https://www.waves.com/careers`
- Reloop — `https://www.reloop.com/jobcenter`
- AudioQuest — `https://www.audioquest.com/pages/careers`
- Void Acoustics — `https://voidacoustics.com/careers/`
- OnePlus — `https://recruit.zohopublic.in/recruit/Portal.na?digest=LN%40TPV3Mvf0el6bBA.0JxQm`
- Kia — `https://www.kia.com/us/en/careers`
- PRX — `https://www.prx.org/company/about/#jobs`
- Audioboom — `https://audioboom.com/about/jobs`
- Monstercat — `https://www.monstercat.com/careers`
- Napster (Rhapsody) — `https://www.napster.com/careers`
- LiveOne — `https://www.liveone.com/careers.html`
- CD Baby — `https://job-boards.greenhouse.io/cdbabyjobs`

## Counts

- A. dead URL: 16
- B. yours, still failing: 5
- C. not a careers page, failing: 102
- D. not a careers page, scraping the wrong page: 11
- E. careers-looking, stores navigation: 45
- F. careers-looking, still failing: 185
- Leave alone: 46
- Excluded because they work: 133

