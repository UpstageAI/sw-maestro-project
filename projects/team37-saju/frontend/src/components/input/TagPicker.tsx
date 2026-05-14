import type { TravelStyle } from '../../types';
import { Tag } from '../common';

const ALL_TAGS: TravelStyle[] = [
  '바다',
  '숲',
  '산',
  '카페',
  '맛집',
  '사찰/한옥',
  '전시/예술',
  '야경',
  '액티비티',
  '조용한 곳',
  '핫플',
];

interface TagPickerProps {
  selected: TravelStyle[];
  onChange: (selected: TravelStyle[]) => void;
}

export default function TagPicker({ selected, onChange }: TagPickerProps) {
  const toggle = (tag: TravelStyle) => {
    onChange(
      selected.includes(tag)
        ? selected.filter((t) => t !== tag)
        : [...selected, tag]
    );
  };

  return (
    <div>
      <p className="text-sm font-semibold text-gray-700 mb-2">
        선호 여행 스타일{' '}
        <span className="text-gray-400 font-normal text-xs">(복수 선택 가능)</span>
      </p>
      <div className="flex flex-wrap gap-2" role="group" aria-label="선호 여행 스타일 선택">
        {ALL_TAGS.map((tag) => (
          <Tag
            key={tag}
            selected={selected.includes(tag)}
            onClick={() => toggle(tag)}
          >
            {tag}
          </Tag>
        ))}
      </div>
      {selected.length > 0 && (
        <p className="mt-2 text-xs text-primary font-medium">
          {selected.length}개 선택됨
        </p>
      )}
    </div>
  );
}
