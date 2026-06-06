import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { cleanContent } from '$lib/utils/filings';

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

export function toTitleCase(str: string) {
	return str
		.replace(/[\s\p{P}]+$/u, '')
		.toLowerCase()
		.split(' ')
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ');
}

/** First few sentences of the intro, cleaned of markdown/footnote noise. */
export function previewContent(text: string | null, length: number = 3): string {
	const cleaned = cleanContent(text ?? '') ?? '';
	const sentences = cleaned.match(/[^.!?]+[.!?]+/g);
	if (!sentences) return cleaned.substring(0, 320);
	return sentences.slice(0, length).join('').trim();
}
