import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import type { AgentId } from '@/types';

interface AgentAvatarProps {
  agentId: AgentId;
  name: string;
  colorKey: string;
  image?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const sizeClass = {
  sm: 'size-7 text-xs',
  md: 'size-10 text-sm',
  lg: 'size-12 text-base',
  xl: 'size-16 text-lg',
};

export function AgentAvatar({ agentId, name, colorKey, image, size = 'md' }: AgentAvatarProps) {
  // 우선 순위: 명시된 이미지 > public/agents/{id}.png 추정 경로 > 외부 dicebear.
  const src = image ?? `/agents/${agentId}.png`;

  return (
    <Avatar
      className={sizeClass[size]}
      style={{ outline: `2px solid color-mix(in oklch, var(--${colorKey}) 60%, white)` }}
    >
      <AvatarImage src={src} alt={name} className="object-cover" />
      <AvatarFallback
        className="font-medium text-white"
        style={{ backgroundColor: `var(--${colorKey})` }}
      >
        {name[0]}
      </AvatarFallback>
    </Avatar>
  );
}
