import { monogatari } from './engine.js';
import { fetchSessionMe } from './api.js';
import { hasLocalAutoSave } from './save.js';
import { handleNewGame, handleResume, handleSomaQuit } from './game-flow.js';

monogatari.registerListener ('soma-new', {
	callback: function () {
		console.debug ('[soma-new] click → handleNewGame()');
		handleNewGame ();
		return true;
	}
});
monogatari.registerListener ('soma-resume', {
	callback: function () {
		console.debug ('[soma-resume] click → handleResume()');
		handleResume ();
		return true;
	}
});
monogatari.registerListener ('soma-quit', {
	callback: function () {
		console.debug ('[soma-quit] click → handleSomaQuit()');
		handleSomaQuit ();
		return true;
	}
});

const MainMenu = monogatari.component ('main-menu');

class SomaMainMenu extends MainMenu {
	render () {
		return `
			<div data-ui="main-brand" aria-hidden="true">
				<span data-ui="main-kicker">SOMA x First Love</span>
                <strong data-ui="main-title">커널을 좋아하는 옆자리의 그녀</strong>
			</div>
			<div data-content="wrapper">
                <button type="button" data-action="soma-resume" data-soma-button="resume" hidden>이어 하기</button>
                <button type="button" data-action="soma-new"    data-soma-button="new">새 게임</button>
                <button type="button" data-action="open-screen" data-open="settings">설정</button>
                <button type="button" data-action="open-screen" data-open="help">도움말</button>
			</div>
		`;
	}

	async didMount () {
		console.debug ('[soma-menu] didMount — registering refresh');
		await this._refreshSomaMenu ();
	}

	async _refreshSomaMenu () {
		try {
			const [me, localHasSave] = await Promise.all ([fetchSessionMe (), hasLocalAutoSave ()]);
			const beReady   = !!(me?.has_session && me?.is_started !== false);
			const canResume = beReady || localHasSave;
			const resumeBtn = this.querySelector ('[data-soma-button="resume"]');
			const newBtn    = this.querySelector ('[data-soma-button="new"]');
			if (resumeBtn) resumeBtn.hidden = !canResume;
			if (newBtn)    newBtn.textContent = canResume ? '새 게임 (이전 진행 삭제)' : '새 게임';
		} catch (e) {}
	}
}
SomaMainMenu.tag = 'main-menu';
monogatari.registerComponent (SomaMainMenu);

const SettingsScreen = monogatari.component ('settings-screen');
class SomaSettingsScreen extends SettingsScreen {
	render () {
		const baseHtml = super.render ();
		const quitHtml = `
			<div class="row row--center padded settings-quit-row">
				<button type="button" data-action="soma-quit" class="settings-quit-btn">메인 메뉴로</button>
			</div>
		`;
		return baseHtml + quitHtml;
	}
}
SomaSettingsScreen.tag = 'settings-screen';
monogatari.registerComponent (SomaSettingsScreen);

export function refreshSomaMainMenu () {
	document.querySelectorAll ('main-menu').forEach (el => {
		if (typeof el._refreshSomaMenu === 'function') el._refreshSomaMenu ();
	});
}
