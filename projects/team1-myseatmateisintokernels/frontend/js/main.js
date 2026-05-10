import { Monogatari, monogatari } from './engine.js';

// side-effect imports — 모듈 평가 시점에 Monogatari 등록·리스너·훅이 설치됨.
import './options.js';
import './storage.js';
import './menu.js';
import './lifecycle.js';
import './script.js';

const { $_ready } = Monogatari;

if (window.location.protocol !== 'file:') {
	const manifestLink = document.createElement ('link');
	manifestLink.rel = 'manifest';
	manifestLink.href = 'manifest.json';
	document.head.appendChild (manifestLink);
}

$_ready (() => {
	monogatari.init ('#monogatari').then (() => {
		// Monogatari 초기화 완료.
	});
});
