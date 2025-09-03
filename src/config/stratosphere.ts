export const ENV: string = (import.meta.env.PUBLIC_ENV as string) || (import.meta.env.MODE === 'development' ? 'dev' : 'pro');
export const STRATOSPHERE_ENABLED: boolean = !!(import.meta.env.PUBLIC_STRATOSPHERE_ENABLED ?? true);

