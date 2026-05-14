export type TravelStyle =
  | '바다'
  | '숲'
  | '산'
  | '카페'
  | '맛집'
  | '사찰/한옥'
  | '전시/예술'
  | '야경'
  | '액티비티'
  | '조용한 곳'
  | '핫플';

export type TravelRange = '2시간 이내' | '4시간 이내' | '제한 없음';

export type TravelDuration = '당일' | '1박 2일' | '2박 3일';

export type DepartureRegion =
  | '서울'
  | '경기'
  | '부산'
  | '대구'
  | '광주'
  | '대전'
  | '기타';

export type BirthHour =
  | '모름'
  | '자시(23-01)'
  | '축시(01-03)'
  | '인시(03-05)'
  | '묘시(05-07)'
  | '진시(07-09)'
  | '사시(09-11)'
  | '오시(11-13)'
  | '미시(13-15)'
  | '신시(15-17)'
  | '유시(17-19)'
  | '술시(19-21)'
  | '해시(21-23)';

export interface UserInput {
  birthDate: string;
  birthHour: BirthHour;
  departure: DepartureRegion;
  travelRange: TravelRange;
  travelDuration: TravelDuration;
  preferredStyles: TravelStyle[];
}

export interface Destination {
  id: string;
  name: string;
  region: string;
  description: string;
  tags: TravelStyle[];
  imageUrl?: string;
  travelTime: Record<DepartureRegion, number>;
}

export interface RecommendResult {
  destinations: Destination[];
  sajuAnalysis: string;
  matchReason: string;
}
