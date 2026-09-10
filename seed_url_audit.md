# Seed careers-URL audit

Read-only. This is a proposal list requiring human confirmation, not a
list of confirmed problems. Nothing here is written to
data/audio_companies_final.json or to the database. Classification is
by URL shape alone — there is no network access, so this cannot see
what the URL actually serves.

Bucket A in particular contains legitimate parent-company URLs. A
careers page hosted on a different domain than the company's own is a
common and correct pattern — for example Soundtrap's careers URL
points at lifeatspotify.com, which is correct because Soundtrap is
owned by Spotify, but this heuristic flags it anyway because the host
does not contain "soundtrap". Verify each bucket A entry before
treating it as wrong.

- entries flagged: 141
- D — error / for-sale / press release: 15
- A — wrong host, no careers vocabulary: 23
- C — right host, no careers vocabulary: 103
- B — wrong host, careers-shaped (likely parent company, not listed): 115 (59 verified)

## D. the URL is an error page, a for-sale page, or a press release — 15 (11 verified)

V  Actran (MSC Software)            https://hexagon.com/company/newsroom/press-releases/2025/hexagon-agrees-sale-of-design--engineering-busin
V  Cadence Design Systems           https://www.cadence.com/en_US/home/errors/accessdenied.html
V  Decibels                         https://www.domaineasy.com/buy-domain/www.decibels.com
V  Flik                             https://www.flik.com/404-page-not-found/
V  Free Field Technologies          https://hexagon.com/company/newsroom/press-releases/2025/hexagon-agrees-sale-of-design--engineering-busin
V  Honor                            https://www.honor.com/global/404/
V  McIntosh Automotive              https://www.mcintoshlabs.com/Page-Not-Found
V  Nexon                            https://www.nexon.com/main/en/error?aspxerrorpath=%2Fen%2Fcareers
V  Shozy                            https://www.shozyaudio.com/password
V  Ubisoft                          https://www.ubisoft.com/en-us/company/404
V  ZTE                              https://www.zte.com.cn/china/404.html
-  Great Wall Motors                https://www.gwm-global.com/error/error.html?referrer=https%3A%2F%2Fwww.gwm-global.com%2Fen%2Fcareers
-  Kush Audio                       https://www.hugedomains.com/domain_profile.cfm?d=kushaudio.com
-  Powerbass                        https://www.hugedomains.com/domain_profile.cfm?d=powerbass.com
-  Vienna Acoustics                 https://www.hugedomains.com/domain_profile.cfm?d=viennaacoustics.com

## A. wrong host and no careers vocabulary anywhere in the URL — 23 (21 verified)

V  Dear Reality                     https://www.sennheiser.com/en-us/immersive/dear-reality
V  Deep Silver                      https://www.animefactory.it/
V  Dehumaniser                      https://afdam.com/
V  EarQ                             https://www.cq-partners.com/what-we-do/business-planning/training-development/
V  Electro-Voice                    https://ev.com:443/new-cars
V  HGC Engineering                  https://acoustical-consultants.com/
V  Jaybird                          https://support.logi.com/hc/en-us
V  Line 6                           https://yamahaguitargroup.com/company/#careers
V  MESA/Boogie                      https://www.gibson.com/pages/mesa-boogie
V  Metric Halo                      https://www.mhsoftware.com/using-connectdaily-5-0s-new-pooled-resource-feature/
V  Middle Atlantic                  https://www.legrandav.com/products/middle_atlantic_products
V  NCSoft                           https://www.nc.com/
V  Omnimount                        https://www.ergotron.com/omnimount
V  Plantronics                      https://www.hp.com/us-en/poly.html
V  Poly (HP)                        https://www.hp.com/us-en/poly.html
V  Roland                           https://www.youtube.com/watch?v=jaO0LffIs1A
V  SOUNDFlow                        https://voxxintl.zendesk.com/hc/en-us
V  Sivantos Group                   https://www.wsa.com/
V  SoapBox Labs                     https://www.curriculumassociates.com/about/ailabs
V  Soundtrap                        https://www.lifeatspotify.com/
V  WS Audiology (Signia/Widex)      https://www.wsa.com/
-  Cross DJ (Mixvibes)              https://fr.linkedin.com/company/mixvibes
-  Fostex                           https://898093.studiowatersolutions.com/?mlk=kzzmoibVw0zDfg4SAYjqBFGr9jEpCc8%2BSUgvklbslQS7mssoUbAEzoPTkU

## C. right host, but no careers vocabulary in the URL — 103 (101 verified)

