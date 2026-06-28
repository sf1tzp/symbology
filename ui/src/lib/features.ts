/**
 * Runtime feature gates, read from `$env/dynamic/public` so they can be flipped
 * by deploy-time env without a rebuild (and stay readable from both server and
 * client code).
 */
import { env } from '$env/dynamic/public';

/**
 * Whether the supporter / payments surface is live. Payments aren't launched
 * yet, so the /support page, its Stripe checkout action, and every nav
 * affordance that points at it stay hidden until `PUBLIC_SUPPORT_ENABLED` is
 * explicitly set to `"true"`.
 */
export const supportEnabled = env.PUBLIC_SUPPORT_ENABLED === 'true';
