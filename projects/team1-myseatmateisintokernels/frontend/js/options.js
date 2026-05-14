/**
 * =======================================
 * 엔진 설정
 *
 * '*'로 표시된 항목은 변경하지 마세요.
 * 무엇을 하는지 아는 경우에만 수정하세요.
 * =======================================
 **/

import { monogatari } from './engine.js';

monogatari.settings({

	// 게임의 이름입니다. 이 이름은 모든 데이터를 저장할 때 사용되므로
	// 한 번 배포한 게임의 이름은 변경하지 않는 것이 좋습니다. 새 릴리스를
	// 표시하려면 `Version` 설정을 사용하세요.
	'Name': '커널을 좋아하는 옆자리의 그녀',

	// 게임의 버전입니다 (시맨틱 버전 규칙, https://semver.org/).
	'Version': '0.1.0',

	// 초기 라벨 *
	'Label': 'Start',

	// 자동 저장 슬롯 수
	'Slots': 10,

	// 다국어 게임 화면을 사용하려면 true로 변경하세요.
	'MultiLanguage': false,

	// `MultiLanguage`가 true로 설정된 경우, 자산 로딩 화면 전에 언어 선택
	// 화면이 표시됩니다. false로 설정하면 로딩 화면이 먼저 나타나고 플레이어는
	// 설정 화면에서 언어를 변경해야 합니다.
	'LanguageSelectionScreen': false,

	// 메인 메뉴에서 재생될 음악.
	'MainScreenMusic': '',

	// 로컬 스토리지에 저장될 저장 슬롯의 접두사.
	'SaveLabel': 'Save',
	'AutoSaveLabel': 'AutoSave',

	// 메인 메뉴 사용 여부; 기본값: true *
	'ShowMainScreen': true,

	// 이미지 프리로딩 사용 여부; 기본값: true
	'Preload': true,

	// 자동 저장 간격(분). 기본값: 0 (비활성화)
	'AutoSave': 0,

	// 서비스 워커 사용 여부; 기본값: true *
	'ServiceWorkers': true,

	// 배경 이미지의 종횡비(Aspect Ratio). `ForceAspectRatio`가 켜져 있을 때만
	// 웹 배포된 비주얼 노벨에 영향을 줍니다.
	'AspectRatio': '16:9',

	// 종횡비 강제 옵션: 모든 이미지에 종횡비를 적용합니다.
	// 사용 가능한 값: 'None'(비강제), 'Visuals'(비주얼만 강제), 'Global'(전체 강제)
	'ForceAspectRatio': 'None',

	// 게임 전체에 대해 타이핑 텍스트 애니메이션을 사용할지 여부.
	'TypeAnimation': true,

	// NVL(노벨) 대화에서 타이핑 텍스트 애니메이션을 사용할지 여부.
	'NVLTypeAnimation': true,

	// 내레이터에 대한 타이핑 애니메이션 사용 여부.
	// 이전 설정이 false로 되어 있으면 이 설정이 true여도 애니메이션이 표시되지 않습니다.
	'NarratorTypeAnimation': true,

	// 중앙에 배치된 특수 캐릭터의 타이핑 애니메이션 사용 여부.
	// `TypeAnimation`이 false이면 이 설정이 true여도 애니메이션이 표시되지 않습니다.
	'CenteredTypeAnimation': true,

	// 모바일 기기에서 화면 방향을 강제합니다. 'portrait' 또는 'landscape'로
	// 설정하면 플레이어에게 회전하라는 경고가 표시됩니다.
	// 가능한 값: any, portrait, landscape
	'Orientation': 'landscape',

	// 플레이어가 게임을 스킵할 수 있게 합니다. 자동 재생과 유사하게,
	// 빠르게 스크립트를 진행합니다. 값이 0이면 스킵이 불가능하며,
	// 큰 값(밀리초)은 스킵 속도로 사용됩니다.
	'Skip': 0,

	// 에셋이 위치한 디렉터리를 정의합니다. 'root'는 다른 에셋 디렉터리들의
	// 기준이 되며 게임에서 파일을 불러올 때 사용됩니다.
	'AssetsPath': {
		'root': 'assets',
		'characters': 'characters',
		'icons': 'icons',
		'images': 'images',
		'music': 'music',
		'scenes': 'scenes',
		'sounds': 'sounds',
		'ui': 'ui',
		'videos': 'videos',
		'voices': 'voices',
		'gallery': 'gallery'
	},

	// 스플래시 스크린 라벨 이름입니다. 해당 이름의 라벨이 스크립트에 존재하면
	// 로딩 화면 직후 스플래시 스크린을 표시합니다.
	'SplashScreenLabel': '',

	// 게임 데이터를 저장할 스토리지 엔진을 정의합니다. *
	// 사용 가능한 어댑터:
	// - LocalStorage: 기본값
	// - SessionStorage: LocalStorage와 같지만 페이지가 닫히면 데이터가 지워집니다.
	// - IndexedDB: IndexedDB 웹 API를 사용하여 저장합니다.
	// - RemoteStorage: 지정한 REST API 엔드포인트로 데이터를 전송/조회합니다.
	'Storage': {
		'Adapter': 'LocalStorage',
		'Store': 'GameData',
		'Endpoint': ''
	}
});

// 초기 설정
monogatari.preferences ({

	// 다국어 게임 또는 기본 GUI 언어의 초기 언어 설정.
	'Language': 'English',

	// 초기 볼륨 값(0.0 ~ 1).
	'Volume': {
		'Music': 1,
		'Voice': 1,
		'Sound': 1,
		'Video': 1
	},

	// Electron에서 사용할 초기 해상도입니다. electron.js의 설정과
	// 일치해야 하며, 웹 배포된 노벨에는 영향을 주지 않습니다.
	'Resolution': '800x600',

	// 대화 텍스트가 표시되는 속도(빠를수록 텍스트가 빨리 나타납니다).
	'TextSpeed': 20,

	// 자동 재생 기능이 다음 문장을 보여주는 속도(초 단위).
	// 텍스트가 완전히 표시된 후에 카운트가 시작됩니다.
	'AutoPlaySpeed': 5
});
