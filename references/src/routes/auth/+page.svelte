<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { getSessionUser, userSignIn, userSignUp, updateUserTimezone } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest, getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { redirect } from '@sveltejs/kit';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = 'landing';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			// Update user timezone
			const timezone = getUserTimezone();
			if (sessionUser.token && timezone) {
				updateUserTimezone(sessionUser.token, timezone);
			}

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirect') || '/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const chooseAuthMode = async (nextMode: 'signin' | 'signup') => {
		mode = nextMode;
		await tick();
		document.getElementById(nextMode === 'signup' ? 'name' : 'email')?.focus();
	};

	const oauthCallbackHandler = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;

				darkImage.onload = () => {
					logo.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
				};
			}
		}
	}

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		if ($user !== undefined) {
			goto(redirectPath || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');
		if (form) {
			mode = form === 'signup' && $config?.features.enable_signup ? 'signup' : 'signin';
		}

		// Auto-redirect to SSO when OAUTH_AUTO_REDIRECT is enabled and the
		// deployment is unambiguously SSO-only (single provider, no login form).
		// Suppressed by ?form=, ?error=, onboarding, trusted-header auth,
		// or an existing session/token.
		if ($config?.oauth?.auto_redirect && !form && !error) {
			const providers = Object.keys($config?.oauth?.providers ?? {});
			if (
				providers.length === 1 &&
				$config?.features?.auth !== false &&
				$config?.features?.enable_login_form === false &&
				!$config?.features?.auth_trusted_header &&
				!$config?.onboarding &&
				!localStorage.token &&
				!document.cookie.split('; ').some((c) => c.startsWith('token='))
			) {
				window.location.href = `${WEBUI_BASE_URL}/oauth/${providers[0]}/login`;
				return;
			}
		}

		loaded = true;
		setLogoImage();

		if (($config?.features?.auth_trusted_header ?? false) || $config?.features?.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = 'signup';
	}}
/>

<div class="w-full min-h-[100dvh] text-white relative overflow-y-auto" id="auth-page">
	<div class="theme-paper-bg w-full h-full absolute top-0 left-0"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if loaded}
		<div
			class="relative bg-transparent min-h-[100dvh] w-full flex justify-center font-primary z-50 text-black dark:text-white"
			id="auth-container"
		>
			<div class="w-full min-h-[100dvh] flex flex-col text-center">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class=" my-auto pb-10 w-full sm:max-w-md">
						<div
							class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-medium dark:text-gray-200"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>

							<div>
								<Spinner className="size-5" />
							</div>
						</div>
					</div>
				{:else}
					<div class="auth-scene">
						<div class="auth-grid" aria-hidden="true"></div>

						<main class="auth-stage" aria-labelledby="auth-heading">
							<section class="auth-story">
								<div class="auth-brand">
									<div class="auth-logo-wrap">
										<div class="auth-logo-halo" aria-hidden="true"></div>
										<img
											id="logo"
											crossorigin="anonymous"
											src="{WEBUI_BASE_URL}/static/favicon.png"
											class="auth-logo dark:hidden"
											alt="{$WEBUI_NAME} logo"
										/>
										<img
											id="logo-dark"
											crossorigin="anonymous"
											src="{WEBUI_BASE_URL}/static/favicon-dark.png"
											class="auth-logo hidden dark:block"
											alt="{$WEBUI_NAME} logo"
										/>
									</div>
									<span>{$WEBUI_NAME}</span>
								</div>

								<div class="auth-story-copy">
									<p class="auth-kicker">{$i18n.t('Enterprise knowledge workspace')}</p>
									<h1 id="auth-heading">
										{$i18n.t('Turn company documents into trusted answers.')}
									</h1>
									<p class="auth-lede">
										{$i18n.t(
											'Find, summarize, and verify information across internal documents without moving company data outside your workspace.'
										)}
									</p>
								</div>

								<div class="auth-document-flow">
									<p>{$i18n.t('From source to answer')}</p>
									<ol>
										<li>
											<span>01</span>
											<div>
												<strong>{$i18n.t('Company documents')}</strong>
												<small>PDF · DOCX · XLSX</small>
											</div>
										</li>
										<li>
											<span>02</span>
											<div>
												<strong>{$i18n.t('Permission-aware knowledge')}</strong>
												<small>{$i18n.t('Indexed for the right team')}</small>
											</div>
										</li>
										<li>
											<span>03</span>
											<div>
												<strong>{$i18n.t('Answers with citations')}</strong>
												<small>{$i18n.t('Linked back to the source')}</small>
											</div>
										</li>
									</ol>
								</div>
							</section>

							<section class="auth-panel" aria-live="polite">
								{#if mode === 'landing'}
									<div class="auth-choice-view">
										<div class="auth-panel-heading">
											<p>{$i18n.t('Secure access')}</p>
											<h2>{$i18n.t('Access your document workspace')}</h2>
											<span>
												{$i18n.t(
													'Sign in with your company account or request access as a new team member.'
												)}
											</span>
										</div>

										<div class="auth-choices">
											<button
												type="button"
												class="auth-choice auth-choice-primary"
												on:click={() => chooseAuthMode('signin')}
											>
												<span class="auth-choice-icon" aria-hidden="true">
													<svg
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.7"
													>
														<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
														<path d="m10 17 5-5-5-5" />
														<path d="M15 12H3" />
													</svg>
												</span>
												<span class="auth-choice-copy">
													<strong>{$i18n.t('Sign in')}</strong>
													<small>{$i18n.t('Open your company workspace.')}</small>
												</span>
												<span class="auth-choice-arrow" aria-hidden="true">→</span>
											</button>

											{#if $config?.features.enable_signup && $config?.features.enable_login_form}
												<button
													type="button"
													class="auth-choice auth-choice-secondary"
													on:click={() => chooseAuthMode('signup')}
												>
													<span class="auth-choice-icon" aria-hidden="true">
														<svg
															viewBox="0 0 24 24"
															fill="none"
															stroke="currentColor"
															stroke-width="1.7"
														>
															<path d="M15 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
															<circle cx="8.5" cy="7" r="4" />
															<path d="M19 8v6M22 11h-6" />
														</svg>
													</span>
													<span class="auth-choice-copy">
														<strong>{$i18n.t('Create Account')}</strong>
														<small>{$i18n.t('Request access for a new team member.')}</small>
													</span>
													<span class="auth-choice-arrow" aria-hidden="true">→</span>
												</button>
											{/if}
										</div>

										<p class="auth-panel-note">
											{$i18n.t('New accounts require administrator approval.')}
										</p>
									</div>
								{:else}
									<div id="auth-login-card" class="auth-form-view w-full dark:text-gray-100">
										{#if !($config?.onboarding ?? false)}
											<button
												type="button"
												class="auth-back"
												on:click={() => {
													mode = 'landing';
												}}
											>
												<span aria-hidden="true">←</span>
												{$i18n.t('Back')}
											</button>
										{/if}
										<form
											class=" flex flex-col justify-center"
											on:submit={(e) => {
												e.preventDefault();
												submitHandler();
											}}
										>
											<div class="mb-1">
												<div class=" text-2xl font-medium">
													{#if $config?.onboarding ?? false}
														{$i18n.t(`Get started with {{WEBUI_NAME}}`, {
															WEBUI_NAME: $WEBUI_NAME
														})}
													{:else if mode === 'signin'}
														{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
													{:else}
														{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
													{/if}
												</div>

												{#if $config?.onboarding ?? false}
													<div class="mt-1 text-xs font-medium text-gray-600 dark:text-gray-500">
														ⓘ {$WEBUI_NAME}
														{$i18n.t(
															'does not make any external connections, and your data stays securely on your locally hosted server.'
														)}
													</div>
												{/if}
											</div>

											{#if $config?.features.enable_login_form || form}
												<div class="flex flex-col mt-4">
													{#if mode === 'signup'}
														<div class="mb-2">
															<label for="name" class="text-sm font-medium text-left mb-1 block"
																>{$i18n.t('Name')}</label
															>
															<input
																bind:value={name}
																type="text"
																id="name"
																class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
																autocomplete="name"
																placeholder={$i18n.t('Enter Your Full Name')}
																required
															/>
														</div>
													{/if}

													<div class="mb-2">
														<label for="email" class="text-sm font-medium text-left mb-1 block"
															>{$i18n.t('Email')}</label
														>
														<input
															bind:value={email}
															type="email"
															id="email"
															class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
															autocomplete="email"
															name="email"
															placeholder={$i18n.t('Enter Your Email')}
															required
														/>
													</div>

													<div>
														<label for="password" class="text-sm font-medium text-left mb-1 block"
															>{$i18n.t('Password')}</label
														>
														<SensitiveInput
															bind:value={password}
															type="password"
															id="password"
															class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
															placeholder={$i18n.t('Enter Your Password')}
															autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
															name="password"
															screenReader={true}
															required
															aria-required="true"
														/>
													</div>

													{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
														<div class="mt-2">
															<label
																for="confirm-password"
																class="text-sm font-medium text-left mb-1 block"
																>{$i18n.t('Confirm Password')}</label
															>
															<SensitiveInput
																bind:value={confirmPassword}
																type="password"
																id="confirm-password"
																class="my-0.5 w-full text-sm outline-hidden bg-transparent"
																placeholder={$i18n.t('Confirm Your Password')}
																autocomplete="new-password"
																name="confirm-password"
																required
															/>
														</div>
													{/if}
												</div>
											{/if}
											<div class="mt-5">
												{#if $config?.features.enable_login_form || form}
													<button
														class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
														type="submit"
													>
														{mode === 'signin'
															? $i18n.t('Sign in')
															: ($config?.onboarding ?? false)
																? $i18n.t('Create Admin Account')
																: $i18n.t('Create Account')}
													</button>

													{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
														<div class=" mt-4 text-sm text-center">
															{mode === 'signin'
																? $i18n.t("Don't have an account?")
																: $i18n.t('Already have an account?')}

															<button
																class=" font-medium underline"
																type="button"
																on:click={() => {
																	if (mode === 'signin') {
																		mode = 'signup';
																	} else {
																		mode = 'signin';
																	}
																}}
															>
																{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
															</button>
														</div>
													{/if}
												{/if}
											</div>
										</form>

										{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
											<div class="inline-flex items-center justify-center w-full">
												<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
												{#if $config?.features.enable_login_form || form}
													<span
														class="px-3 text-sm font-medium text-gray-900 dark:text-white bg-transparent"
														>{$i18n.t('or')}</span
													>
												{/if}

												<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
											</div>
											<div class="flex flex-col space-y-2">
												{#if $config?.oauth?.providers?.google}
													<button
														class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
														on:click={() => {
															window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 48 48"
															class="size-6 mr-3"
															aria-hidden="true"
														>
															<path
																fill="#EA4335"
																d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
															/><path
																fill="#4285F4"
																d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
															/><path
																fill="#FBBC05"
																d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
															/><path
																fill="#34A853"
																d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
															/><path fill="none" d="M0 0h48v48H0z" />
														</svg>
														<span
															>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span
														>
													</button>
												{/if}
												{#if $config?.oauth?.providers?.microsoft}
													<button
														class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
														on:click={() => {
															window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 21 21"
															class="size-6 mr-3"
															aria-hidden="true"
														>
															<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
																x="1"
																y="11"
																width="9"
																height="9"
																fill="#00a4ef"
															/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
																x="11"
																y="11"
																width="9"
																height="9"
																fill="#ffb900"
															/>
														</svg>
														<span
															>{$i18n.t('Continue with {{provider}}', {
																provider: 'Microsoft'
															})}</span
														>
													</button>
												{/if}
												{#if $config?.oauth?.providers?.github}
													<button
														class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
														on:click={() => {
															window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 24 24"
															class="size-6 mr-3"
															aria-hidden="true"
														>
															<path
																fill="currentColor"
																d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
															/>
														</svg>
														<span
															>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span
														>
													</button>
												{/if}
												{#if $config?.oauth?.providers?.oidc}
													<button
														class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
														on:click={() => {
															window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															fill="none"
															viewBox="0 0 24 24"
															stroke-width="1.5"
															stroke="currentColor"
															class="size-6 mr-3"
															aria-hidden="true"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
															/>
														</svg>

														<span
															>{$i18n.t('Continue with {{provider}}', {
																provider: $config?.oauth?.providers?.oidc ?? 'SSO'
															})}</span
														>
													</button>
												{/if}
												{#if $config?.oauth?.providers?.feishu}
													<button
														class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
														on:click={() => {
															window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
														}}
													>
														<span
															>{$i18n.t('Continue with {{provider}}', { provider: 'Feishu' })}</span
														>
													</button>
												{/if}
											</div>
										{/if}
									</div>
								{/if}
							</section>
						</main>

						{#if $config?.metadata?.login_footer}
							<div class="auth-footer max-w-3xl mx-auto">
								<div class="text-[0.7rem] text-gray-500 dark:text-gray-400 marked">
									{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<!--
	LEGACY LDAP CODE — intentionally disabled and kept for reference.

	SCRIPT

	import { ldapUserSignIn } from '$lib/apis/auths';

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';
	let ldapUsername = '';

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	// Onboarding mode:
	mode = $config?.features.enable_ldap ? 'ldap' : 'signup';

	// OAuth auto-redirect guard:
	!$config?.features?.enable_ldap;

	TEMPLATE

	{:else if mode === 'ldap'}
		{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, { WEBUI_NAME: $WEBUI_NAME })}

	{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}

	{#if mode === 'ldap'}
		<div class="mb-2">
			<label for="username">{$i18n.t('Username')}</label>
			<input
				bind:value={ldapUsername}
				type="text"
				autocomplete="username"
				name="username"
				id="username"
				placeholder={$i18n.t('Enter Your Username')}
				required
			/>
		</div>
	{:else}
		ACTIVE EMAIL FIELD
	{/if}

	{#if mode === 'ldap'}
		<button type="submit">{$i18n.t('Authenticate')}</button>
	{:else}
		ACTIVE LOCAL SIGN-IN/SIGN-UP BUTTON
	{/if}

	{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
		<div class="mt-2">
			<button
				type="button"
				on:click={() => {
					if (mode === 'ldap')
						mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
					else mode = 'ldap';
				}}
			>
				<span>
					{mode === 'ldap'
						? $i18n.t('Continue with Email')
						: $i18n.t('Continue with LDAP')}
				</span>
			</button>
		</div>
	{/if}
-->

<style>
	.auth-scene {
		--auth-accent: #2563eb;
		--auth-accent-strong: #1d4ed8;
		--auth-ink: #0f172a;
		--auth-muted: #475569;
		--auth-surface: #f8fafc;
		--auth-panel: #ffffff;
		--auth-border: #cbd5e1;
		--auth-shadow: rgba(15, 23, 42, 0.2);
		--auth-story-ink: #f8fafc;
		--auth-story-muted: #cbd5e1;
		position: relative;
		isolation: isolate;
		display: flex;
		box-sizing: border-box;
		min-height: 100dvh;
		width: 100%;
		align-items: center;
		justify-content: center;
		overflow-x: hidden;
		overflow-y: auto;
		padding: clamp(1rem, 3vw, 2.5rem);
		background:
			radial-gradient(circle at 12% 12%, rgba(37, 99, 235, 0.13), transparent 27%),
			linear-gradient(135deg, #e8eef6 0%, #f8fafc 52%, #e7edf5 100%);
		color: var(--auth-ink);
	}

	:global(.dark) .auth-scene {
		--auth-accent: #60a5fa;
		--auth-accent-strong: #93c5fd;
		--auth-ink: #f8fafc;
		--auth-muted: #94a3b8;
		--auth-surface: #0b1627;
		--auth-panel: #0f1b2d;
		--auth-border: rgba(148, 163, 184, 0.24);
		--auth-shadow: rgba(2, 6, 23, 0.58);
		background:
			radial-gradient(circle at 12% 12%, rgba(37, 99, 235, 0.18), transparent 27%),
			linear-gradient(135deg, #07111f 0%, #0f172a 56%, #0a1424 100%);
	}

	.auth-grid {
		position: absolute;
		inset: 0;
		z-index: -3;
		background-image:
			linear-gradient(rgba(37, 99, 235, 0.05) 1px, transparent 1px),
			linear-gradient(90deg, rgba(37, 99, 235, 0.05) 1px, transparent 1px);
		background-size: 64px 64px;
		mask-image: radial-gradient(circle at center, black 8%, transparent 76%);
	}

	.auth-stage {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1.08fr) minmax(24rem, 0.92fr);
		box-sizing: border-box;
		width: min(74rem, 100%);
		min-height: min(43rem, calc(100dvh - 5rem));
		overflow: hidden;
		border: 1px solid var(--auth-border);
		border-radius: 1.25rem;
		background: var(--auth-surface);
		box-shadow:
			0 2rem 5rem -2rem var(--auth-shadow),
			0 0.25rem 1rem rgba(15, 23, 42, 0.08);
		text-align: left;
	}

	.auth-story {
		position: relative;
		display: flex;
		box-sizing: border-box;
		min-width: 0;
		flex-direction: column;
		justify-content: space-between;
		overflow: hidden;
		padding: clamp(2rem, 5vw, 4.5rem);
		background:
			radial-gradient(circle at 16% 12%, rgba(96, 165, 250, 0.2), transparent 30%),
			linear-gradient(150deg, #0b2340 0%, #102f55 64%, #0a1e37 100%);
		border-right: 1px solid var(--auth-border);
		color: var(--auth-story-ink);
	}

	:global(.dark) .auth-story {
		background:
			radial-gradient(circle at 16% 12%, rgba(96, 165, 250, 0.2), transparent 30%),
			linear-gradient(150deg, #0c2545 0%, #12345d 64%, #091d35 100%);
	}

	.auth-story::after {
		position: absolute;
		right: -4.5rem;
		bottom: -7rem;
		width: 18rem;
		height: 24rem;
		border: 1px solid rgba(147, 197, 253, 0.2);
		border-radius: 1.25rem;
		content: '';
		transform: rotate(-9deg);
		box-shadow:
			-2rem -2rem 0 rgba(147, 197, 253, 0.035),
			-4rem -4rem 0 rgba(147, 197, 253, 0.025);
	}

	.auth-brand,
	.auth-logo-wrap,
	.auth-choice {
		display: flex;
		align-items: center;
	}

	.auth-brand {
		position: relative;
		z-index: 1;
		gap: 0.8rem;
		font-size: 0.95rem;
		font-weight: 600;
		letter-spacing: -0.02em;
		color: var(--auth-story-ink);
	}

	.auth-logo-wrap {
		position: relative;
		width: 2.75rem;
		height: 2.75rem;
		justify-content: center;
		border: 1px solid rgba(191, 219, 254, 0.24);
		border-radius: 0.8rem;
		background: rgba(255, 255, 255, 0.07);
	}

	.auth-logo-halo {
		position: absolute;
		inset: -0.25rem;
		border: 1px solid rgba(147, 197, 253, 0.18);
		border-radius: 1rem;
	}

	.auth-logo {
		position: relative;
		width: 2.25rem;
		height: 2.25rem;
		border-radius: 0.55rem;
		object-fit: cover;
		box-shadow: 0 0.6rem 1.8rem -0.9rem var(--auth-shadow);
	}

	.auth-story-copy {
		position: relative;
		z-index: 1;
		max-width: 35rem;
		margin-block: 3rem;
	}

	.auth-kicker,
	.auth-panel-heading > p {
		margin: 0 0 1rem;
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.14em;
		text-transform: uppercase;
	}

	.auth-kicker {
		color: #93c5fd;
	}

	.auth-panel-heading > p {
		color: var(--auth-accent);
	}

	.auth-story h1 {
		max-width: 13ch;
		margin: 0;
		font-family: 'Archivo', 'Vazirmatn', sans-serif;
		font-size: clamp(2.8rem, 4.8vw, 4.65rem);
		font-weight: 650;
		letter-spacing: -0.055em;
		line-height: 0.98;
		text-wrap: balance;
	}

	.auth-lede {
		max-width: 31rem;
		margin: 1.5rem 0 0;
		color: var(--auth-story-muted);
		font-size: 1rem;
		line-height: 1.7;
		text-wrap: pretty;
	}

	.auth-document-flow {
		position: relative;
		z-index: 1;
		max-width: 32rem;
		padding-top: 1.4rem;
		border-top: 1px solid rgba(191, 219, 254, 0.2);
	}

	.auth-document-flow > p {
		margin: 0 0 0.85rem;
		color: #93c5fd;
		font-size: 0.68rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}

	.auth-document-flow ol {
		display: grid;
		gap: 0.7rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.auth-document-flow li {
		display: grid;
		grid-template-columns: 2rem minmax(0, 1fr);
		gap: 0.7rem;
		align-items: center;
	}

	.auth-document-flow li > span {
		color: #93c5fd;
		font-size: 0.72rem;
		font-variant-numeric: tabular-nums;
		font-weight: 700;
		letter-spacing: 0.06em;
	}

	.auth-document-flow li div {
		display: grid;
		gap: 0.1rem;
		min-width: 0;
	}

	.auth-document-flow strong {
		color: var(--auth-story-ink);
		font-size: 0.8rem;
		font-weight: 600;
	}

	.auth-document-flow small {
		color: var(--auth-story-muted);
		font-size: 0.7rem;
	}

	.auth-panel {
		display: flex;
		box-sizing: border-box;
		min-width: 0;
		max-width: 100%;
		align-items: center;
		justify-content: center;
		overflow-y: auto;
		padding: clamp(2rem, 4vw, 3.75rem);
		background: var(--auth-panel);
	}

	.auth-choice-view,
	.auth-form-view {
		width: 100%;
		max-width: 25rem;
		min-width: 0;
		margin: auto;
	}

	.auth-panel-heading h2 {
		margin: 0;
		color: var(--auth-ink);
		font-size: clamp(1.85rem, 3vw, 2.55rem);
		font-weight: 600;
		letter-spacing: -0.045em;
		line-height: 1.08;
		overflow-wrap: anywhere;
		text-wrap: balance;
	}

	.auth-panel-heading > span {
		display: block;
		margin-top: 0.9rem;
		color: var(--auth-muted);
		font-size: 0.88rem;
		line-height: 1.55;
	}

	.auth-choices {
		display: grid;
		gap: 0.8rem;
		margin-top: 2rem;
	}

	.auth-choice {
		position: relative;
		width: 100%;
		min-height: 5.25rem;
		gap: 0.9rem;
		border: 1px solid var(--auth-border);
		border-radius: 1.15rem;
		padding: 1rem;
		text-align: left;
		box-sizing: border-box;
		transition:
			transform 220ms ease,
			border-color 220ms ease,
			background-color 220ms ease,
			box-shadow 220ms ease;
	}

	.auth-choice:hover {
		transform: translateY(-2px);
		box-shadow: 0 1.2rem 2.4rem -1.7rem var(--auth-shadow);
	}

	.auth-choice:active {
		transform: scale(0.985);
	}

	.auth-choice:focus-visible,
	.auth-back:focus-visible {
		outline: 3px solid color-mix(in srgb, var(--auth-accent) 36%, transparent);
		outline-offset: 3px;
	}

	.auth-choice-primary {
		border-color: #2563eb;
		background: #2563eb;
		color: #fff;
	}

	:global(.dark) .auth-choice-primary {
		border-color: #3b82f6;
		background: #2563eb;
		color: #ffffff;
	}

	.auth-choice-secondary {
		background: color-mix(in srgb, var(--auth-panel) 88%, var(--auth-surface));
		color: var(--auth-ink);
	}

	.auth-choice-secondary:hover {
		border-color: color-mix(in srgb, var(--auth-accent) 40%, transparent);
		background: color-mix(in srgb, var(--auth-accent) 7%, var(--auth-surface));
	}

	.auth-choice-icon {
		display: grid;
		width: 2.7rem;
		height: 2.7rem;
		flex: none;
		place-items: center;
		border-radius: 0.8rem;
		background: rgba(255, 255, 255, 0.11);
	}

	.auth-choice-secondary .auth-choice-icon {
		background: color-mix(in srgb, var(--auth-accent) 10%, transparent);
		color: var(--auth-accent-strong);
	}

	.auth-choice-icon svg {
		width: 1.35rem;
		height: 1.35rem;
	}

	.auth-choice-copy {
		display: grid;
		min-width: 0;
		flex: 1;
		gap: 0.2rem;
	}

	.auth-choice-copy strong {
		font-size: 0.95rem;
		font-weight: 650;
	}

	.auth-choice-copy small {
		color: currentColor;
		font-size: 0.76rem;
		line-height: 1.35;
		opacity: 0.68;
	}

	.auth-choice-arrow {
		font-size: 1.2rem;
		transition: transform 220ms ease;
	}

	.auth-choice:hover .auth-choice-arrow {
		transform: translateX(0.22rem);
	}

	.auth-panel-note {
		margin: 1.5rem 0 0;
		color: var(--auth-muted);
		font-size: 0.72rem;
		text-align: center;
	}

	.auth-back {
		display: inline-flex;
		min-height: 2.75rem;
		align-items: center;
		gap: 0.45rem;
		margin: -0.6rem 0 1.25rem;
		border-radius: 0.65rem;
		padding: 0 0.6rem;
		color: var(--auth-muted);
		font-size: 0.78rem;
		font-weight: 600;
		transition:
			color 180ms ease,
			background-color 180ms ease;
	}

	.auth-back:hover {
		background: color-mix(in srgb, var(--auth-accent) 8%, transparent);
		color: var(--auth-ink);
	}

	.auth-form-view :global(input) {
		min-height: 2.8rem;
		border-bottom: 1px solid var(--auth-border);
		color: var(--auth-ink);
		transition:
			border-color 180ms ease,
			box-shadow 180ms ease;
	}

	.auth-form-view :global(input:focus) {
		border-color: var(--auth-accent);
		box-shadow: 0 1px 0 var(--auth-accent);
	}

	.auth-form-view :global(label) {
		color: var(--auth-ink);
	}

	.auth-form-view :global(button[type='submit']) {
		min-height: 2.9rem;
		border-radius: 0.75rem;
		background: #2563eb;
		color: #ffffff;
		transition:
			background-color 180ms ease,
			transform 180ms ease;
	}

	.auth-form-view :global(button[type='submit']:hover) {
		background: #1d4ed8;
	}

	.auth-form-view :global(button[type='submit']:active) {
		transform: scale(0.985);
	}

	.auth-form-view :global(button:focus-visible) {
		outline: 3px solid color-mix(in srgb, var(--auth-accent) 36%, transparent);
		outline-offset: 3px;
	}

	.auth-footer {
		position: relative;
		z-index: 1;
		margin-top: 1rem;
		padding-inline: 1rem;
		text-align: center;
	}

	@media (min-width: 861px) and (max-height: 820px) {
		.auth-scene {
			padding: 1rem;
		}

		.auth-stage {
			min-height: calc(100dvh - 2rem);
		}

		.auth-story {
			padding: 2.5rem clamp(2.5rem, 4vw, 3.5rem);
		}

		.auth-story-copy {
			margin-block: 1.5rem;
		}

		.auth-story h1 {
			font-size: clamp(2.8rem, 4.4vw, 3.8rem);
		}

		.auth-lede {
			margin-top: 1rem;
			line-height: 1.55;
		}

		.auth-document-flow {
			padding-top: 1rem;
		}

		.auth-document-flow ol {
			gap: 0.45rem;
		}

		.auth-panel {
			padding: 2.5rem;
		}
	}

	@media (max-width: 860px) {
		.auth-scene {
			align-items: stretch;
			justify-content: flex-start;
			overflow: visible;
			padding: 0.75rem;
		}

		.auth-stage {
			grid-template-columns: minmax(0, 1fr);
			width: 100%;
			max-width: 100%;
			min-height: calc(100dvh - 1.5rem);
			max-height: none;
			border-radius: 1rem;
		}

		.auth-story {
			min-height: 17rem;
			padding: 1.75rem;
			border-right: 0;
			border-bottom: 1px solid var(--auth-border);
		}

		.auth-story-copy {
			margin: 3.25rem 0 0.75rem;
		}

		.auth-story h1 {
			max-width: 15ch;
			font-size: clamp(2.5rem, 10vw, 3.7rem);
		}

		.auth-lede {
			width: 100%;
			max-width: 34rem;
			margin-top: 1.1rem;
			font-size: 0.9rem;
			overflow-wrap: anywhere;
		}

		.auth-document-flow {
			display: none;
		}

		.auth-panel {
			overflow: visible;
			padding: 2.5rem 1.4rem 3rem;
		}
	}

	@media (max-width: 430px) {
		.auth-story {
			min-height: 14.5rem;
			padding: 1.35rem;
		}

		.auth-story-copy {
			margin-top: 2.7rem;
		}

		.auth-story h1 {
			font-size: clamp(2.2rem, 10.5vw, 2.8rem);
		}

		.auth-lede {
			display: none;
		}

		.auth-panel {
			padding: 2.15rem 1rem 2.5rem;
		}

		.auth-panel-heading h2 {
			font-size: 1.65rem;
		}

		.auth-choice {
			min-height: 5rem;
			padding: 0.85rem;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.auth-choice,
		.auth-choice-arrow,
		.auth-form-view :global(button[type='submit']) {
			transition-duration: 0.01ms;
		}
	}
</style>
