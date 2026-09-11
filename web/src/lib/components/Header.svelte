<script lang="ts">
	import { page } from '$app/state';
	import discordLink from '$lib/data/discord-link.txt?raw';
	import ThemeToggle from './ThemeToggle.svelte';

	const discord = discordLink.trim();
	const links = [
		{ href: '/jobs', label: 'Jobs' },
		{ href: '/companies', label: 'Companies' },
		{ href: '/resources', label: 'Resources' },
		{ href: '/about', label: 'About' }
	];

	let menuOpen = $state(false);

	const active = (href: string) =>
		page.url.pathname === href || page.url.pathname.startsWith(href + '/');

	$effect(() => {
		page.url.pathname;
		menuOpen = false;
	});
</script>

<a
	href="#main"
	class="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-ground focus:px-3 focus:py-2 focus:outline focus:outline-2 focus:outline-accent"
>
	Skip to content
</a>

<header class="sticky top-0 z-40 border-b border-rule bg-ground/95 backdrop-blur">
	<div class="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
		<a href="/" class="flex flex-col leading-none" aria-label="ASoundJob home">
			<span class="text-title font-bold tracking-tight">ASoundJob</span>
			<span class="coord mt-0.5 text-muted">by Young Audio Professionals</span>
		</a>

		<nav aria-label="Primary" class="ml-auto hidden items-center gap-5 md:flex">
			{#each links as link (link.href)}
				<a
					href={link.href}
					aria-current={active(link.href) ? 'page' : undefined}
					class="text-meta font-semibold transition-colors hover:text-accent {active(link.href) ? 'text-ink underline decoration-2 underline-offset-[6px]'
						: 'text-muted'}"
				>
					{link.label}
				</a>
			{/each}
			{#if discord}
				<a
					href={discord}
					target="_blank"
					rel="noopener noreferrer"
					class="text-meta font-semibold text-muted transition-colors hover:text-accent"
				>
					Discord<span class="sr-only"> (opens in a new tab)</span>
				</a>
			{/if}
			<ThemeToggle />
			<a href="/jobs/submit" class="btn btn-primary">Submit a job</a>
		</nav>

		<div class="ml-auto flex items-center gap-2 md:hidden">
			<ThemeToggle />
			<button
			type="button"
			class="btn btn-quiet"
			aria-expanded={menuOpen}
			aria-controls="mobile-nav"
			onclick={() => (menuOpen = !menuOpen)}
		>
			{menuOpen ? 'Close' : 'Menu'}
			</button>
		</div>
	</div>

	<nav
		id="mobile-nav"
		aria-label="Primary, mobile"
		class="border-t border-rule px-4 py-3 md:hidden"
		hidden={!menuOpen}
	>
		<ul class="flex flex-col">
			{#each links as link (link.href)}
				<li>
					<a
						href={link.href}
						aria-current={active(link.href) ? 'page' : undefined}
						class="block py-2.5 font-semibold {active(link.href) ? 'text-ink underline decoration-2 underline-offset-4'
							: 'text-muted'}"
					>
						{link.label}
					</a>
				</li>
			{/each}
			{#if discord}
				<li>
					<a
						href={discord}
						target="_blank"
						rel="noopener noreferrer"
						class="block py-2.5 font-semibold text-muted"
					>
						Discord<span class="sr-only"> (opens in a new tab)</span>
					</a>
				</li>
			{/if}
			<li class="pt-3">
				<a href="/jobs/submit" class="btn btn-primary w-full">Submit a job</a>
			</li>
		</ul>
	</nav>
</header>
