<script lang="ts">
	import { page } from '$app/state';
	import discordLink from '$lib/data/discord-link.txt?raw';

	const discord = discordLink.trim();
	const links = [
		{ href: '/jobs', label: 'Jobs' },
		{ href: '/companies', label: 'Companies' },
		{ href: '/resources', label: 'Resources' },
		{ href: '/about', label: 'About' }
	];

	let menuOpen = $state(false);

	const active = (href: string) => page.url.pathname === href || page.url.pathname.startsWith(href + '/');
</script>

<a
	href="#main"
	class="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-panel-raised focus:px-3 focus:py-2"
>
	Skip to content
</a>

<header class="sticky top-0 z-40 border-b border-seam bg-panel/95 backdrop-blur">
	<div class="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
		<a href="/" class="flex items-center gap-2.5" aria-label="ASoundJob home">
			<div class="flex flex-col leading-none">
				<span class="text-lg font-black tracking-tight">ASoundJob</span>
				<span class="font-mono text-[10px] tracking-wide text-ink-soft">by Young Audio Professionals</span>
			</div>
			<img src="/yap-logo.png" alt="Young Audio Professionals logo" class="h-9 w-9 rounded-sm border border-seam object-cover" />
		</a>

		<nav aria-label="Primary" class="ml-auto hidden items-center gap-1 md:flex">
			{#each links as link (link.href)}
				<a
					href={link.href}
					aria-current={active(link.href) ? 'page' : undefined}
					class="btn-latch !shadow-none {active(link.href)
						? 'is-on'
						: '!bg-transparent !border-transparent'}"
				>
					{link.label}
				</a>
			{/each}
			{#if discord}
				<a
					href={discord}
					target="_blank"
					rel="noopener noreferrer"
					class="btn-latch !bg-transparent !border-transparent"
				>
					Discord
				</a>
			{/if}
			<a href="/jobs/submit" class="btn-primary ml-2">Submit a job</a>
		</nav>

		<button
			type="button"
			class="btn-latch ml-auto md:hidden"
			aria-expanded={menuOpen}
			aria-controls="mobile-nav"
			onclick={() => (menuOpen = !menuOpen)}
		>
			{menuOpen ? 'Close' : 'Menu'}
		</button>
	</div>

	{#if menuOpen}
		<nav id="mobile-nav" aria-label="Primary" class="border-t border-seam px-4 py-3 md:hidden">
			<ul class="flex flex-col gap-1">
				{#each [...links, ...(discord ? [{ href: discord, label: 'Discord ↗' }] : [])] as link (link.href)}
					<li>
						<a
							href={link.href}
							aria-current={active(link.href) ? 'page' : undefined}
							class="block rounded px-2 py-2 font-semibold {active(link.href)
								? 'bg-fader text-white'
								: ''}"
							onclick={() => (menuOpen = false)}
						>
							{link.label}
						</a>
					</li>
				{/each}
				<li class="pt-2">
					<a href="/jobs/submit" class="btn-primary w-full" onclick={() => (menuOpen = false)}>
						Submit a job
					</a>
				</li>
			</ul>
		</nav>
	{/if}
</header>
