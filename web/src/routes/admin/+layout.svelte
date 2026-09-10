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
		<form class="panel space-y-4 p-6" onsubmit={login}>
			<h1 class="legend">CONSOLE ACCESS</h1>
			<p class="text-sm text-ink-soft">Admin sign-in for the ASoundJob backend.</p>
			<label class="block">
				<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] uppercase">Username</span>
				<input bind:value={username} autocomplete="username" class="well h-10 w-full px-3 text-sm" required />
			</label>
			<label class="block">
				<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] uppercase">Password</span>
				<input type="password" bind:value={password} autocomplete="current-password" class="well h-10 w-full px-3 text-sm" required />
			</label>
			{#if error}<p class="text-sm font-semibold text-fader-deep" role="alert">{error}</p>{/if}
			<button type="submit" disabled={busy} class="btn-primary w-full disabled:opacity-60">
				{busy ? 'Checking…' : 'Sign in'}
			</button>
		</form>
	</div>
{:else}
	<nav aria-label="Admin sections" class="mt-6 flex flex-wrap gap-1.5">
		{#each sections as [href, label] (href)}
			<a href={href} class="btn-latch !normal-case !tracking-normal" aria-current={isActive(href) ? 'page' : undefined}>
				{label}
			</a>
		{/each}
		<button
			type="button"
			class="btn-latch ml-auto"
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
