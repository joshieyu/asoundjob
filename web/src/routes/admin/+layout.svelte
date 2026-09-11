<script lang="ts">
	import { page } from '$app/state';
	import { clientApi, getToken, setToken } from '$lib/client';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	let token = $state<string | null>(null);
	let username = $state('');
	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	$effect(() => {
		token = getToken();
	});

	const isActive = (href: string) => page.url.pathname === href;

	async function login(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		busy = true;
		try {
			const result = await clientApi<{ access_token: string }>('/api/admin/login', {
				method: 'POST',
				body: { username, password }
			});
			setToken(result.access_token);
			token = result.access_token;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Login failed';
		} finally {
			busy = false;
		}
	}

	const sections = [
		['/admin', 'Dashboard'],
		['/admin/submissions', 'Submissions'],
		['/admin/feedback', 'Feedback'],
		['/admin/scraper', 'Scraper'],
		['/admin/companies', 'Companies']
	] as const;
</script>

<svelte:head>
	<meta name="robots" content="noindex" />
	<title>Admin | ASoundJob</title>
</svelte:head>

{#if !token}
	<div class="mx-auto mt-16 max-w-sm">
		<form class="space-y-6" onsubmit={login}>
			<div class="space-y-1">
				<h1 class="text-title font-semibold">Admin sign in</h1>
				<p class="text-meta text-muted">Admin sign-in for the ASoundJob backend.</p>
			</div>
			<label class="block">
				<span class="axis-label mb-1 block">Username</span>
				<input bind:value={username} autocomplete="username" class="field h-10" required />
			</label>
			<label class="block">
				<span class="axis-label mb-1 block">Password</span>
				<input type="password" bind:value={password} autocomplete="current-password" class="field h-10" required />
			</label>
			{#if error}<p class="text-meta font-semibold text-ink" role="alert">{error}</p>{/if}
			<button type="submit" disabled={busy} class="btn btn-primary w-full">
				{busy ? 'Checking…' : 'Sign in'}
			</button>
		</form>
	</div>
{:else}
	<nav aria-label="Admin sections" class="mt-6 flex flex-wrap items-center gap-1.5">
		{#each sections as [href, label] (href)}
			<a
				href={href}
				class="btn btn-quiet"
				class:is-on={isActive(href)}
				class:underline={isActive(href)}
				class:underline-offset-4={isActive(href)}
				aria-current={isActive(href) ? 'page' : undefined}
			>
				{label}
			</a>
		{/each}
		<button
			type="button"
			class="btn btn-quiet ml-auto"
			onclick={() => {
				setToken(null);
				token = null;
			}}
		>
			Sign out
		</button>
	</nav>
	{@render children()}
{/if}
