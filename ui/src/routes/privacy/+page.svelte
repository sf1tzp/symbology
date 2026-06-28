<script lang="ts">
	import SectionHead from '$lib/components/SectionHead.svelte';
	import { ChevronLeft } from '@lucide/svelte';

	const lastUpdated = 'June 28, 2026';
</script>

<svelte:head>
	<title>Privacy Policy - Symbology</title>
	<meta name="description" content="How Symbology collects, uses, and protects your data." />
</svelte:head>

<!-- Back link -->
<div class="hidden md:block" style="margin-bottom: 3rem;">
	<a
		href="/"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		Home
	</a>
</div>

<!-- Masthead -->
<header style="max-width: 720px;">
	<div class="eyebrow" style="margin-bottom: 1rem;">
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;LEGAL
	</div>
	<h1 class="display" style="margin-bottom: 1rem;">Privacy Policy</h1>
	<p class="lede" style="color: var(--ink-2); max-width: 52ch;">
		What we collect, why we collect it, and the choices you have.
	</p>
	<p class="meta" style="color: var(--ink-3); margin-top: 1rem;">Last updated: {lastUpdated}</p>
</header>

<!-- Content -->
<article style="margin-top: 5rem;">
	<div class="analysis-body">
		<section>
			<SectionHead sticky stickyHeading eyebrow="Privacy Policy" heading="Who we are" />
			<p>
				Symbology is operated by Streetfortress Industries, LLC ("we", "us", or "our"). This policy
				explains how we handle personal data when you use the Service. For data-protection purposes,
				Streetfortress Industries, LLC is the data controller.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead sticky stickyHeading eyebrow="Privacy Policy" heading="Information we collect" />
			<p>We collect only what we need to run the Service:</p>
			<ul style="margin: 1rem 0; padding-left: 1.5rem; list-style: disc; color: var(--ink-2);">
				<li style="margin-bottom: 0.75rem;">
					<strong style="color: var(--ink);">Account information</strong> — your name, email address,
					and a securely hashed password. We never store your password in plain text. We also record whether
					your email has been verified and any profile preferences you set.
				</li>
				<li style="margin-bottom: 0.75rem;">
					<strong style="color: var(--ink);">Usage data you create</strong> — the companies you add to
					your watchlist and similar in-app activity.
				</li>
				<li style="margin-bottom: 0.75rem;">
					<strong style="color: var(--ink);">Payment records</strong> — if you make a supporter contribution,
					our payment processor (Stripe) handles your card details; we never see or store your full card
					number. We retain a record of the contribution (amount, the period granted, and the Stripe transaction
					identifier).
				</li>
				<li style="margin-bottom: 0.75rem;">
					<strong style="color: var(--ink);">Session &amp; technical data</strong> — session tokens needed
					to keep you logged in, and standard technical information (such as your IP address and browser
					type) processed by our hosting infrastructure to deliver and secure the Service.
				</li>
				<li style="margin-bottom: 0.75rem;">
					<strong style="color: var(--ink);">Analytics</strong> — privacy-friendly, aggregate usage statistics
					(such as page views) collected through our self-hosted Umami analytics, which does not use tracking
					cookies or build advertising profiles.
				</li>
			</ul>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Privacy Policy"
				heading="How we use your information"
			/>
			<ul style="margin: 1rem 0; padding-left: 1.5rem; list-style: disc; color: var(--ink-2);">
				<li style="margin-bottom: 0.5rem;">to create and operate your account;</li>
				<li style="margin-bottom: 0.5rem;">
					to provide core features such as your watchlist and supporter access;
				</li>
				<li style="margin-bottom: 0.5rem;">
					to send transactional emails — verification, password reset, and welcome messages;
				</li>
				<li style="margin-bottom: 0.5rem;">to process and record supporter contributions;</li>
				<li style="margin-bottom: 0.5rem;">
					to secure the Service, prevent abuse, and meet legal obligations;
				</li>
				<li style="margin-bottom: 0.5rem;">
					to understand aggregate usage so we can improve the Service.
				</li>
			</ul>
			<p>
				We do <strong style="color: var(--ink);">not</strong> sell your personal data, and we do not use
				it for third-party advertising.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Privacy Policy"
				heading="Legal bases (EU/UK users)"
			/>
			<p>
				If you are in the European Economic Area or the United Kingdom, we process your personal
				data on the following legal bases: <strong style="color: var(--ink);">contract</strong> (to
				provide the account and features you request),
				<strong style="color: var(--ink);">legitimate interests</strong>
				(to secure, maintain, and improve the Service),
				<strong style="color: var(--ink);">legal obligation</strong>
				(for example, retaining payment records), and
				<strong style="color: var(--ink);">consent</strong>
				where required.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Privacy Policy"
				heading="How we share information"
			/>
			<p>
				We share personal data only with service providers that help us run the Service, and only as
				needed:
			</p>
			<ul style="margin: 1rem 0; padding-left: 1.5rem; list-style: disc; color: var(--ink-2);">
				<li style="margin-bottom: 0.5rem;">
					<strong style="color: var(--ink);">Stripe</strong> — payment processing. Receives your email
					and contribution details.
				</li>
				<li style="margin-bottom: 0.5rem;">
					<strong style="color: var(--ink);">Resend</strong> — delivery of transactional email. Receives
					your email address.
				</li>
				<li style="margin-bottom: 0.5rem;">
					<strong style="color: var(--ink);">Hosting &amp; infrastructure providers</strong> — process
					data on our behalf to operate the Service.
				</li>
				<li style="margin-bottom: 0.5rem;">
					<strong style="color: var(--ink);">Google Fonts</strong> — serving web fonts may expose your
					IP address to Google as part of standard delivery.
				</li>
			</ul>
			<p>
				We may also disclose information when required by law, to enforce our Terms, or to protect
				the rights, safety, and property of Symbology, our users, or others. If we are involved in a
				merger, acquisition, or asset sale, personal data may be transferred as part of that
				transaction.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead sticky stickyHeading eyebrow="Privacy Policy" heading="Cookies" />
			<p>
				We use a small number of strictly necessary cookies to keep you signed in and to operate the
				Service. Our analytics are cookieless. We do not use advertising or cross-site tracking
				cookies.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead sticky stickyHeading eyebrow="Privacy Policy" heading="Data retention" />
			<p>
				We keep your personal data for as long as your account is active or as needed to provide the
				Service. When you delete your account, we delete or anonymize your personal data within a
				reasonable period, except where we must retain certain records (such as payment and tax
				records) to comply with legal obligations.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead sticky stickyHeading eyebrow="Privacy Policy" heading="Security" />
			<p>
				We use reasonable technical and organizational measures to protect your data, including
				password hashing and encrypted connections. No method of transmission or storage is
				perfectly secure, so we cannot guarantee absolute security.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead sticky stickyHeading eyebrow="Privacy Policy" heading="Your rights (EU/UK)" />
			<p>
				Depending on where you live, you may have the right to access, correct, delete, or receive a
				copy of your personal data; to restrict or object to certain processing; and to withdraw
				consent. To exercise these rights, contact us using the details below. You also have the
				right to lodge a complaint with your local data-protection supervisory authority.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Privacy Policy"
				heading="Your rights (California)"
			/>
			<p>
				If you are a California resident, you have the right to know what personal information we
				collect and how we use it, to request deletion of your personal information, and to not be
				discriminated against for exercising these rights. We do not sell or share your personal
				information as those terms are defined under California law. To make a request, contact us
				using the details below.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Privacy Policy"
				heading="International transfers"
			/>
			<p>
				We and our service providers may process your data in the United States and other countries.
				Where required, we rely on appropriate safeguards (such as standard contractual clauses) for
				international transfers of personal data.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead sticky stickyHeading eyebrow="Privacy Policy" heading="Children's privacy" />
			<p>
				The Service is not directed to children under 16, and we do not knowingly collect personal
				data from them. If you believe a child has provided us personal data, please contact us and
				we will delete it.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead sticky stickyHeading eyebrow="Privacy Policy" heading="Changes to this policy" />
			<p>
				We may update this Privacy Policy from time to time. When we do, we will revise the "Last
				updated" date above and, where appropriate, provide additional notice.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead sticky stickyHeading eyebrow="Privacy Policy" heading="Contact" />
			<p>
				For privacy questions or to exercise your rights, contact us at
				<a
					href="mailto:support@streetfortress.com"
					style="color: var(--teal-2); text-decoration: underline; text-underline-offset: 3px;"
					>support@streetfortress.com</a
				>.
			</p>
		</section>
	</div>

	<div class="meta mt-6 flex justify-start border-t pt-6 text-ink-3 md:justify-end">
		<p>
			See also our
			<a href="/terms" style="color: var(--teal-2); text-decoration: none;">Terms of Service</a>.
		</p>
	</div>
</article>
