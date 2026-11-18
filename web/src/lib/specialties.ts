export interface Specialty {
	id: string;
	slug: string;
	heading: string;
	lead: string;
}

export const SPECIALTIES: Specialty[] = [
	{
		id: 'acoustics_consulting',
		slug: 'acoustics',
		heading: 'Acoustics jobs',
		lead: 'Architectural, building and environmental acoustics roles: acoustic consultants, noise and vibration analysts, and engineers working on sound isolation, room acoustics and noise control for buildings and infrastructure.'
	},
	{
		id: 'audio_dsp_embedded',
		slug: 'audio-dsp',
		heading: 'Audio DSP jobs',
		lead: 'Audio DSP and embedded firmware roles: filters, EQ, dynamics, spatial audio, beamforming and noise cancellation, plus the real-time firmware that runs them on DSPs, ARM cores and embedded Linux.'
	},
	{
		id: 'audio_software',
		slug: 'audio-software-engineering',
		heading: 'Audio software engineering jobs',
		lead: 'Software roles building audio applications, engines, plugins, drivers and frameworks, usually in C++ with tools like JUCE, at DAW makers, platform companies and audio product teams.'
	},
	{
		id: 'game_audio_interactive',
		slug: 'game-audio',
		heading: 'Game audio jobs',
		lead: 'Sound designers, audio programmers and technical sound designers creating and implementing interactive audio for games and XR, typically with Wwise, FMOD or engine-native audio tools.'
	},
	{
		id: 'sound_design',
		slug: 'sound-design',
		heading: 'Sound design jobs',
		lead: 'Creative sound design for film, television, products, installations and interactive media: foley, sound effects, soundscapes and sonic branding.'
	},
	{
		id: 'live_sound_events',
		slug: 'live-sound',
		heading: 'Live sound jobs',
		lead: 'Live sound and event production roles for concerts, theatre, broadcast and corporate events: front of house and monitor engineers, A/V technicians and system techs.'
	},
	{
		id: 'music_production_recording',
		slug: 'music-production',
		heading: 'Music production and recording jobs',
		lead: 'Studio and production roles capturing and finishing music and spoken audio: recording, tracking, mixing, mastering and audio engineering for studios, labels and media companies.'
	},
	{
		id: 'audio_aiml',
		slug: 'audio-machine-learning',
		heading: 'Audio AI and machine learning jobs',
		lead: 'Machine learning roles applied to sound: speech recognition and synthesis, source separation, music information retrieval, generative audio and ML-based audio enhancement.'
	},
	{
		id: 'audio_research',
		slug: 'audio-research',
		heading: 'Audio research jobs',
		lead: 'Research scientist and research engineer roles in audio, acoustics and perception, from spatial audio and novel acoustic architectures to prototyping research hardware.'
	},
	{
		id: 'audio_ee',
		slug: 'audio-electrical-engineering',
		heading: 'Audio electrical engineering jobs',
		lead: 'Hardware engineering roles in analog and digital audio circuit design: amplifiers, mixed-signal circuits, power supplies and PCB design for consumer and professional audio products.'
	},
	{
		id: 'transducers',
		slug: 'transducer-engineering',
		heading: 'Transducer and loudspeaker engineering jobs',
		lead: 'Engineering roles designing loudspeakers, headphone and earbud drivers and acoustic chambers, covering motor and suspension design, materials, simulation and transducer measurement.'
	},
	{
		id: 'microphones_recording',
		slug: 'microphone-engineering',
		heading: 'Microphone engineering jobs',
		lead: 'Roles designing microphones, MEMS microphones, microphone arrays, wireless microphone systems and the capture pipelines behind them.'
	},
	{
		id: 'audio_systems',
		slug: 'audio-systems',
		heading: 'Audio systems engineering jobs',
		lead: 'Engineers who integrate and tune the whole audio path in phones, wearables, smart speakers and other products, owning how a product sounds end to end.'
	},
	{
		id: 'automotive_audio',
		slug: 'automotive-audio',
		heading: 'Automotive audio jobs',
		lead: 'Roles integrating, tuning and testing audio systems in vehicles: cabin acoustics, infotainment audio, sound system tuning and in-car measurement.'
	},
	{
		id: 'nvh',
		slug: 'nvh',
		heading: 'NVH engineering jobs',
		lead: 'Noise, vibration and harshness roles measuring and reducing unwanted sound and vibration in vehicles, aircraft and industrial products.'
	},
	{
		id: 'test_measurement_qa',
		slug: 'audio-test-engineering',
		heading: 'Audio test and measurement jobs',
		lead: 'Roles verifying that audio hardware and software perform: acoustic and electroacoustic measurement, test automation and fixtures, lab and anechoic chamber work, and production quality.'
	},
	{
		id: 'audio_product_mechanical',
		slug: 'audio-mechanical-engineering',
		heading: 'Audio mechanical and product engineering jobs',
		lead: 'Mechanical, industrial and manufacturing engineering for audio hardware: enclosures and acoustic fit, materials, tooling, design for manufacturing and new product introduction.'
	},
	{
		id: 'music_technology',
		slug: 'music-technology',
		heading: 'Music technology jobs',
		lead: 'Roles building instruments and creative tools for musicians: synthesizers, effects pedals, MIDI controllers, drum machines and virtual instruments.'
	},
	{
		id: 'psychoacoustics_perception',
		slug: 'psychoacoustics',
		heading: 'Psychoacoustics jobs',
		lead: 'Roles studying how people hear: listening test design, subjective audio evaluation, HRTF and spatial hearing research, and hearing science.'
	},
	{
		id: 'audiology_hearing',
		slug: 'audiology-hearing',
		heading: 'Audiology and hearing jobs',
		lead: 'Hearing care roles at hearing health companies and clinics: audiologists, hearing instrument specialists, and hearing aid and cochlear implant support.'
	},
	{
		id: 'sales_marketing_cs',
		slug: 'audio-sales-marketing',
		heading: 'Audio sales and marketing jobs',
		lead: 'Commercial roles at audio companies: sales and applications engineering, business development, account management, product marketing and customer success for audio products.'
	},
	{
		id: 'av_systems_integration',
		slug: 'av-systems',
		heading: 'AV systems design and integration jobs',
		lead: 'Roles designing, installing, programming and supporting audiovisual systems in buildings and venues: AV consultants and designers, integrators, control system programmers, meeting-room AV and public address systems.'
	},
	{
		id: 'business_operations',
		slug: 'business-operations',
		heading: 'Business and operations jobs at audio companies',
		lead: 'Roles at audio companies outside engineering and sales: finance, people and HR, operations, supply chain, IT, product and program management, design and general internships.'
	}
];

export const SPECIALTY_BY_SLUG = new Map(SPECIALTIES.map((s) => [s.slug, s]));
export const SPECIALTY_BY_ID = new Map(SPECIALTIES.map((s) => [s.id, s]));

export function specialtyPath(categoryId: string): string {
	const specialty = SPECIALTY_BY_ID.get(categoryId);
	return specialty ? `/jobs/${specialty.slug}` : `/jobs?category=${categoryId}`;
}
