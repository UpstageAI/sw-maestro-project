# Team 2: 스마트 가계부 앱

## 프로젝트 개요
영수증 사진을 찍으면 OCR로 자동 인식하여 지출을 기록하는 스마트 가계부 앱입니다.

## 팀원
- 최서연 (팀장) - 풀스택
- 정도현 - 백엔드/OCR
- 한소희 - 모바일 앱

## 기술 스택
- **Backend**: Node.js, Express
- **Mobile**: Flutter
- **OCR**: Upstage Document AI
- **Database**: MongoDB
- **Deployment**: Firebase

## 주요 기능
1. 영수증 OCR 인식 (Upstage Document AI)
2. 자동 지출 분류 및 기록
3. 월별/카테고리별 지출 통계
4. 예산 설정 및 알림

## 실행 방법
```bash
# 백엔드
cd backend
npm install
npm start

# 모바일 앱
cd mobile
flutter pub get
flutter run
```

## 프로젝트 구조
```
team2/
├── backend/
│   ├── index.js
│   ├── package.json
│   └── routes/
│       └── receipt.js
├── mobile/
│   └── lib/
│       └── main.dart
└── README.md
```