V  AIVA                             https://www.aiva.ai/
V  Akustiks                         https://akustiks.com/
V  Audio Ltd                        https://www.sounddevices.com/
V  Bandsintown                      https://www.bandsintown.com/a/7488894
V  BeatMaker (Intua)                https://intua.net/
V  Beyma                            https://www.beyma.com/en/home/
V  Blaupunkt                        https://www.blaupunkt.com/en-us/
V  CEVA                             https://www.ceva-ip.com/
V  Cabasse                          https://www.cabasse.com/carriere/
V  Creative Technology              https://us.creative.com:443/
V  Davis Acoustics                  https://davis-acoustics.com/en/teamnv/
V  Deezer                           https://www.deezer-investors.com/
V  Devialet                         https://devialet.welcomekit.co/
V  Devicemarket                     https://devicemarket.com/
V  Digigram                         https://www.digigram.com/
V  Ditto Music                      https://login.dittomusic.com/en/
V  EarMaster                        https://www.earmaster.com/company/work-at-earmaster.html
V  Eargo                            https://www.eargo.com/
V  EastWest Sounds                  https://www.soundsonline.com/
V  Echo Digital Audio               http://www.echoaudio.com/about/
V  Embrace Hearing                  https://embracehearing.com/user-guides
V  Endlesss                         https://endlesss.fm/
V  Equator Sound                    https://www.equatorsound.com/lander
V  Evertz Microsystems              https://evertz.com/
V  Fairphone                        https://www.fairphone.com/team
V  Focal                            https://www.focal.com/fr/recrutement
V  Fractal Audio Systems            https://www.fractalaudio.com/p-fx8-multieffects-pedalboard/
V  Fujitsu                          https://global.fujitsu/en-global
V  Fulcrum Acoustic                 https://www.fulcrum-acoustic.com/projects/benson-center-for-arts-and-learning
V  Funktion-One                     https://funktion-one.com/about/
V  Groove3                          https://www.groove3.com/
V  GungHo Online                    https://www.gungho.com/investments/#opportunities
V  Harbeth Audio                    https://harbeth.co.uk/
V  Hearing Health Foundation        https://hearinghealthfoundation.org/help
V  Heco Audio                       https://heco-audio.de/Ambient-Line/
V  Hegel Music Systems              https://www.hegel.com/en/
V  Hit'n'Mix                        https://hitnmix.com
V  Hush Acoustics                   https://www.hushacoustics.co.uk/technical-resources/environmental/
V  Hyundai Motor                    https://www.hyundai.com/worldwide/en
V  Immersive Audio                  https://www.immersiveaudio.com/lander
V  Inventis                         https://inventis.it/it-it/soluzioni/medicina-del-lavoro
V  JLab Audio                       https://www.jlab.com/products/epic-keyboard-mouse-bundle
V  JamPlay                          https://jamplay.com:443/
V  Joué                             https://www.joueclub.fr/contenu/recrutement.html
V  KEF                              https://us.kef.com/
V  Kawasaki Motors                  https://www.kawasaki.com/en-us/
V  Klotz                            https://www.klotz-ais.com/
V  L-Acoustics                      https://www.l-acoustics.com/
V  LMS (Siemens)                    https://www.siemens.com/en-us/
V  Larian Studios                   https://eu.merch.larian.com/products/divinity-original-sin-the-boardgame
V  Lexie Hearing                    https://www.lexiehearing.com/us
V  Luminary                         https://luminarypodcasts.com/?country=US
V  Mackie DL                        https://mackie.com/
V  Magix (Samplitude/Sequoia)       https://www.magix.com/us/
V  McCauley Sound                   https://www.mccauleysound.com/
V  McDSP                            https://mcdsp.com/
V  Musicbed                         https://www.musicbed.com/
V  Musician's Friend                https://www.musiciansfriend.com/pages/ways-to-pay
V  Musixmatch                       https://about.musixmatch.com/open-positions
V  NYU Music Technology             https://www.nyu.edu/about/university-initiatives/nyu-irl.html
V  Naim Audio                       https://www.naimaudio.com/
V  Nuheara                          https://www.nuheara.com/team-behind-the-tech/
V  OmniMic                          https://www.omnimic.com/lander
V  PRX                              https://www.prx.org/company/about/#jobs
V  Puremix                          https://www.puremix.com/
V  Qu-Bit Electronix                https://www.qubitelectronix.com/team
V  QuietOn                          https://quieton.com
V  RF Venue                         https://www.rfvenue.com/about#jobs
V  Raal Requisite                   https://requisiteaudio.com/
V  Radial Engineering               https://www.radialeng.com/keyboard
V  Rock Heritage                    https://www.rockheritage.com/lander
V  Rumblefish                       https://www.rumblefish.com/team/
V  SPL (plugins)                    https://spl.audio/en/
V  SVS                              https://www.svsound.com/pages/about-us
V  Sanus                            https://www.sanus.com/en_US/
V  Soma Laboratory                  https://somasynths.com/team/
V  Sounds.com                       https://www.native-instruments.com:443/
V  Spatial                          https://www.spatial.io/team
V  Spitch                           https://spitch.ai/de/
V  Spotify                          https://www.lifeatspotify.com/
V  Stem                             https://stem.is/
V  System Audio                     https://www.system-audio.com/product-category/active-wireless-speakers/
V  The Music Bed                    https://www.musicbed.com/
V  Threshold Acoustics              https://threshold.llc/team
V  TikTok Audio (ByteDance)         https://www.bytedance.com/en/
V  Triangle Loudspeakers            https://trianglehifi.us/
V  TuneIn                           https://tunein.com/
V  Turtle Beach                     https://www.turtlebeach.com/pages/influencers
V  Two Notes Audio                  http://twonotes.com/
V  Ultimate Support                 https://www.ultimatesupport.com/collections/guitar-stands-pedalboards-accessories
V  Universal Production Music       https://www.universalproductionmusic.com:443/en-us
V  University of York Audio Lab     https://www.york.ac.uk/study/work/
V  Valve Corporation                https://www.valvesoftware.com/en/
V  Vintage King Audio               https://vintageking.com/recording/studio-furniture/19-outboard-racks
V  Virtual DJ (Atomix)              https://virtualdj.com/atomixproductions/
V  Voiceflow                        https://www.voiceflow.com/about#careers
V  Voiser                           https://www.voiser.net/
V  Volkswagen                       https://www.volkswagen.de/de.html
V  Wheatstone                       https://wheatstone.com/contact-us/
V  Zaxcom                           https://zaxcom.com/ibc-2026/
V  dCS                              https://dcsaudio.com/
-  Creek Audio                      https://creekaudio.com/
-  Modal Electronics                https://modalelectronics.com
