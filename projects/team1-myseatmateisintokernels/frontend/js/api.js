import { API_BASE } from './constants.js';

let _sessionBootstrapped = false;

export function resetSessionBootstrapFlag () {
	_sessionBootstrapped = false;
}

export function setSessionBootstrapped () {
	_sessionBootstrapped = true;
}

export function isSessionBootstrapped () {
	return _sessionBootstrapped;
}

export async function bootstrapSessionOnce (playerName) {
	if (_sessionBootstrapped) return;
	try {
		const meRes = await fetch (`${API_BASE}/sessions/me`, { credentials: 'include' });
		const meJson = meRes.ok ? await meRes.json () : null;
		const hasSession = !!(meJson?.data?.has_session);
		if (!hasSession) {
			await fetch (`${API_BASE}/sessions`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify ({ force_reset: false })
			});
		}
		await fetch (`${API_BASE}/sessions/me/start`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			credentials: 'include',
			body: JSON.stringify ({ player_name: playerName })
		});
		_sessionBootstrapped = true;
	} catch (e) {
		console.warn ('[session] bootstrap failed (BE 미가용?):', e.message || e);
	}
}

export async function fetchSessionMe () {
	try {
		const res = await fetch (`${API_BASE}/sessions/me`, { credentials: 'include' });
		if (!res.ok) return null;
		const json = await res.json ();
		return json?.data || null;
	} catch (e) { return null; }
}

export async function postSessionsCreate (forceReset) {
	const res = await fetch (`${API_BASE}/sessions`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		credentials: 'include',
		body: JSON.stringify ({ force_reset: !!forceReset })
	});
	return res;
}

export async function fetchResume () {
	try {
		const res = await fetch (`${API_BASE}/sessions/me/resume`, { credentials: 'include' });
		if (!res.ok) return { ok: false, status: res.status };
		const json = await res.json ();
		return { ok: true, data: json?.data || null };
	} catch (e) { return { ok: false, status: 0 }; }
}

export async function fetchEndingContent () {
	try {
		const res = await fetch (`${API_BASE}/game/ending`, { credentials: 'include' });
		if (!res.ok) return null;
		const json = await res.json ();
		return json?.data || null;
	} catch (e) { return null; }
}
